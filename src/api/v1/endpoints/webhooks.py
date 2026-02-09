"""Webhook 엔드포인트

Cloud Scheduler와 같은 외부 서비스에서 호출하는 엔드포인트입니다.
GCP OIDC 토큰으로 인증합니다.
"""

import os
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request

from infrastructure.database.connection import get_db_session
from schemas.requests import PipelineRequest
from services.pipeline_runner import execute_pipeline_task, init_pipeline_status
from utils.logger import (
    get_logger,
    log_feature_end,
    log_feature_fail,
    log_feature_start,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


async def verify_oidc_token(request: Request):
    """GCP OIDC 토큰 검증

    Cloud Scheduler가 보내는 Authorization 헤더의 OIDC 토큰을 검증합니다.
    로컬 개발 시에는 검증을 건너뜁니다.
    """
    from config.settings import get_settings

    settings = get_settings()

    # Cloud Run에서는 외부 요청이 HTTPS여도 컨테이너 내부에서는 request.url이 http로 보일 수 있다.
    # (TLS는 프록시에서 종료) 따라서 X-Forwarded-Proto를 우선한다.
    forwarded_proto = (request.headers.get("x-forwarded-proto") or "").lower()
    scheme = (request.url.scheme or "").lower()
    is_https = forwarded_proto == "https" or scheme == "https"

    # 로컬 개발 환경에서는 OIDC 검증을 건너뛴다.
    # Cloud Run에서는 scheduler_service_account가 설정돼 있으면 항상 OIDC 검증을 수행한다.
    is_cloud_run = bool(os.environ.get("K_SERVICE"))
    if not is_cloud_run:
        return None

    if not settings.app.scheduler_service_account:
        logger.warning("SCHEDULER_SERVICE_ACCOUNT 미설정: OIDC 검증을 건너뜁니다.")
        return None

    if not is_https:
        # Cloud Run 내부에서 http로 보이는 경우라도, forwarded header가 없으면 위험 신호.
        logger.warning("HTTPS로 확인되지 않아 OIDC 검증을 진행할 수 없습니다.")
        raise HTTPException(status_code=403, detail="Insecure request")

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=403, detail="Missing OIDC token")

    token = auth_header.removeprefix("Bearer ")

    try:
        from google.auth.transport import requests as google_requests
        from google.oauth2 import id_token

        audience = f"{settings.app.app_url}/api/v1/webhooks/scheduler"
        claims = id_token.verify_oauth2_token(
            token, google_requests.Request(), audience=audience
        )
        logger.info(f"OIDC 인증 성공: {claims.get('email', 'unknown')}")
        return claims
    except Exception as e:
        logger.error(f"OIDC 토큰 검증 실패: {e}")
        raise HTTPException(status_code=403, detail="Invalid OIDC token") from e


@router.post("/scheduler", dependencies=[Depends(verify_oidc_token)])
async def scheduler_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    session=Depends(get_db_session),
):
    """Cloud Scheduler에서 호출하는 Webhook

    Cloud Scheduler Job이 실행될 때 이 엔드포인트를 호출하여 파이프라인을 실행합니다.

    요청 본문:
        - schedule_id: 스케줄 ID (선택)
        - product_name: 제품명 (필수)
        - 기타 PipelineRequest 파라미터들
    """
    log_feature_start("webhook_pipeline", "scheduler trigger")
    payload = await request.json()
    schedule_id = payload.get("schedule_id")
    product_name = payload.get("product_name")

    if not product_name:
        log_feature_fail("webhook_pipeline", "product_name is required")
        raise HTTPException(status_code=400, detail="product_name is required")

    # PipelineRequest 재구성
    pipeline_req = PipelineRequest(
        product_name=product_name,
        youtube_count=payload.get("youtube_count", 3),
        naver_count=payload.get("naver_count", 10),
        include_comments=payload.get("include_comments", True),
        generate_social=payload.get("generate_social", True),
        generate_video=payload.get("generate_video", True),
        generate_thumbnails=payload.get("generate_thumbnails", True),
        export_to_notion=payload.get("export_to_notion", True),
        thumbnail_count=payload.get("thumbnail_count"),
        thumbnail_styles=payload.get("thumbnail_styles"),
    )

    # Task ID 생성 및 파이프라인 실행
    task_id = str(uuid4())
    init_pipeline_status(task_id, product_name)
    background_tasks.add_task(execute_pipeline_task, pipeline_req, task_id)

    # next_execution_at 갱신
    if schedule_id:
        try:
            from api.deps import get_scheduler_client
            from services.scheduler_service import SchedulerService

            scheduler_client = get_scheduler_client()
            service = SchedulerService(session, scheduler_client)
            await service.update_next_execution(schedule_id)
        except Exception as e:
            logger.warning(f"next_execution_at 갱신 실패 (schedule_id={schedule_id}): {e}")

    logger.info(f"Webhook 파이프라인 실행: task_id={task_id}, product={product_name}")
    log_feature_end("webhook_pipeline", extra_detail=f"task_id={task_id}")

    return {
        "status": "triggered",
        "task_id": task_id,
        "schedule_id": schedule_id,
        "product_name": product_name,
    }
