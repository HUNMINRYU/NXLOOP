from __future__ import annotations

import argparse
import asyncio
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select

from config.dependencies import get_services
from config.settings import get_settings
from infrastructure.database.connection import AsyncSessionFactory
from infrastructure.database.models import CTRFeedback, CTRRankerApproval, CTRRankerCandidate, CTRRankerRun, now_kst
from infrastructure.services.notion_service import NotionService
from services.ctr_predictor import CTRPredictor
from services.model_eval_report_service import ModelEvalReportService
from utils.logger import get_logger


logger = get_logger(__name__)


@dataclass(frozen=True)
class CandidateRow:
    run_id: str
    candidate_id: int
    video_id: str | None
    title: str
    thumbnail_description: str
    competitor_titles: list[str]
    y_approved: int


def _parse_meta_thumbnail_desc(meta_json: str) -> str:
    if not meta_json:
        return ""
    try:
        obj = json.loads(meta_json)
    except Exception:
        return ""
    if isinstance(obj, dict):
        # 여러 키 후보를 유연하게 수용
        for k in ("thumbnail_description", "thumbnail_desc", "thumbnail_prompt", "thumbnail"):
            v = obj.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip()
    return ""


def _safe_float(v: object) -> float | None:
    if v is None:
        return None
    try:
        return float(str(v).strip().replace("%", ""))
    except Exception:
        return None


def _today_kst() -> date:
    return now_kst().date()


async def _load_approval_dataset(limit_runs: int | None = None) -> list[CandidateRow]:
    async with AsyncSessionFactory() as session:
        # 1) approvals
        approvals = (
            await session.execute(select(CTRRankerApproval))
        ).scalars().all()
        approved_by_run: dict[str, int] = {a.run_id: a.candidate_id for a in approvals}

        # 2) candidates for approved runs
        run_ids = list(approved_by_run.keys())
        if not run_ids:
            return []
        if limit_runs is not None:
            run_ids = run_ids[: max(0, int(limit_runs))]

        candidates = (
            await session.execute(
                select(CTRRankerCandidate).where(CTRRankerCandidate.run_id.in_(run_ids))
            )
        ).scalars().all()

        # group titles per run for competitor context
        titles_by_run: dict[str, list[str]] = defaultdict(list)
        for c in candidates:
            titles_by_run[c.run_id].append(c.title)

        rows: list[CandidateRow] = []
        for c in candidates:
            approved_id = approved_by_run.get(c.run_id)
            y = 1 if approved_id == c.id else 0
            competitor_titles = [t for t in titles_by_run.get(c.run_id, []) if t != c.title]
            rows.append(
                CandidateRow(
                    run_id=c.run_id,
                    candidate_id=c.id,
                    video_id=c.video_id,
                    title=c.title,
                    thumbnail_description=_parse_meta_thumbnail_desc(c.meta_json),
                    competitor_titles=competitor_titles,
                    y_approved=y,
                )
            )

        return rows


async def _load_regression_feedback(limit_rows: int | None = None) -> list[dict[str, Any]]:
    async with AsyncSessionFactory() as session:
        stmt = select(CTRFeedback).where(CTRFeedback.actual_ctr.is_not(None)).order_by(CTRFeedback.created_at.desc())
        if limit_rows is not None:
            stmt = stmt.limit(int(limit_rows))
        rows = (await session.execute(stmt)).scalars().all()

        out: list[dict[str, Any]] = []
        for r in rows:
            actual = _safe_float(r.actual_ctr)
            if actual is None:
                continue

            title = ""
            thumb_desc = ""
            if r.metadata_json:
                try:
                    meta = json.loads(r.metadata_json)
                except Exception:
                    meta = None
                if isinstance(meta, dict):
                    title = str(meta.get("title") or meta.get("video_title") or "").strip()
                    thumb_desc = str(meta.get("thumbnail_description") or "").strip()

            if not title:
                # title이 없으면 extract_features가 불가능하므로 스킵
                continue

            out.append(
                {
                    "video_id": r.video_id,
                    "title": title,
                    "thumbnail_description": thumb_desc,
                    "actual_ctr": float(actual),
                }
            )
        return out


def _flatten_features(features: dict[str, Any]) -> dict[str, float]:
    breakdown = features.get("breakdown") or {}
    if not isinstance(breakdown, dict):
        breakdown = {}
    flat: dict[str, float] = {}
    for k, v in breakdown.items():
        try:
            flat[str(k)] = float(v)
        except Exception:
            continue
    for k in ("rule_tower_score", "embedding_tower_score", "total_score"):
        try:
            flat[k] = float(features.get(k) or 0.0)
        except Exception:
            flat[k] = 0.0
    return flat


def _ensure_sklearn() -> Any:
    try:
        import sklearn  # noqa: F401
    except Exception as e:
        raise RuntimeError(
            "scikit-learn이 필요합니다. 로컬에서는 `pip install -e '.[dev]'` 를 실행하세요."
        ) from e
    return True


def _groupkfold_eval_classification(rows: list[CandidateRow]) -> dict[str, Any]:
    _ensure_sklearn()
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import precision_recall_fscore_support, roc_auc_score
    from sklearn.model_selection import GroupKFold
    from sklearn.preprocessing import StandardScaler

    predictor = CTRPredictor(gemini_client=None)

    # build feature matrix
    X_list: list[dict[str, float]] = []
    y: list[int] = []
    groups: list[str] = []
    run_ids: list[str] = []
    cand_ids: list[int] = []
    for r in rows:
        f = predictor.extract_features(
            title=r.title,
            thumbnail_description=r.thumbnail_description,
            competitor_titles=r.competitor_titles,
        )
        X_list.append(_flatten_features(f))
        y.append(int(r.y_approved))
        groups.append(r.run_id)
        run_ids.append(r.run_id)
        cand_ids.append(r.candidate_id)

    if not X_list:
        return {"error": "no_samples"}

    # stable column order
    cols = sorted({k for x in X_list for k in x.keys()})
    X = [[x.get(c, 0.0) for c in cols] for x in X_list]

    gkf = GroupKFold(n_splits=min(5, max(2, len(set(groups)))))

    fold_metrics: list[dict[str, Any]] = []
    all_scores: list[float] = []
    all_y: list[int] = []

    for fold_idx, (train_idx, test_idx) in enumerate(gkf.split(X, y, groups=groups), start=1):
        X_train = [X[i] for i in train_idx]
        y_train = [y[i] for i in train_idx]
        X_test = [X[i] for i in test_idx]
        y_test = [y[i] for i in test_idx]

        scaler = StandardScaler()
        X_train_s = scaler.fit_transform(X_train)
        X_test_s = scaler.transform(X_test)

        clf = LogisticRegression(max_iter=1000, class_weight="balanced")
        clf.fit(X_train_s, y_train)

        scores = clf.predict_proba(X_test_s)[:, 1].tolist()
        preds = [1 if s >= 0.5 else 0 for s in scores]

        p, r, f1, _ = precision_recall_fscore_support(y_test, preds, average="binary", zero_division=0)
        auc = 0.0
        try:
            auc = float(roc_auc_score(y_test, scores))
        except Exception:
            auc = 0.0

        fold_metrics.append(
            {
                "fold": fold_idx,
                "precision": float(round(p, 4)),
                "recall": float(round(r, 4)),
                "f1": float(round(f1, 4)),
                "roc_auc": float(round(auc, 4)),
                "test_samples": len(test_idx),
            }
        )
        all_scores.extend(scores)
        all_y.extend(y_test)

    # aggregate
    p, r, f1, _ = precision_recall_fscore_support(all_y, [1 if s >= 0.5 else 0 for s in all_scores], average="binary", zero_division=0)
    try:
        auc = float(roc_auc_score(all_y, all_scores))
    except Exception:
        auc = 0.0

    return {
        "n_samples": len(rows),
        "n_runs": len(set(groups)),
        "n_features": len(cols),
        "precision": float(round(p, 4)),
        "recall": float(round(r, 4)),
        "f1": float(round(f1, 4)),
        "roc_auc": float(round(auc, 4)),
        "folds": fold_metrics,
        "feature_columns": cols,
    }


def _baseline_top1_hit(rows: list[CandidateRow]) -> dict[str, Any]:
    predictor = CTRPredictor(gemini_client=None)
    by_run: dict[str, list[tuple[int, float, int]]] = defaultdict(list)  # cand_id, score, y
    for r in rows:
        f = predictor.extract_features(
            title=r.title,
            thumbnail_description=r.thumbnail_description,
            competitor_titles=r.competitor_titles,
        )
        score = float(f.get("total_score") or 0.0)
        by_run[r.run_id].append((r.candidate_id, score, r.y_approved))

    total = 0
    hit = 0
    for run_id, items in by_run.items():
        if not items:
            continue
        total += 1
        best = max(items, key=lambda t: t[1])
        if int(best[2]) == 1:
            hit += 1

    return {
        "top1_hit_rate": float(round((hit / total) if total else 0.0, 4)),
        "runs": total,
    }


def _groupkfold_eval_regression(rows: list[dict[str, Any]]) -> dict[str, Any]:
    _ensure_sklearn()
    from sklearn.linear_model import Ridge
    from sklearn.metrics import mean_absolute_error, mean_squared_error
    from sklearn.model_selection import KFold
    from sklearn.preprocessing import StandardScaler

    predictor = CTRPredictor(gemini_client=None)

    X_list: list[dict[str, float]] = []
    y: list[float] = []
    for r in rows:
        f = predictor.extract_features(
            title=str(r["title"]),
            thumbnail_description=str(r.get("thumbnail_description") or ""),
            competitor_titles=[],
        )
        X_list.append(_flatten_features(f))
        y.append(float(r["actual_ctr"]))

    if not X_list:
        return {"error": "no_samples"}

    cols = sorted({k for x in X_list for k in x.keys()})
    X = [[x.get(c, 0.0) for c in cols] for x in X_list]

    kf = KFold(n_splits=min(5, max(2, len(X) // 5)), shuffle=True, random_state=42)

    maes: list[float] = []
    rmses: list[float] = []
    for train_idx, test_idx in kf.split(X):
        X_train = [X[i] for i in train_idx]
        y_train = [y[i] for i in train_idx]
        X_test = [X[i] for i in test_idx]
        y_test = [y[i] for i in test_idx]

        scaler = StandardScaler()
        X_train_s = scaler.fit_transform(X_train)
        X_test_s = scaler.transform(X_test)

        model = Ridge(alpha=1.0)
        model.fit(X_train_s, y_train)
        pred = model.predict(X_test_s)

        maes.append(float(mean_absolute_error(y_test, pred)))
        rmses.append(float(mean_squared_error(y_test, pred, squared=False)))

    return {
        "n_samples": len(y),
        "n_features": len(cols),
        "mae": float(round(sum(maes) / len(maes), 4)) if maes else None,
        "rmse": float(round(sum(rmses) / len(rmses), 4)) if rmses else None,
        "feature_columns": cols,
    }


def _render_md(report: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# CTR Offline Training/Eval Report")
    lines.append(f"- generated_at: {report.get('generated_at')}")
    lines.append(f"- report_date: {report.get('report_date')}")
    lines.append("")

    ds = report.get("dataset_counts") or {}
    lines.append("## Dataset")
    for k, v in ds.items():
        lines.append(f"- {k}: {v}")
    lines.append("")

    lines.append("## Classification (Approval)")
    cls = report.get("classification") or {}
    if "error" in cls:
        lines.append(f"- error: {cls['error']}")
    else:
        lines.append(f"- precision: {cls.get('precision')}")
        lines.append(f"- recall: {cls.get('recall')}")
        lines.append(f"- f1: {cls.get('f1')}")
        lines.append(f"- roc_auc: {cls.get('roc_auc')}")
        lines.append("")
    base = report.get("baseline") or {}
    if base:
        lines.append("### Baseline")
        lines.append(f"- top1_hit_rate: {base.get('top1_hit_rate')} (runs={base.get('runs')})")
        lines.append("")

    lines.append("## Regression (Actual CTR)")
    reg = report.get("regression") or {}
    if "error" in reg:
        lines.append(f"- error: {reg['error']}")
    else:
        lines.append(f"- mae: {reg.get('mae')}")
        lines.append(f"- rmse: {reg.get('rmse')}")
        lines.append("")

    lines.append("## Reproduce")
    lines.append("```bash")
    lines.append("python -m services.ctr_offline_eval --limit-runs 200 --limit-feedback 500 --write-db --export-notion --upload-gcs")
    lines.append("```")
    return "\n".join(lines)


async def main_async(args: argparse.Namespace) -> int:
    rows = await _load_approval_dataset(limit_runs=args.limit_runs)
    feedback = await _load_regression_feedback(limit_rows=args.limit_feedback)

    logger.info("[FEATURE] ▶ ctr_offline_eval 시작 | runs=%s feedback=%s", len(set(r.run_id for r in rows)), len(feedback))

    baseline = _baseline_top1_hit(rows) if rows else {"error": "no_samples"}
    cls = _groupkfold_eval_classification(rows) if rows else {"error": "no_samples"}
    reg = _groupkfold_eval_regression(feedback) if feedback else {"error": "no_samples"}

    report_date = _today_kst()
    generated_at = datetime.now(timezone.utc).isoformat()
    report: dict[str, Any] = {
        "report_type": ModelEvalReportService.REPORT_TYPE_CTR_OFFLINE_EVAL,
        "report_date": report_date.isoformat(),
        "generated_at": generated_at,
        "dataset_counts": {
            "approval_candidates": len(rows),
            "approval_runs": len(set(r.run_id for r in rows)),
            "regression_samples": len(feedback),
        },
        "baseline": baseline,
        "classification": cls,
        "regression": reg,
    }

    out_dir = Path("outputs/ctr_training/reports")
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / f"{report_date.isoformat()}-ctr-offline-eval.json"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    docs_dir = Path("docs") / report_date.isoformat() / "codex"
    docs_dir.mkdir(parents=True, exist_ok=True)
    md_path = docs_dir / "ctr-offline-training-eval.md"
    md_path.write_text(_render_md(report), encoding="utf-8")

    # Upload artifacts to GCS (archive)
    settings = get_settings()
    services = get_services()
    artifact_gcs_path: str | None = None
    if args.upload_gcs and services.storage_service.is_configured():
        date_prefix = report_date.isoformat()
        base_path = f"reports/model-eval/{date_prefix}/ctr-offline-eval"
        ok1 = services.storage_service.upload(
            json_path.read_text(encoding="utf-8"),
            f"{base_path}.json",
            content_type="application/json",
        )
        ok2 = services.storage_service.upload(
            md_path.read_text(encoding="utf-8"),
            f"{base_path}.md",
            content_type="text/markdown",
        )
        if ok1 and ok2 and services.storage_service.bucket_name:
            artifact_gcs_path = f"gs://{services.storage_service.bucket_name}/{base_path}.json"

    notion_url: str | None = None
    if args.export_notion and settings.notion_api_key and settings.notion_database_id:
        notion = NotionService(settings.notion_api_key, settings.notion_database_id)
        payload = {
            "report_type": ModelEvalReportService.REPORT_TYPE_CTR_OFFLINE_EVAL,
            "meta": {
                "report_date": report_date.isoformat(),
                "generated_at": generated_at,
                "artifact_gcs_path": artifact_gcs_path,
            },
            "report": report,
        }
        try:
            notion_url = notion.export(payload)
        except Exception as e:
            # Notion 실패는 평가 자체를 실패로 만들지 않는다.
            logger.error("Notion export failed: %s", e)

    if args.write_db:
        async with AsyncSessionFactory() as session:
            svc = ModelEvalReportService(session)
            await svc.upsert_report(
                report_type=ModelEvalReportService.REPORT_TYPE_CTR_OFFLINE_EVAL,
                report_date=report_date,
                dataset_counts=report["dataset_counts"],
                cls_metrics={k: v for k, v in cls.items() if k not in ("folds", "feature_columns")},
                reg_metrics={k: v for k, v in reg.items() if k not in ("feature_columns",)},
                baseline_metrics=baseline,
                artifact_gcs_path=artifact_gcs_path,
                notion_url=notion_url,
            )

    logger.info("[FEATURE] ■ ctr_offline_eval 완료 | json=%s md=%s", str(json_path), str(md_path))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="CTR offline training/eval (approval cls + actual ctr reg)")
    p.add_argument("--limit-runs", type=int, default=None)
    p.add_argument("--limit-feedback", type=int, default=None)
    p.add_argument("--write-db", action="store_true")
    p.add_argument("--export-notion", action="store_true")
    p.add_argument("--upload-gcs", action="store_true")
    return p


def main() -> int:
    args = build_parser().parse_args()
    try:
        return asyncio.run(main_async(args))
    except Exception as e:
        raise RuntimeError(f"ctr_offline_eval failed: {e}") from e


if __name__ == "__main__":
    raise SystemExit(main())

