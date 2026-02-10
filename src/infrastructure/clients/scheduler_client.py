"""Google Cloud Scheduler API 클라이언트"""

import json
from typing import Any

from google.api_core.exceptions import (
    AlreadyExists,
    DeadlineExceeded,
    NotFound,
    PermissionDenied,
    ResourceExhausted,
    ServiceUnavailable,
)
from google.cloud import scheduler_v1
from google.protobuf.duration_pb2 import Duration

from core.exceptions import (
    ScheduleDuplicateError,
    ScheduleNotFoundError,
    SchedulerAuthError,
    SchedulerError,
    SchedulerQuotaError,
)
from utils.logger import get_logger
from utils.retry import retry_on_error

logger = get_logger(__name__)


def _map_gcp_exception(exc: Exception, context: str = "") -> SchedulerError:
    """GCP 예외를 Scheduler 커스텀 예외로 매핑"""
    if isinstance(exc, NotFound):
        return ScheduleNotFoundError(original_error=exc)
    if isinstance(exc, AlreadyExists):
        return ScheduleDuplicateError(original_error=exc)
    if isinstance(exc, PermissionDenied):
        return SchedulerAuthError(original_error=exc)
    if isinstance(exc, ResourceExhausted):
        return SchedulerQuotaError(original_error=exc)
    return SchedulerError(
        message=f"Cloud Scheduler 오류 ({context}): {exc!s}",
        original_error=exc,
    )


class CloudSchedulerClient:
    """Cloud Scheduler API 클라이언트

    GCP Cloud Scheduler Job을 생성, 수정, 삭제, 일시정지, 재개하는 기능을 제공합니다.
    """

    def __init__(self, project_id: str, location: str, service_account_email: str = ""):
        """
        Args:
            project_id: GCP 프로젝트 ID
            location: Cloud Scheduler 리전 (예: asia-northeast3)
            service_account_email: OIDC 토큰용 서비스 계정 이메일
        """
        self.client = scheduler_v1.CloudSchedulerClient()
        self.project_id = project_id
        self.location = location
        self.service_account_email = service_account_email
        self.parent = f"projects/{project_id}/locations/{location}"

    @retry_on_error(max_attempts=3, base_delay=1.0)
    def create_job(
        self,
        job_id: str,
        cron_expression: str,
        timezone: str,
        target_url: str,
        payload: dict[str, Any],
    ) -> str:
        """Cloud Scheduler Job 생성

        Args:
            job_id: Job 고유 ID
            cron_expression: 크론 표현식 (예: "0 16 * * *")
            timezone: 타임존 (예: "Asia/Seoul")
            target_url: HTTP 타겟 URL
            payload: HTTP 요청 본문 (dict)

        Returns:
            생성된 Job의 전체 이름

        Raises:
            ScheduleDuplicateError: 중복 Job ID
            SchedulerAuthError: 인증/권한 실패
            SchedulerQuotaError: 할당량 초과
            SchedulerError: 기타 GCP 오류
        """
        http_target = scheduler_v1.HttpTarget(
            uri=target_url,
            http_method=scheduler_v1.HttpMethod.POST,
            headers={"Content-Type": "application/json"},
            body=json.dumps(payload).encode(),
        )

        # OIDC 토큰 설정 (서비스 계정이 설정된 경우 && https인 경우)
        # Cloud Scheduler는 http 대상에 대해 OIDC 토큰을 보낼 수 없음
        if self.service_account_email and target_url.startswith("https://"):
            http_target.oidc_token = scheduler_v1.OidcToken(
                service_account_email=self.service_account_email,
                audience=target_url,
            )
        elif self.service_account_email:
            logger.warning(
                f"URL이 https가 아니므로 OIDC 토큰을 설정하지 않습니다 ({target_url}). "
                "로컬 환경이 아니라면 APP_URL을 https로 설정해야 합니다."
            )

        job = scheduler_v1.Job(
            name=f"{self.parent}/jobs/{job_id}",
            schedule=cron_expression,
            time_zone=timezone,
            http_target=http_target,
            attempt_deadline=Duration(seconds=180),
        )

        try:
            response = self.client.create_job(
                request=scheduler_v1.CreateJobRequest(
                    parent=self.parent,
                    job=job,
                )
            )
            logger.info(f"Cloud Scheduler Job 생성 완료: {response.name}")
            return response.name
        except (NotFound, AlreadyExists, PermissionDenied, ResourceExhausted,
                ServiceUnavailable, DeadlineExceeded) as e:
            raise _map_gcp_exception(e, "create_job") from e

    @retry_on_error(max_attempts=3, base_delay=1.0)
    def update_job(
        self,
        job_id: str,
        cron_expression: str,
        payload: dict[str, Any],
        timezone: str | None = None,
    ) -> None:
        """Job 수정

        Args:
            job_id: Job ID
            cron_expression: 새로운 크론 표현식
            payload: 새로운 HTTP 요청 본문
            timezone: 새로운 타임존 (None이면 변경 없음)
        """
        name = f"{self.parent}/jobs/{job_id}"

        try:
            job = self.client.get_job(name=name)
            job.schedule = cron_expression
            if job.http_target:
                job.http_target.body = json.dumps(payload).encode()
            if timezone:
                job.time_zone = timezone
            self.client.update_job(job=job)
            logger.info(f"Cloud Scheduler Job 수정 완료: {name}")
        except (NotFound, PermissionDenied, ResourceExhausted,
                ServiceUnavailable, DeadlineExceeded) as e:
            raise _map_gcp_exception(e, "update_job") from e

    @retry_on_error(max_attempts=3, base_delay=1.0)
    def delete_job(self, job_id: str) -> None:
        """Job 삭제

        Args:
            job_id: Job ID
        """
        name = f"{self.parent}/jobs/{job_id}"
        try:
            self.client.delete_job(name=name)
            logger.info(f"Cloud Scheduler Job 삭제 완료: {name}")
        except NotFound:
            logger.warning(f"삭제할 Job이 이미 없음: {name}")
        except (PermissionDenied, ResourceExhausted,
                ServiceUnavailable, DeadlineExceeded) as e:
            raise _map_gcp_exception(e, "delete_job") from e

    @retry_on_error(max_attempts=3, base_delay=1.0)
    def pause_job(self, job_id: str) -> None:
        """Job 일시정지"""
        name = f"{self.parent}/jobs/{job_id}"
        try:
            self.client.pause_job(name=name)
            logger.info(f"Cloud Scheduler Job 일시정지: {name}")
        except (NotFound, PermissionDenied, ServiceUnavailable, DeadlineExceeded) as e:
            raise _map_gcp_exception(e, "pause_job") from e

    @retry_on_error(max_attempts=3, base_delay=1.0)
    def resume_job(self, job_id: str) -> None:
        """Job 재개"""
        name = f"{self.parent}/jobs/{job_id}"
        try:
            self.client.resume_job(name=name)
            logger.info(f"Cloud Scheduler Job 재개: {name}")
        except (NotFound, PermissionDenied, ServiceUnavailable, DeadlineExceeded) as e:
            raise _map_gcp_exception(e, "resume_job") from e

    def get_job(self, job_id: str) -> scheduler_v1.Job:
        """Job 정보 조회"""
        name = f"{self.parent}/jobs/{job_id}"
        try:
            return self.client.get_job(name=name)
        except (NotFound, PermissionDenied) as e:
            raise _map_gcp_exception(e, "get_job") from e
