"""파이프라인 스케줄러 서비스 (async)"""

from contextlib import suppress
from datetime import datetime
from uuid import uuid4

import pytz
from croniter import croniter
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import get_settings
from core.exceptions import (
    InvalidCronError,
    ScheduleConflictError,
    ScheduleNotFoundError,
    SchedulerError,
)
from infrastructure.clients.scheduler_client import CloudSchedulerClient
from infrastructure.database.models import PipelineSchedule
from schemas.requests import ScheduleRequest
from utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


class SchedulerService:
    """파이프라인 스케줄 관리 서비스

    Cloud Scheduler Job과 DB를 동기화하여 파이프라인 스케줄을 관리합니다.
    DB를 source of truth로 사용하며, 보상 트랜잭션 패턴을 적용합니다.
    """

    def __init__(self, session: AsyncSession, scheduler_client: CloudSchedulerClient):
        self.session = session
        self.scheduler = scheduler_client

    async def create_schedule(self, req: ScheduleRequest, user_id: int) -> PipelineSchedule:
        """스케줄 생성 (GCP Job 생성 → DB 저장, 실패 시 GCP Job 삭제)"""
        cron = self._build_cron(req.days_of_week, req.hour, req.minute, req.frequency)
        self._validate_cron(cron)
        self._validate_timezone(req.timezone)

        # Cloud Scheduler Job ID는 [a-zA-Z\d_-] 정규식만 허용하므로 한글 등 제거
        import re
        safe_product_name = re.sub(r'[^a-zA-Z0-9_-]', '', req.product_name.replace(' ', '-'))
        gcp_job_id = f"pipeline-{safe_product_name}-{uuid4().hex[:8]}"
        # 만약 제품명이 한글로만 되어있어 safe_product_name이 비어있다면 대비
        if not safe_product_name:
             gcp_job_id = f"pipeline-{uuid4().hex[:12]}"
        webhook_url = f"{settings.app.app_url}/api/v1/webhooks/scheduler"

        payload = {
            "schedule_id": None,
            "product_name": req.product_name,
            **req.pipeline_config.model_dump(),
        }

        # 1. GCP Job 생성
        self.scheduler.create_job(
            job_id=gcp_job_id,
            cron_expression=cron,
            timezone=req.timezone,
            target_url=webhook_url,
            payload=payload,
        )

        # 2. DB 저장 (실패 시 GCP Job 삭제)
        try:
            next_exec = self._calc_next_execution(cron, req.timezone)

            schedule = PipelineSchedule(
                name=req.name,
                description=req.description,
                gcp_job_id=gcp_job_id,
                cron_expression=cron,
                timezone=req.timezone,
                product_name=req.product_name,
                config_json=req.pipeline_config.model_dump_json(),
                enabled=True,
                next_execution_at=next_exec,
                created_by=user_id,
            )
            self.session.add(schedule)
            await self.session.commit()
            await self.session.refresh(schedule)
        except Exception as e:
            # 보상 트랜잭션: GCP Job 삭제
            logger.error(f"DB 저장 실패, GCP Job 롤백: {gcp_job_id} - {e}")
            try:
                self.scheduler.delete_job(gcp_job_id)
            except Exception:
                logger.error(f"GCP Job 롤백 실패 (수동 삭제 필요): {gcp_job_id}")
            raise SchedulerError(message=f"스케줄 생성 실패: {e!s}", original_error=e) from e

        # 3. schedule_id를 payload에 추가하고 GCP Job 업데이트
        payload["schedule_id"] = schedule.id
        with suppress(Exception):
            # schedule_id는 선택적 필드이므로, 업데이트 실패 시에도 스케줄 자체는 유효하다.
            self.scheduler.update_job(gcp_job_id, cron, payload)

        logger.info(f"스케줄 생성 완료: {schedule.id} ({schedule.name})")
        return schedule

    async def update_schedule(
        self, schedule_id: int, req: ScheduleRequest, expected_version: int | None = None
    ) -> PipelineSchedule:
        """스케줄 수정 (Optimistic Locking + 보상 트랜잭션)"""
        schedule = await self._get_schedule(schedule_id)

        # Optimistic locking
        if expected_version is not None and schedule.version != expected_version:
            raise ScheduleConflictError(schedule_id)

        cron = self._build_cron(req.days_of_week, req.hour, req.minute, req.frequency)
        self._validate_cron(cron)
        self._validate_timezone(req.timezone)

        # 기존 상태 백업 (롤백용)
        old_cron = schedule.cron_expression
        old_timezone = schedule.timezone

        payload = {
            "schedule_id": schedule_id,
            "product_name": req.product_name,
            **req.pipeline_config.model_dump(),
        }

        # 1. GCP Job 수정
        self.scheduler.update_job(
            schedule.gcp_job_id, cron, payload, timezone=req.timezone
        )

        # 2. DB 수정 (실패 시 GCP Job 원복)
        try:
            next_exec = self._calc_next_execution(cron, req.timezone)

            result = await self.session.execute(
                update(PipelineSchedule)
                .where(
                    PipelineSchedule.id == schedule_id,
                    PipelineSchedule.version == schedule.version,
                    PipelineSchedule.deleted_at.is_(None),
                )
                .values(
                    name=req.name,
                    description=req.description,
                    cron_expression=cron,
                    timezone=req.timezone,
                    product_name=req.product_name,
                    config_json=req.pipeline_config.model_dump_json(),
                    next_execution_at=next_exec,
                    version=schedule.version + 1,
                )
            )

            if result.rowcount == 0:
                raise ScheduleConflictError(schedule_id)

            await self.session.commit()
        except ScheduleConflictError:
            raise
        except Exception as e:
            # 보상 트랜잭션: GCP Job 원복
            logger.error(f"DB 수정 실패, GCP Job 원복: {schedule.gcp_job_id} - {e}")
            try:
                old_payload = {"schedule_id": schedule_id, "product_name": schedule.product_name}
                self.scheduler.update_job(
                    schedule.gcp_job_id, old_cron, old_payload, timezone=old_timezone
                )
            except Exception:
                logger.error(f"GCP Job 원복 실패: {schedule.gcp_job_id}")
            raise SchedulerError(message=f"스케줄 수정 실패: {e!s}", original_error=e) from e

        # 갱신된 객체 반환
        await self.session.refresh(schedule)
        logger.info(f"스케줄 수정 완료: {schedule_id}")
        return schedule

    async def delete_schedule(self, schedule_id: int) -> None:
        """스케줄 삭제 (DB 소프트 삭제 → GCP Job 삭제)"""
        schedule = await self._get_schedule(schedule_id)

        # 1. DB 소프트 삭제
        schedule.deleted_at = datetime.now(pytz.timezone(schedule.timezone))
        schedule.enabled = False
        await self.session.commit()

        # 2. GCP Job 삭제 (실패해도 DB 기준으로 삭제 완료)
        try:
            self.scheduler.delete_job(schedule.gcp_job_id)
        except Exception as e:
            logger.warning(f"GCP Job 삭제 실패 (이미 없거나 오류): {schedule.gcp_job_id} - {e}")

        logger.info(f"스케줄 삭제 완료: {schedule_id}")

    async def toggle_schedule(self, schedule_id: int, enabled: bool) -> None:
        """스케줄 활성화/비활성화"""
        schedule = await self._get_schedule(schedule_id)

        # GCP Job 활성화/비활성화
        if enabled:
            self.scheduler.resume_job(schedule.gcp_job_id)
        else:
            self.scheduler.pause_job(schedule.gcp_job_id)

        # DB 업데이트
        schedule.enabled = enabled
        if enabled:
            schedule.next_execution_at = self._calc_next_execution(
                schedule.cron_expression, schedule.timezone
            )
        else:
            schedule.next_execution_at = None
        await self.session.commit()

        logger.info(f"스케줄 {'활성화' if enabled else '비활성화'}: {schedule_id}")

    async def update_next_execution(self, schedule_id: int) -> None:
        """Webhook 실행 후 next_execution_at 갱신"""
        schedule = await self._get_schedule(schedule_id)
        schedule.last_executed_at = datetime.now(pytz.timezone(schedule.timezone))
        schedule.next_execution_at = self._calc_next_execution(
            schedule.cron_expression, schedule.timezone
        )
        await self.session.commit()

    # --- Private helpers ---

    async def _get_schedule(self, schedule_id: int) -> PipelineSchedule:
        """스케줄 조회 (삭제되지 않은 것만)"""
        result = await self.session.execute(
            select(PipelineSchedule).where(
                PipelineSchedule.id == schedule_id,
                PipelineSchedule.deleted_at.is_(None),
            )
        )
        schedule = result.scalar_one_or_none()
        if not schedule:
            raise ScheduleNotFoundError(schedule_id)
        return schedule

    @staticmethod
    def _build_cron(
        days: list[int],
        hour: int,
        minute: int,
        frequency: str,
    ) -> str:
        """크론 표현식 생성

        Args:
            days: 요일 리스트 (0=월, 6=일)
            hour: 시간 (0-23)
            minute: 분 (0-59)
            frequency: 'daily' | 'weekly' | 'custom'

        Returns:
            크론 표현식 (예: "0 16 * * 1,3,5")
        """
        if frequency == "daily":
            return f"{minute} {hour} * * *"

        if days:
            # UI의 0=월을 크론의 1=월로 변환 (크론: 0=일, 1=월, ...)
            day_str = ",".join(str((d + 1) % 7) for d in sorted(days))
            return f"{minute} {hour} * * {day_str}"

        return f"{minute} {hour} * * *"

    @staticmethod
    def _validate_cron(cron: str) -> None:
        """크론 표현식 유효성 검증"""
        if not croniter.is_valid(cron):
            raise InvalidCronError(cron)

    @staticmethod
    def _validate_timezone(timezone: str) -> None:
        """타임존 유효성 검증"""
        if timezone not in pytz.all_timezones:
            raise SchedulerError(message=f"유효하지 않은 타임존입니다: {timezone}")

    @staticmethod
    def _calc_next_execution(cron: str, timezone: str) -> datetime:
        """다음 실행 시각 계산"""
        tz = pytz.timezone(timezone)
        now = datetime.now(tz)
        return croniter(cron, now).get_next(datetime)
