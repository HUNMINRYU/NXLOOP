from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from infrastructure.database.connection import AsyncSessionFactory
from infrastructure.database.connection import engine as db_engine
from infrastructure.database.models import PipelineTask
from utils.logger import get_logger

logger = get_logger(__name__)


class PipelineTaskService:
    """파이프라인 상태/결과를 DB에 best-effort로 저장/조회한다.

    목표:
    - Cloud Run 다중 인스턴스에서도 /status, /result가 404로 튀지 않게 하기
    - 테이블이 아직 없거나(DB 마이그레이션 전) DB가 불안정하면 자동으로 degrade
    """

    _table_checked: bool = False
    _last_ensure_attempt_at: float = 0.0
    _ensure_retry_interval_sec: float = 60.0

    async def _ensure_table(self) -> None:
        """pipeline_tasks 테이블이 없으면(특히 운영에서 마이그레이션 누락 시) best-effort로 생성한다.

        NOTE:
        - 원칙적으로는 Alembic 마이그레이션이 정답.
        - 하지만 배포 직후 즉시 안정화가 필요한 상황에서 404 튐을 막기 위한 응급 장치로 둔다.
        - 권한 부족/네트워크 문제 등으로 실패해도 호출자는 계속 진행한다.
        """
        if self._table_checked:
            return

        now = time.monotonic()
        if now - self._last_ensure_attempt_at < self._ensure_retry_interval_sec:
            return
        self._last_ensure_attempt_at = now

        try:
            async with db_engine.begin() as conn:
                await conn.run_sync(PipelineTask.__table__.create, checkfirst=True)
            # create(checkfirst=True)가 성공했으면 이후부터는 재시도하지 않는다.
            self._table_checked = True
        except Exception as exc:
            logger.warning(f"pipeline_tasks table ensure skipped: {exc}")

    async def upsert_status(self, status: dict[str, Any]) -> None:
        task_id = str(status.get("task_id") or "")
        if not task_id:
            return

        await self._ensure_table()

        product = str(status.get("product") or status.get("product_name") or "")
        state = str(status.get("status") or "")
        message = str(status.get("message") or "")
        now = datetime.now(timezone.utc)

        try:
            async with AsyncSessionFactory() as session:
                row = await session.get(PipelineTask, task_id)
                payload = PipelineTask.dumps(status)
                if row is None:
                    row = PipelineTask(
                        task_id=task_id,
                        product_name=product or "unknown",
                        status=state or "queued",
                        message=message,
                        status_json=payload,
                        created_at=now,
                        updated_at=now,
                    )
                    session.add(row)
                else:
                    row.product_name = product or row.product_name
                    row.status = state or row.status
                    row.message = message
                    row.status_json = payload
                    row.updated_at = now
                await session.commit()
        except SQLAlchemyError as exc:
            logger.warning(f"pipeline_tasks upsert_status skipped: {exc}")

    async def upsert_result(self, task_id: str, result: dict[str, Any]) -> None:
        task_id = str(task_id or "")
        if not task_id:
            return
        now = datetime.now(timezone.utc)

        await self._ensure_table()

        try:
            async with AsyncSessionFactory() as session:
                row = await session.get(PipelineTask, task_id)
                if row is None:
                    # 상태가 저장되지 않은 채 결과만 먼저 들어오는 케이스도 방어
                    row = PipelineTask(
                        task_id=task_id,
                        product_name=str(result.get("product_name") or "unknown"),
                        status="success" if result.get("success") else "failed",
                        message="",
                        status_json=PipelineTask.dumps({}),
                        result_json=PipelineTask.dumps(result),
                        created_at=now,
                        updated_at=now,
                    )
                    session.add(row)
                else:
                    row.result_json = PipelineTask.dumps(result)
                    row.updated_at = now
                await session.commit()
        except SQLAlchemyError as exc:
            logger.warning(f"pipeline_tasks upsert_result skipped: {exc}")

    async def get_status(self, task_id: str) -> dict[str, Any] | None:
        task_id = str(task_id or "")
        if not task_id:
            return None
        await self._ensure_table()
        try:
            async with AsyncSessionFactory() as session:
                row = await session.get(PipelineTask, task_id)
                if row is None:
                    return None
                return json.loads(row.status_json or "{}")
        except (SQLAlchemyError, json.JSONDecodeError) as exc:
            logger.warning(f"pipeline_tasks get_status skipped: {exc}")
            return None

    async def get_result(self, task_id: str) -> dict[str, Any] | None:
        task_id = str(task_id or "")
        if not task_id:
            return None
        await self._ensure_table()
        try:
            async with AsyncSessionFactory() as session:
                row = await session.get(PipelineTask, task_id)
                if row is None or not row.result_json:
                    return None
                return json.loads(row.result_json or "{}")
        except (SQLAlchemyError, json.JSONDecodeError) as exc:
            logger.warning(f"pipeline_tasks get_result skipped: {exc}")
            return None

    async def list_recent(self, limit: int = 50) -> list[dict[str, Any]]:
        lim = max(1, min(int(limit), 200))
        await self._ensure_table()
        try:
            async with AsyncSessionFactory() as session:
                stmt = select(PipelineTask).order_by(PipelineTask.updated_at.desc()).limit(lim)
                rows = (await session.execute(stmt)).scalars().all()
                return [
                    {
                        "task_id": r.task_id,
                        "product": r.product_name,
                        "status": r.status,
                        "message": r.message,
                        "created_at": r.created_at.isoformat() if r.created_at else "",
                        "updated_at": r.updated_at.isoformat() if r.updated_at else "",
                    }
                    for r in rows
                ]
        except SQLAlchemyError as exc:
            logger.warning(f"pipeline_tasks list_recent skipped: {exc}")
            return []
