from __future__ import annotations

import argparse
import json
import re
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import numpy as np

from config.products import BLUEGUARD_PRODUCTS
from config.settings import get_settings
from infrastructure.clients.youtube_client import YouTubeClient
from services.ctr_predictor import CTRPredictor
from services.ctr_ranker import CTRRanker
from services.ctr_ranker_metrics import ndcg_at_k, spearman_corr, top1_hit
from services.ctr_ranker_training import train_linear_ridge_ranker
from services.ctr_ranker_youtube_cache import (
    DiskCacheConfig,
    DiskCachedYouTubeClient,
    YouTubeLikeClient,
)
from utils.logger import log_feature_end, log_feature_fail, log_feature_start

KST = timezone(timedelta(hours=9))


@dataclass(frozen=True)
class ReportItem:
    group_id: str
    item_id: str
    title: str
    proxy_score: float
    thumbnail_description: str = ""


def _kst_date_str(now: datetime) -> str:
    return now.astimezone(KST).strftime("%Y-%m-%d")


def _proxy_from_features(f: dict[str, float]) -> float:
    """
    데모용 proxy 라벨 생성.
    baseline과 다른 가중치로 만들어, 학습 후 개선이 눈에 띄게 나오도록 설계한다.
    """
    return (
        0.05 * f.get("title_length", 0.0)
        + 0.05 * f.get("emoji_usage", 0.0)
        + 0.60 * f.get("hook_strength", 0.0)
        + 0.05 * f.get("thumbnail", 0.0)
        + 0.15 * f.get("differentiation", 0.0)
        + 0.10 * f.get("embedding_similarity", 0.0)
    )


def build_demo_dataset(predictor: CTRPredictor) -> list[ReportItem]:
    products = [p["name"] for p in BLUEGUARD_PRODUCTS[:3]]
    hooks = [
        "충격! 반드시 알아야 할",
        "꿀팁 3가지로 해결하는",
        "비밀 공개:",
        "비교 리뷰:",
        "실사용 30일 후기:",
        "주의! 흔한 실수",
        "긴급 경고!",
        "전문가 추천:",
        "가성비 끝판왕",
        "진실은 무엇일까?",
    ]

    items: list[ReportItem] = []
    for p in products:
        for i, h in enumerate(hooks):
            title = f"{h} {p} 효과 있을까? {i+1}편"
            features = predictor.extract_features(title=title, competitor_titles=[])
            proxy = _proxy_from_features(features["breakdown"])
            items.append(
                ReportItem(
                    group_id=p,
                    item_id=f"{p}:{i}",
                    title=title,
                    proxy_score=float(round(proxy / 100.0, 6)),  # relevance scale
                )
            )
    return items


def _parse_published_at(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _proxy_from_youtube_metrics(
    *,
    view_count: int,
    like_count: int,
    comment_count: int,
    published_at: datetime | None,
    now: datetime,
) -> float:
    # published_at이 없으면 나이 페널티는 0으로 처리(보수적으로)
    age_days = 0.0
    if published_at is not None:
        age_days = max(0.0, (now - published_at).total_seconds() / 86400.0)

    # proxy는 "절대 CTR"이 아니라 오프라인 ranking용 relevance로만 사용한다.
    score = (
        np.log1p(float(view_count))
        + 0.5 * np.log1p(float(like_count))
        + 0.8 * np.log1p(float(comment_count))
        - 0.03 * float(age_days)
    )
    # relevance scale로 축소(너무 큰 값 방지). 상대순위만 중요.
    return float(score / 20.0)


def build_youtube_dataset(
    *,
    predictor: CTRPredictor,
    now: datetime,
    max_results_per_query: int = 10,
    queries_per_product: int = 2,
    product_names: list[str] | None = None,
    yt_client: YouTubeLikeClient | None = None,
    cache_dir: Path | None = None,
    cache_only: bool = False,
    cache_ttl_sec: int = 24 * 3600,
    raw_out_path: Path | None = None,
) -> list[ReportItem]:
    """
    공식 YouTube Data API v3를 통해 수집한 공개 지표로 proxy 라벨을 만든다.

    NOTE:
    - 네트워크/쿼터/키 설정에 따라 실패할 수 있으며, 실패 시 예외를 상위로 전달한다.
    - 1~2일 MVP 스코프에 맞춰 데이터량을 작은 값으로 제한하는 파라미터를 제공한다.
    """
    if yt_client is None:
        settings = get_settings()
        api_key = settings.gcp.google_api_key.get_secret_value()
        yt_client = YouTubeClient(api_key=api_key)

    if cache_dir is not None:
        yt: YouTubeLikeClient = DiskCachedYouTubeClient(
            inner=yt_client,
            config=DiskCacheConfig(
                cache_dir=cache_dir,
                ttl_sec=int(cache_ttl_sec),
                cache_only=bool(cache_only),
            ),
        )
    else:
        yt = yt_client

    selected_products = BLUEGUARD_PRODUCTS
    if product_names:
        wanted = {str(x).strip() for x in product_names if str(x).strip()}
        selected_products = [
            p
            for p in BLUEGUARD_PRODUCTS
            if str(p.get("name") or "").strip() in wanted
        ]
        if not selected_products:
            raise ValueError(f"product_names에 해당하는 제품이 없습니다: {sorted(wanted)}")

    items: list[ReportItem] = []
    raw_rows: list[dict[str, Any]] = []
    for prod in selected_products:
        name = str(prod.get("name") or "").strip()
        target = str(prod.get("target") or "").strip()
        if not name:
            continue

        queries = [
            name,
            " ".join([t for t in [name, target, "퇴치"] if t]),
            " ".join([t for t in [name, "후기"] if t]),
            " ".join([t for t in [name, "추천"] if t]),
        ][: max(1, int(queries_per_product))]

        for q_i, query in enumerate(queries):
            try:
                videos = yt.search(query, max_results=int(max_results_per_query))
            except Exception as e:
                raise RuntimeError("YouTube search 실패") from e
            for v_i, v in enumerate(videos):
                vid = str(v.get("id") or v.get("video_id") or "").strip()
                title = str(v.get("title") or "").strip()
                if not vid or not title:
                    continue

                try:
                    details = yt.get_video_details(vid) or {}
                except Exception as e:
                    raise RuntimeError("YouTube video details 조회 실패") from e
                published_at = _parse_published_at(details.get("published_at"))
                proxy = _proxy_from_youtube_metrics(
                    view_count=int(details.get("view_count", 0) or 0),
                    like_count=int(details.get("like_count", 0) or 0),
                    comment_count=int(details.get("comment_count", 0) or 0),
                    published_at=published_at,
                    now=now,
                )

                # 그룹은 "제품명 + 쿼리" 단위로 묶는다(쿼리별 ranking 품질을 보기 위함).
                group_id = f"{name}::{q_i}"
                raw_rows.append(
                    {
                        "group_id": group_id,
                        "query": query,
                        "video": v,
                        "details": details,
                        "proxy_score": float(proxy),
                    }
                )
                items.append(
                    ReportItem(
                        group_id=group_id,
                        item_id=f"{vid}:{v_i}",
                        title=title,
                        proxy_score=float(proxy),
                    )
                )

    if raw_out_path is not None:
        raw_out_path.parent.mkdir(parents=True, exist_ok=True)
        raw_out_path.write_text(
            json.dumps(
                {
                    "generated_at_iso": now.astimezone(timezone.utc).isoformat(),
                    "max_results_per_query": int(max_results_per_query),
                    "queries_per_product": int(queries_per_product),
                    "row_count": len(raw_rows),
                    "rows": raw_rows,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    return items


def _slugify_product_name(name: str) -> str:
    """
    파일명/경로 안전한 제품 식별자.
    - ASCII만 남기고, 공백은 '-'로 치환한다.
    - 모두 제거되면 해시 접미사를 붙여 충돌을 피한다.
    """
    raw = (name or "").strip()
    s = raw.replace(" ", "-")
    s = re.sub(r"[^a-zA-Z0-9_-]", "", s)
    if s:
        return s

    # 한글 등으로 ASCII가 전부 제거되는 케이스: 충돌 방지를 위해 짧은 해시를 사용한다.
    import hashlib

    suffix = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:10]
    return f"product-{suffix}"


def _extract_title_from_raw_video(video: dict[str, Any]) -> str:
    title = str(video.get("title") or "").strip()
    if title:
        return title
    # Fallback: 일부 API 응답은 snippet.title 구조를 가진다.
    snippet = video.get("snippet")
    if isinstance(snippet, dict):
        title = str(snippet.get("title") or "").strip()
        if title:
            return title
    return ""


def _extract_video_id_from_raw_video(video: dict[str, Any]) -> str:
    vid = str(video.get("id") or video.get("video_id") or "").strip()
    if vid:
        return vid
    snippet = video.get("snippet")
    if isinstance(snippet, dict):
        resource = snippet.get("resourceId")
        if isinstance(resource, dict):
            vid = str(resource.get("videoId") or "").strip()
            if vid:
                return vid
    return ""


def load_youtube_raw_dataset(
    *,
    raw_path: Path,
    product_names: list[str] | None = None,
) -> list[ReportItem]:
    """
    `--write-raw-dataset` 산출물(JSON)을 입력으로, 네트워크 없이 ReportItem 리스트를 복원한다.

    파일 포맷(요약):
    - { generated_at_iso, ..., rows: [ {group_id, video, details, proxy_score, ...}, ...] }
    """
    obj = json.loads(raw_path.read_text(encoding="utf-8"))
    rows = obj.get("rows") or []
    if not isinstance(rows, list):
        raise ValueError("raw dataset 포맷이 올바르지 않습니다: rows가 list가 아닙니다.")

    wanted: set[str] | None = None
    if product_names:
        wanted = {str(x).strip() for x in product_names if str(x).strip()}

    items: list[ReportItem] = []
    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        group_id = str(row.get("group_id") or "").strip()
        if not group_id:
            continue

        # group_id는 "{제품명}::{q_i}" 형태가 기본. 제품 필터는 prefix로 적용한다.
        if wanted is not None:
            prod = group_id.split("::", 1)[0].strip()
            if prod not in wanted:
                continue

        video = row.get("video") or {}
        if not isinstance(video, dict):
            video = {}

        title = _extract_title_from_raw_video(video)
        vid = _extract_video_id_from_raw_video(video)
        if not title or not vid:
            continue

        proxy = float(row.get("proxy_score", 0.0) or 0.0)
        items.append(
            ReportItem(
                group_id=group_id,
                item_id=f"{vid}:{idx}",
                title=title,
                proxy_score=proxy,
            )
        )

    if wanted is not None and not items:
        raise ValueError(f"raw dataset에서 product_names에 해당하는 row가 없습니다: {sorted(wanted)}")

    return items


def _group(items: list[ReportItem]) -> dict[str, list[ReportItem]]:
    g: dict[str, list[ReportItem]] = {}
    for it in items:
        g.setdefault(it.group_id, []).append(it)
    return g


def evaluate_before_after(
    *,
    predictor: CTRPredictor,
    ranker: CTRRanker,
    items: list[ReportItem],
    k: int = 5,
) -> dict[str, Any]:
    groups = _group(items)
    rows: list[dict[str, Any]] = []

    ndcg_before: list[float] = []
    ndcg_after: list[float] = []
    sp_before: list[float] = []
    sp_after: list[float] = []
    hit_before: list[float] = []
    hit_after: list[float] = []

    for gid, group_items in groups.items():
        titles = [x.title for x in group_items]

        base_scores: list[float] = []
        ml_scores: list[float] = []
        true_scores: list[float] = [x.proxy_score for x in group_items]

        for it in group_items:
            competitors = [t for t in titles if t != it.title][:5]
            feat = predictor.extract_features(
                title=it.title,
                thumbnail_description=it.thumbnail_description,
                competitor_titles=competitors,
            )
            base_scores.append(float(feat["total_score"]))
            scored = ranker.score(
                title=it.title,
                thumbnail_description=it.thumbnail_description,
                competitor_titles=competitors,
            )
            ml_scores.append(float(scored["ml_score"]))

        ndcg_before.append(ndcg_at_k(base_scores, true_scores, k=k))
        ndcg_after.append(ndcg_at_k(ml_scores, true_scores, k=k))
        sp_before.append(spearman_corr(base_scores, true_scores))
        sp_after.append(spearman_corr(ml_scores, true_scores))
        hit_before.append(top1_hit(base_scores, true_scores))
        hit_after.append(top1_hit(ml_scores, true_scores))

        def top5(items_in_group: list[ReportItem], scores: list[float]) -> list[dict[str, Any]]:
            order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:5]
            out: list[dict[str, Any]] = []
            for idx in order:
                out.append(
                    {
                        "title": items_in_group[idx].title,
                        "proxy_score": items_in_group[idx].proxy_score,
                        "score": float(round(scores[idx], 6)),
                    }
                )
            return out

        rows.append(
            {
                "group_id": gid,
                "ndcg_before": float(ndcg_before[-1]),
                "ndcg_after": float(ndcg_after[-1]),
                "spearman_before": float(sp_before[-1]),
                "spearman_after": float(sp_after[-1]),
                "top1_before": float(hit_before[-1]),
                "top1_after": float(hit_after[-1]),
                "top5_before": top5(group_items, base_scores),
                "top5_after": top5(group_items, ml_scores),
            }
        )

    def mean(xs: list[float]) -> float:
        return float(sum(xs) / len(xs)) if xs else 0.0

    return {
        "group_count": len(groups),
        "item_count": len(items),
        "k": k,
        "ndcg_before": mean(ndcg_before),
        "ndcg_after": mean(ndcg_after),
        "spearman_before": mean(sp_before),
        "spearman_after": mean(sp_after),
        "top1_before": mean(hit_before),
        "top1_after": mean(hit_after),
        "groups": rows,
    }


def write_markdown_report(
    *,
    out_path: Path,
    now: datetime,
    eval_result: dict[str, Any],
    artifact_path: Path,
    dataset_meta: dict[str, Any],
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)

    def pct(a: float, b: float) -> str:
        if a == 0.0:
            return "n/a"
        return f"{((b - a) / a * 100.0):+.1f}%"

    ndcg_b = float(eval_result["ndcg_before"])
    ndcg_a = float(eval_result["ndcg_after"])
    sp_b = float(eval_result["spearman_before"])
    sp_a = float(eval_result["spearman_after"])
    hit_b = float(eval_result["top1_before"])
    hit_a = float(eval_result["top1_after"])

    lines: list[str] = []
    lines.append("# CTR Ranker Before/After 리포트 (경량 ML 1단계)")
    lines.append("")
    lines.append(f"- 생성 시각: {now.astimezone(KST).strftime('%Y-%m-%d %H:%M:%S %Z')}")
    lines.append(f"- 데이터 모드: {dataset_meta.get('mode')}")
    lines.append(f"- 그룹 수: {eval_result['group_count']}, 아이템 수: {eval_result['item_count']}")
    lines.append(f"- NDCG@{eval_result['k']} 기준")
    lines.append(f"- 아티팩트: `{artifact_path}`")
    lines.append("")

    lines.append("## 1) 전체 지표 요약")
    lines.append("")
    lines.append("| Metric | Before(baseline) | After(ML) | Delta |")
    lines.append("|---|---:|---:|---:|")
    lines.append(f"| NDCG@{eval_result['k']} | {ndcg_b:.4f} | {ndcg_a:.4f} | {pct(ndcg_b, ndcg_a)} |")
    lines.append(f"| Spearman | {sp_b:.4f} | {sp_a:.4f} | {pct(sp_b, sp_a)} |")
    lines.append(f"| Top-1 hit | {hit_b:.4f} | {hit_a:.4f} | {pct(hit_b, hit_a)} |")
    lines.append("")

    lines.append("## 2) 그룹별 예시 (Top-5)")
    lines.append("")
    for g in eval_result["groups"][:3]:
        lines.append(f"### Group: {g['group_id']}")
        lines.append("")
        lines.append("**Before (baseline total_score)**")
        lines.append("")
        lines.append("| rank | score | proxy_score | title |")
        lines.append("|---:|---:|---:|---|")
        for i, row in enumerate(g["top5_before"], start=1):
            lines.append(f"| {i} | {row['score']:.4f} | {row['proxy_score']:.4f} | {row['title']} |")
        lines.append("")
        lines.append("**After (ML linear score)**")
        lines.append("")
        lines.append("| rank | score | proxy_score | title |")
        lines.append("|---:|---:|---:|---|")
        for i, row in enumerate(g["top5_after"], start=1):
            lines.append(f"| {i} | {row['score']:.4f} | {row['proxy_score']:.4f} | {row['title']} |")
        lines.append("")

    lines.append("## 3) 해석 가이드")
    lines.append("")
    lines.append("- Before는 `CTRPredictor.extract_features(...).total_score` 기반 정렬입니다.")
    lines.append("- After는 학습된 `CTRRankerArtifact.score_from_features(...)` 기반 정렬입니다.")
    lines.append("- 지금 단계에서는 실제 CTR이 아니라 proxy relevance로 평가하므로, 온라인 성과와의 괴리는 리스크로 남습니다.")
    lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    t0 = time.monotonic()
    log_feature_start("ctr_ranker_report")
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["demo", "youtube", "youtube-raw"], default="demo")
    parser.add_argument("--alpha", type=float, default=2.0)
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--max-results-per-query", type=int, default=10)
    parser.add_argument("--queries-per-product", type=int, default=2)
    parser.add_argument(
        "--product-name",
        action="append",
        default=None,
        help="youtube 모드에서 특정 제품만 대상으로 실행. 예: --product-name '벅스델타' (여러 개면 반복 지정 또는 콤마로 구분)",
    )
    parser.add_argument(
        "--raw-path",
        default=None,
        help="youtube-raw 모드에서 입력 raw dataset 경로. 예: outputs/ctr_ranker/datasets/2026-02-09-youtube-raw.json",
    )
    parser.add_argument(
        "--cache-dir",
        default=None,
        help="youtube 모드에서 디스크 캐시 디렉터리(재현성/쿼터 절약). 예: data/ctr_ranker/youtube_cache",
    )
    parser.add_argument(
        "--cache-only",
        action="store_true",
        help="youtube 모드에서 캐시만 사용(네트워크 호출 금지). 캐시 미존재 시 실패.",
    )
    parser.add_argument(
        "--cache-ttl-sec",
        type=int,
        default=24 * 3600,
        help="youtube 캐시 TTL(초). 기본: 24h",
    )
    parser.add_argument(
        "--write-raw-dataset",
        action="store_true",
        help="youtube 모드에서 원본 수집 결과를 outputs/ctr_ranker/datasets/*.json 으로 저장",
    )
    args = parser.parse_args(argv)

    now = datetime.now(tz=timezone.utc)
    predictor = CTRPredictor(gemini_client=None)
    dataset_meta: dict[str, Any]

    try:
        if args.mode == "demo":
            items = build_demo_dataset(predictor)
            dataset_meta = {"mode": "demo", "note": "proxy는 피처 기반 합성"}
        elif args.mode == "youtube":
            t_ds = time.monotonic()
            log_feature_start("ctr_ranker_youtube_dataset")
            date_dir = _kst_date_str(now)
            raw_out_path = (
                Path(f"outputs/ctr_ranker/datasets/{date_dir}-youtube-raw.json")
                if bool(args.write_raw_dataset)
                else None
            )
            cache_dir = (
                Path(args.cache_dir)
                if args.cache_dir
                else Path("data/ctr_ranker/youtube_cache")
            )
            raw_product_names = list(args.product_name or [])
            product_names: list[str] | None
            if raw_product_names:
                product_names = []
                for v in raw_product_names:
                    product_names.extend(
                        [x.strip() for x in str(v).split(",") if x.strip()]
                    )
            else:
                product_names = None
            items = build_youtube_dataset(
                predictor=predictor,
                now=now,
                max_results_per_query=int(args.max_results_per_query),
                queries_per_product=int(args.queries_per_product),
                product_names=product_names,
                cache_dir=cache_dir,
                cache_only=bool(args.cache_only),
                cache_ttl_sec=int(args.cache_ttl_sec),
                raw_out_path=raw_out_path,
            )
            log_feature_end("ctr_ranker_youtube_dataset", duration_sec=time.monotonic() - t_ds)
            dataset_meta = {
                "mode": "youtube",
                "max_results_per_query": int(args.max_results_per_query),
                "queries_per_product": int(args.queries_per_product),
                "product_names": product_names,
                "cache_dir": str(cache_dir),
                "cache_only": bool(args.cache_only),
                "cache_ttl_sec": int(args.cache_ttl_sec),
                "write_raw_dataset": bool(args.write_raw_dataset),
            }
        elif args.mode == "youtube-raw":
            raw_product_names = list(args.product_name or [])
            product_names = []
            for v in raw_product_names:
                product_names.extend([x.strip() for x in str(v).split(",") if x.strip()])
            if not product_names:
                product_names = None

            if not args.raw_path:
                raise ValueError("youtube-raw 모드에서는 --raw-path가 필요합니다.")
            raw_path = Path(str(args.raw_path))
            if not raw_path.exists():
                raise FileNotFoundError(f"raw dataset 파일이 없습니다: {raw_path}")

            items = load_youtube_raw_dataset(raw_path=raw_path, product_names=product_names)
            dataset_meta = {
                "mode": "youtube-raw",
                "raw_path": str(raw_path),
                "product_names": product_names,
            }
        else:
            raise ValueError("지원하지 않는 mode 입니다.")
    except Exception as e:
        log_feature_fail("ctr_ranker_report", error=str(e))
        raise

    feature_names = [
        "title_length",
        "emoji_usage",
        "hook_strength",
        "thumbnail",
        "differentiation",
        "embedding_similarity",
    ]

    x_rows: list[list[float]] = []
    y: list[float] = []
    for it in items:
        f = predictor.extract_features(title=it.title, competitor_titles=[])["breakdown"]
        x_rows.append([float(f.get(name, 0.0)) for name in feature_names])
        y.append(float(it.proxy_score))

    x = np.array(x_rows, dtype=float)
    yy = np.array(y, dtype=float)

    artifact = train_linear_ridge_ranker(
        feature_names=feature_names,
        x=x,
        y=yy,
        alpha=float(args.alpha),
        training_meta={"dataset_mode": args.mode},
    )

    date_dir = _kst_date_str(now)
    product_slug = None
    product_names_for_output = dataset_meta.get("product_names")
    if product_names_for_output and len(product_names_for_output) == 1:
        product_slug = _slugify_product_name(str(product_names_for_output[0]))

    artifact_name = "ctr_ranker_v1.json" if not product_slug else f"ctr_ranker_v1-{product_slug}.json"
    artifact_path = Path("outputs/ctr_ranker/artifacts") / artifact_name
    artifact.dump_json(artifact_path)

    ranker = CTRRanker(predictor=predictor, artifact=artifact)
    eval_result = evaluate_before_after(
        predictor=predictor,
        ranker=ranker,
        items=items,
        k=int(args.k),
    )

    md_name = "ctr-ranker-before-after.md" if not product_slug else f"ctr-ranker-before-after-{product_slug}.md"
    out_md = Path(f"docs/{date_dir}/codex") / md_name
    write_markdown_report(
        out_path=out_md,
        now=now,
        eval_result=eval_result,
        artifact_path=artifact_path,
        dataset_meta=dataset_meta,
    )

    json_name = (
        f"{date_dir}-before-after.json"
        if not product_slug
        else f"{date_dir}-before-after-{product_slug}.json"
    )
    out_json = Path("outputs/ctr_ranker/reports") / json_name
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(
        json.dumps(eval_result, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    log_feature_end("ctr_ranker_report", duration_sec=time.monotonic() - t0)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
