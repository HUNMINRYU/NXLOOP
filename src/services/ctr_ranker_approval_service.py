from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import date
from io import StringIO
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.models import (
    CTRRankerApproval,
    CTRRankerCandidate,
    CTRRankerRun,
    now_kst,
)


@dataclass(frozen=True)
class ImportResult:
    run_id: str
    candidate_count: int


def _safe_float(v: str | None) -> float | None:
    if v is None:
        return None
    s = str(v).strip()
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _safe_int(v: str | None) -> int | None:
    if v is None:
        return None
    s = str(v).strip()
    if not s:
        return None
    try:
        return int(s)
    except ValueError:
        return None


class CTRRankerApprovalService:
    """CTR Ranker 후보 import + 승인(approve) 워크플로우.

    - run 단위로 후보(topK)를 저장한다.
    - 승인 결과는 run에 귀속된다. (사용자 선택: 1)
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def import_from_raw_and_topk_csv(
        self,
        *,
        product_name: str,
        report_date: date,
        raw_dataset: dict[str, Any],
        topk_csv_text: str,
        mode: str = "youtube",
        raw_dataset_path: str | None = None,
        topk_csv_path: str | None = None,
        report_json_path: str | None = None,
        metrics: dict[str, Any] | None = None,
    ) -> ImportResult:
        """raw + topK(before/after) CSV를 조합해 승인 후보를 DB에 적재한다.

        현재 리포트 JSON(2026-02-09-before-after.json)은 그룹별 집계 중심이라
        후보 단위를 만들기엔 정보가 부족합니다.
        그래서 MVP는 `*-top5.csv`(후보) + `*-youtube-raw.json`(썸네일/비디오 id)를
        조합하는 방식으로 import 합니다.
        """
        if not product_name.strip():
            raise ValueError("product_name은 비어 있을 수 없습니다.")
        if "rows" not in raw_dataset:
            raise ValueError("raw_dataset에 rows가 없습니다.")

        candidate_rows = build_candidate_rows_from_raw_and_topk(
            product_name=product_name,
            raw_dataset=raw_dataset,
            topk_csv_text=topk_csv_text,
        )

        # 3) run 생성 + 후보 upsert(동일 date/product 재수집 시 새 run 생성)
        run = CTRRankerRun(
            product_name=product_name,
            report_date=report_date,
            mode=mode,
            raw_dataset_path=raw_dataset_path,
            topk_csv_path=topk_csv_path,
            report_json_path=report_json_path,
            metrics_json=json.dumps(metrics or {}, ensure_ascii=False),
            created_at=now_kst(),
        )
        self._session.add(run)
        await self._session.flush()  # run.id 확정

        candidates: list[CTRRankerCandidate] = []
        for row in candidate_rows:
            candidates.append(
                CTRRankerCandidate(
                    run_id=run.id,
                    video_id=row.get("video_id"),
                    title=row["title"],
                    thumbnail_url=row.get("thumbnail_url"),
                    baseline_rank=row.get("baseline_rank"),
                    baseline_score=row.get("baseline_score"),
                    after_rank=row.get("after_rank"),
                    after_score=row.get("after_score"),
                    proxy_score=row.get("proxy_score"),
                    meta_json="{}",
                    created_at=now_kst(),
                )
            )

        self._session.add_all(candidates)
        await self._session.commit()
        return ImportResult(run_id=run.id, candidate_count=len(candidates))

    async def list_runs(
        self,
        *,
        product_name: str,
        limit: int = 20,
    ) -> list[CTRRankerRun]:
        stmt = (
            select(CTRRankerRun)
            .where(CTRRankerRun.product_name == product_name)
            .order_by(CTRRankerRun.created_at.desc())
            .limit(limit)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return list(rows)

    async def list_candidates(
        self,
        *,
        run_id: str,
        limit: int = 50,
    ) -> list[CTRRankerCandidate]:
        stmt = (
            select(CTRRankerCandidate)
            .where(CTRRankerCandidate.run_id == run_id)
            .order_by(CTRRankerCandidate.after_rank.asc().nullslast(), CTRRankerCandidate.id.asc())
            .limit(limit)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return list(rows)

    async def get_approval(self, *, run_id: str) -> CTRRankerApproval | None:
        stmt = select(CTRRankerApproval).where(CTRRankerApproval.run_id == run_id)
        return (await self._session.execute(stmt)).scalars().first()

    async def approve(
        self,
        *,
        run_id: str,
        candidate_id: int,
        approved_by_user_id: int | None = None,
        note: str | None = None,
    ) -> CTRRankerApproval:
        # run/후보 존재 검증
        run = (await self._session.execute(select(CTRRankerRun).where(CTRRankerRun.id == run_id))).scalars().first()
        if run is None:
            raise ValueError(f"run이 없습니다: {run_id}")

        candidate = (
            await self._session.execute(
                select(CTRRankerCandidate).where(
                    CTRRankerCandidate.id == candidate_id,
                    CTRRankerCandidate.run_id == run_id,
                )
            )
        ).scalars().first()
        if candidate is None:
            raise ValueError(f"candidate가 없습니다: {candidate_id} (run_id={run_id})")

        # 제품당 1개 승인: 기존 승인 있으면 제거 후 재생성(단순/명확)
        await self._session.execute(delete(CTRRankerApproval).where(CTRRankerApproval.run_id == run_id))

        approval = CTRRankerApproval(
            run_id=run_id,
            candidate_id=candidate_id,
            approved_by_user_id=approved_by_user_id,
            note=note,
            approved_at=now_kst(),
        )
        self._session.add(approval)
        await self._session.commit()
        await self._session.refresh(approval)
        return approval


def build_candidate_rows_from_raw_and_topk(
    *,
    product_name: str,
    raw_dataset: dict[str, Any],
    topk_csv_text: str,
) -> list[dict[str, Any]]:
    """raw + topK CSV를 조합해 후보 row를 만든다. (DB 의존성 없는 순수 로직)

    반환 row 스키마:
    - title (str)
    - video_id (str | None)
    - thumbnail_url (str | None)
    - baseline_rank/baseline_score (int/float | None)
    - after_rank/after_score (int/float | None)
    - proxy_score (float | None)
    """
    if not product_name.strip():
        raise ValueError("product_name은 비어 있을 수 없습니다.")
    if "rows" not in raw_dataset:
        raise ValueError("raw_dataset에 rows가 없습니다.")

    title_map: dict[str, dict[str, Any]] = {}
    for row in raw_dataset.get("rows", []):
        video = row.get("video") or {}
        title = (video.get("title") or "").strip()
        if not title:
            continue
        if title in title_map:
            continue
        title_map[title] = {
            "video_id": video.get("id"),
            "thumbnail_url": video.get("thumbnail"),
            "proxy_score": row.get("proxy_score"),
        }

    baseline_by_title: dict[str, dict[str, Any]] = {}
    after_by_title: dict[str, dict[str, Any]] = {}

    reader = csv.DictReader(StringIO(topk_csv_text))
    if not reader.fieldnames:
        raise ValueError("topk_csv_text 헤더가 비어 있습니다.")
    expected = {"group_id", "variant", "rank", "score", "proxy_score", "title"}
    missing = expected - set(reader.fieldnames)
    if missing:
        raise ValueError(f"topk_csv_text에 필요한 컬럼이 없습니다: {sorted(missing)}")

    for row in reader:
        group_id = (row.get("group_id") or "").strip()
        if group_id != product_name:
            continue
        variant = (row.get("variant") or "").strip()
        title = (row.get("title") or "").strip()
        if not title:
            continue

        payload = {
            "rank": _safe_int(row.get("rank")),
            "score": _safe_float(row.get("score")),
            "proxy_score": _safe_float(row.get("proxy_score")),
        }
        if variant == "before":
            baseline_by_title[title] = payload
        elif variant == "after":
            after_by_title[title] = payload

    if not after_by_title:
        raise ValueError("after 후보가 없습니다. (product_name/topk_csv_text 확인 필요)")

    titles = set(baseline_by_title) | set(after_by_title)
    rows: list[dict[str, Any]] = []
    for title in titles:
        raw = title_map.get(title) or {}
        base_payload = baseline_by_title.get(title) or {}
        after_payload = after_by_title.get(title) or {}
        rows.append(
            {
                "title": title,
                "video_id": raw.get("video_id"),
                "thumbnail_url": raw.get("thumbnail_url"),
                "baseline_rank": base_payload.get("rank"),
                "baseline_score": base_payload.get("score"),
                "after_rank": after_payload.get("rank"),
                "after_score": after_payload.get("score"),
                "proxy_score": after_payload.get("proxy_score") or raw.get("proxy_score"),
            }
        )

    rows.sort(key=lambda r: (r.get("after_rank") is None, r.get("after_rank") or 10**9, r["title"]))
    return rows
