from __future__ import annotations

import json
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.models import ModelEvalReport


class ModelEvalReportService:
    """모델 평가 리포트 요약 저장/조회 서비스."""

    REPORT_TYPE_CTR_OFFLINE_EVAL = "ctr_offline_eval"

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert_report(
        self,
        *,
        report_type: str,
        report_date: date,
        dataset_counts: dict[str, Any],
        cls_metrics: dict[str, Any],
        reg_metrics: dict[str, Any],
        baseline_metrics: dict[str, Any],
        artifact_gcs_path: str | None = None,
        notion_url: str | None = None,
    ) -> ModelEvalReport:
        """(report_type, report_date) 기준으로 upsert."""
        stmt = select(ModelEvalReport).where(
            ModelEvalReport.report_type == report_type,
            ModelEvalReport.report_date == report_date,
        )
        row = (await self._session.execute(stmt)).scalars().first()

        if row is None:
            row = ModelEvalReport(
                report_type=report_type,
                report_date=report_date,
            )
            self._session.add(row)

        row.dataset_counts_json = json.dumps(dataset_counts or {}, ensure_ascii=False, separators=(",", ":"))
        row.cls_metrics_json = json.dumps(cls_metrics or {}, ensure_ascii=False, separators=(",", ":"))
        row.reg_metrics_json = json.dumps(reg_metrics or {}, ensure_ascii=False, separators=(",", ":"))
        row.baseline_metrics_json = json.dumps(baseline_metrics or {}, ensure_ascii=False, separators=(",", ":"))
        row.artifact_gcs_path = artifact_gcs_path
        row.notion_url = notion_url

        await self._session.commit()
        await self._session.refresh(row)
        return row

