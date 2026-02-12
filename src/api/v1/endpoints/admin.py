from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from api.deps import CurrentUser, get_scheduler_client, require_role
from config.dependencies import get_services
from core.audit import record_audit_log
from core.exceptions import (
    ScheduleConflictError,
    ScheduleNotFoundError,
    SchedulerError,
)
from infrastructure.clients.scheduler_client import CloudSchedulerClient
from infrastructure.database.connection import get_db_session
from infrastructure.database.models import PipelineSchedule
from schemas.requests import RoleCreateRequest, ScheduleRequest, TeamCreateRequest
from schemas.responses import ScheduleResponse
from services.admin_service import AdminService
from services.notification_service import send_slack_notification
from services.scheduler_service import SchedulerService
from utils.cache import clear_all_api_cache, get_cache_stats
from utils.logger import log_feature_end, log_feature_fail, log_feature_start


class ToggleRequest(BaseModel):
    enabled: bool


class EvaluatePredictionsRequest(BaseModel):
    """회귀 메트릭(MAE, RMSE 등) 평가 요청"""

    predictions: list[float]
    actuals: list[float]


class EvaluateRankingRequest(BaseModel):
    """순위 메트릭(NDCG@K) 평가 요청"""

    predicted_ranking: list[str]
    ideal_ranking: list[str]
    k: int = 5


class CompareModelsRequest(BaseModel):
    """두 모델 예측 비교 요청"""

    model_a_name: str
    model_a_predictions: list[float]
    model_b_name: str
    model_b_predictions: list[float]
    actuals: list[float]


router = APIRouter()


@router.get("/notifications/slack-test")
async def slack_test(
    user: Annotated[CurrentUser, Depends(require_role(["admin"]))],
):
    """Slack Incoming Webhook 연결 테스트 (관리자 전용)."""
    log_feature_start("admin_slack_test", getattr(user, "email", ""))
    try:
        send_slack_notification(
            f"[Nexloop] Slack test\n"
            f"- user: {getattr(user, 'email', '')}\n"
            f"- tier: {getattr(user, 'tier', '')}\n"
            f"- env: {getattr(get_services(), 'settings', None).env if getattr(get_services(), 'settings', None) else 'unknown'}"
        )
        log_feature_end("admin_slack_test")
        return {"status": "ok"}
    except Exception as e:
        # send_slack_notification 자체는 예외를 전파하지 않지만,
        # 향후 구현 변경에 대비해 방어적으로 처리한다.
        log_feature_fail("admin_slack_test", str(e)[:200])
        raise HTTPException(status_code=500, detail="Slack test failed") from e


@router.get("/cache/stats")
async def get_cache_stats_endpoint(
    user: Annotated[CurrentUser, Depends(require_role(["admin"]))],
):
    log_feature_start("admin_get_cache_stats")
    stats = get_cache_stats()
    log_feature_end("admin_get_cache_stats")
    return {"stats": stats}


@router.post("/cache/clear")
async def clear_cache_endpoint(
    user: Annotated[CurrentUser, Depends(require_role(["admin"]))],
):
    log_feature_start("admin_clear_cache")
    cleared = clear_all_api_cache()
    log_feature_end("admin_clear_cache")
    return {"cleared": cleared}


@router.post("/evaluate-model/predictions")
async def evaluate_model_predictions(
    request: EvaluatePredictionsRequest,
    user: Annotated[CurrentUser, Depends(require_role(["admin"]))],
):
    """예측값과 실제값으로 회귀 메트릭(MAE, RMSE, MAPE, R²) 계산."""
    log_feature_start("admin_evaluate_model", "predictions")
    if len(request.predictions) != len(request.actuals):
        log_feature_fail("admin_evaluate_model", "predictions/actuals length mismatch")
        raise HTTPException(
            status_code=400,
            detail="predictions와 actuals 길이가 같아야 합니다.",
        )
    from services.model_evaluator import ModelEvaluator

    evaluator = ModelEvaluator()
    result = evaluator.evaluate_predictions(request.predictions, request.actuals)
    log_feature_end("admin_evaluate_model")
    return result


@router.post("/evaluate-model/ranking")
async def evaluate_model_ranking(
    request: EvaluateRankingRequest,
    user: Annotated[CurrentUser, Depends(require_role(["admin"]))],
):
    """예측 순위와 이상 순위로 NDCG@K 계산."""
    log_feature_start("admin_evaluate_model", "ranking")
    from services.model_evaluator import ModelEvaluator

    evaluator = ModelEvaluator()
    result = evaluator.evaluate_ranking(
        request.predicted_ranking,
        request.ideal_ranking,
        k=request.k,
    )
    log_feature_end("admin_evaluate_model")
    return result


@router.post("/evaluate-model/compare")
async def evaluate_model_compare(
    request: CompareModelsRequest,
    user: Annotated[CurrentUser, Depends(require_role(["admin"]))],
):
    """두 모델의 예측을 실제값과 비교하여 메트릭·승자 반환."""
    log_feature_start("admin_evaluate_model", "compare")
    n = len(request.actuals)
    if (
        len(request.model_a_predictions) != n
        or len(request.model_b_predictions) != n
    ):
        log_feature_fail("admin_evaluate_model", "predictions/actuals length mismatch")
        raise HTTPException(
            status_code=400,
            detail="모든 예측 리스트는 actuals와 길이가 같아야 합니다.",
        )
    from services.model_evaluator import ModelEvaluator

    evaluator = ModelEvaluator()
    result = evaluator.compare_models(
        request.model_a_name,
        request.model_a_predictions,
        request.model_b_name,
        request.model_b_predictions,
        request.actuals,
    )
    log_feature_end("admin_evaluate_model")
    return result


# Dependency
async def get_admin_service(
    session=Depends(get_db_session),
    scheduler_client: CloudSchedulerClient = Depends(get_scheduler_client),
) -> AdminService:
    services = get_services()
    return AdminService(session, scheduler_client, services.storage_service)


@router.get("/roles")
async def list_roles(
    user: Annotated[CurrentUser, Depends(require_role(["admin"]))],
    service: AdminService = Depends(get_admin_service),
):
    log_feature_start("admin_list_roles")
    roles = await service.get_roles()
    log_feature_end("admin_list_roles")
    return {
        "roles": [
            {"id": role.id, "name": role.name, "description": role.description}
            for role in roles
        ]
    }


@router.post("/roles")
async def create_role(
    request: RoleCreateRequest,
    user: Annotated[CurrentUser, Depends(require_role(["admin"]))],
    service: AdminService = Depends(get_admin_service),
):
    log_feature_start("admin_create_role", request.name)
    try:
        role = await service.create_role(
            name=request.name,
            description=request.description,
            actor_email=getattr(user, "email", "unknown"),
            actor_role=getattr(user, "role", "editor"),
        )
        log_feature_end("admin_create_role")
        return {"id": role.id, "name": role.name, "description": role.description}
    except Exception as e:
        log_feature_fail("admin_create_role", str(e))
        raise


@router.get("/teams")
async def list_teams(
    user: Annotated[CurrentUser, Depends(require_role(["admin"]))],
    service: AdminService = Depends(get_admin_service),
):
    log_feature_start("admin_list_teams")
    teams = await service.get_teams()
    log_feature_end("admin_list_teams")
    return {"teams": [{"id": team.id, "name": team.name} for team in teams]}


@router.post("/teams")
async def create_team(
    request: TeamCreateRequest,
    user: Annotated[CurrentUser, Depends(require_role(["admin"]))],
    service: AdminService = Depends(get_admin_service),
):
    log_feature_start("admin_create_team", request.name)
    try:
        team = await service.create_team(
            name=request.name,
            actor_email=getattr(user, "email", "unknown"),
            actor_role=getattr(user, "role", "editor"),
        )
        log_feature_end("admin_create_team")
        return {"id": team.id, "name": team.name}
    except Exception as e:
        log_feature_fail("admin_create_team", str(e))
        raise


@router.get("/audit-logs")
async def list_audit_logs(
    user: Annotated[CurrentUser, Depends(require_role(["admin"]))],
    limit: int = 50,
    service: AdminService = Depends(get_admin_service),
):
    log_feature_start("admin_list_audit_logs", f"limit={limit}")
    logs = await service.get_audit_logs(limit=limit)
    log_feature_end("admin_list_audit_logs")
    return {
        "logs": [
            {
                "id": log.id,
                "action": log.action,
                "actor_email": log.actor_email,
                "actor_role": log.actor_role,
                "entity_type": log.entity_type,
                "entity_id": log.entity_id,
                "metadata": log.meta_json,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log in logs
        ]
    }


@router.get("/gcs/metadata")
async def get_gcs_metadata(
    user: Annotated[CurrentUser, Depends(require_role(["admin"]))],
    gcs_path: str | None = None,
    prefix: str | None = None,
    limit: int = 50,
):
    services = get_services()
    storage = services.storage_service
    bucket_name = storage.bucket_name

    log_feature_start("admin_get_gcs_metadata", gcs_path or prefix)
    if not gcs_path and not prefix:
        log_feature_fail("admin_get_gcs_metadata", "no path or prefix")
        raise HTTPException(
            status_code=400, detail="gcs_path 또는 prefix가 필요합니다."
        )

    def _parse_gcs_path(raw: str) -> tuple[str | None, str]:
        raw = raw.strip()
        if raw.startswith("gs://"):
            parts = raw[5:].split("/", 1)
            bucket = parts[0]
            object_path = parts[1] if len(parts) == 2 else ""
            return bucket, object_path
        return None, raw.lstrip("/")

    if gcs_path:
        bucket, object_path = _parse_gcs_path(gcs_path)
        if bucket and bucket_name and bucket != bucket_name:
            raise HTTPException(status_code=400, detail="Bucket mismatch")
        metadata = storage.get_metadata(object_path)
        if not metadata:
            raise HTTPException(status_code=404, detail="Object not found")
        url = getattr(storage, "get_signed_url", lambda p: None)(object_path)
        log_feature_end("admin_get_gcs_metadata", extra_detail="single_object")
        return {"items": [{**metadata, "signed_url": url}]}

    bucket, object_prefix = _parse_gcs_path(prefix or "")
    if bucket and bucket_name and bucket != bucket_name:
        raise HTTPException(status_code=400, detail="Bucket mismatch")

    paths = storage.list_files(object_prefix)[: max(1, min(limit, 200))]
    items = []
    for path in paths:
        metadata = storage.get_metadata(path)
        if not metadata:
            continue
        url = getattr(storage, "get_signed_url", lambda p: None)(path)
        items.append({**metadata, "signed_url": url})
    log_feature_end("admin_get_gcs_metadata")
    return {"items": items}


@router.get("/prompt-logs")
async def get_prompt_logs(
    user: Annotated[CurrentUser, Depends(require_role(["admin"]))], limit: int = 20
):
    log_feature_start("admin_get_prompt_logs", f"limit={limit}")
    services = get_services()
    history = services.history_service.get_history_list()
    logs = []
    for item in history[: max(1, min(limit, 50))]:
        record = services.history_service.load_history(item.get("id", ""))
        prompt_log = getattr(record, "prompt_log", None) if record else None
        logs.append(
            {
                "history_id": item.get("id"),
                "product_name": item.get("product_name", ""),
                "executed_at": item.get("executed_at", ""),
                "prompt_log": prompt_log,
            }
        )
    log_feature_end("admin_get_prompt_logs")
    return {"logs": logs}


# 스케줄 목록 조회
@router.get("/schedules", response_model=list[ScheduleResponse])
async def list_schedules(
    user: Annotated[CurrentUser, Depends(require_role(["admin"]))],
    session=Depends(get_db_session),
):
    """스케줄 목록 조회"""
    log_feature_start("admin_list_schedules")
    result = await session.execute(
        select(PipelineSchedule)
        .where(PipelineSchedule.deleted_at.is_(None))
        .order_by(PipelineSchedule.id.desc())
    )
    schedules = result.scalars().all()
    log_feature_end("admin_list_schedules")
    return [ScheduleResponse.model_validate(s) for s in schedules]


# 스케줄 생성
@router.post("/schedules", response_model=ScheduleResponse)
async def create_schedule(
    request: ScheduleRequest,
    user: Annotated[CurrentUser, Depends(require_role(["admin"]))],
    session=Depends(get_db_session),
    scheduler_client: CloudSchedulerClient = Depends(get_scheduler_client),
):
    """스케줄 생성"""
    log_feature_start("admin_create_schedule", request.name)
    service = SchedulerService(session, scheduler_client)
    try:
        schedule = await service.create_schedule(request, user.id)
        await record_audit_log(
            session=session,
            action="create_schedule",
            actor_email=user.email,
            actor_role=user.role,
            entity_type="schedule",
            entity_id=str(schedule.id),
            metadata={"name": schedule.name, "product": schedule.product_name},
        )
        log_feature_end("admin_create_schedule")
        return ScheduleResponse.model_validate(schedule)
    except SchedulerError as e:
        log_feature_fail("admin_create_schedule", str(e))
        raise HTTPException(status_code=400, detail=str(e)) from e


# 스케줄 수정
@router.put("/schedules/{schedule_id}", response_model=ScheduleResponse)
async def update_schedule(
    schedule_id: int,
    request: ScheduleRequest,
    user: Annotated[CurrentUser, Depends(require_role(["admin"]))],
    session=Depends(get_db_session),
    scheduler_client: CloudSchedulerClient = Depends(get_scheduler_client),
):
    """스케줄 수정"""
    log_feature_start("admin_update_schedule", f"id={schedule_id} name={request.name}")
    service = SchedulerService(session, scheduler_client)
    try:
        schedule = await service.update_schedule(schedule_id, request)
        await record_audit_log(
            session=session,
            action="update_schedule",
            actor_email=user.email,
            actor_role=user.role,
            entity_type="schedule",
            entity_id=str(schedule.id),
            metadata={"name": schedule.name},
        )
        log_feature_end("admin_update_schedule")
        return ScheduleResponse.model_validate(schedule)
    except ScheduleConflictError as e:
        log_feature_fail("admin_update_schedule", "conflict")
        raise HTTPException(status_code=409, detail=str(e)) from e
    except (ScheduleNotFoundError, SchedulerError) as e:
        log_feature_fail("admin_update_schedule", str(e))
        raise HTTPException(status_code=400, detail=str(e)) from e


# 스케줄 삭제
@router.delete("/schedules/{schedule_id}")
async def delete_schedule(
    schedule_id: int,
    user: Annotated[CurrentUser, Depends(require_role(["admin"]))],
    session=Depends(get_db_session),
    scheduler_client: CloudSchedulerClient = Depends(get_scheduler_client),
):
    """스케줄 삭제"""
    log_feature_start("admin_delete_schedule", f"id={schedule_id}")
    service = SchedulerService(session, scheduler_client)
    try:
        await service.delete_schedule(schedule_id)
        await record_audit_log(
            session=session,
            action="delete_schedule",
            actor_email=user.email,
            actor_role=user.role,
            entity_type="schedule",
            entity_id=str(schedule_id),
            metadata={},
        )
        log_feature_end("admin_delete_schedule")
        return {"message": "Schedule deleted"}
    except ScheduleNotFoundError as e:
        log_feature_fail("admin_delete_schedule", f"Not found: {schedule_id}")
        raise HTTPException(status_code=404, detail=str(e)) from e
    except SchedulerError as e:
        log_feature_fail("admin_delete_schedule", str(e))
        raise HTTPException(status_code=400, detail=str(e)) from e


# 스케줄 활성화/비활성화
@router.patch("/schedules/{schedule_id}/toggle")
async def toggle_schedule(
    schedule_id: int,
    body: ToggleRequest,
    user: Annotated[CurrentUser, Depends(require_role(["admin"]))],
    session=Depends(get_db_session),
    scheduler_client: CloudSchedulerClient = Depends(get_scheduler_client),
):
    """스케줄 활성화/비활성화"""
    log_feature_start("admin_toggle_schedule", f"id={schedule_id} enabled={body.enabled}")
    service = SchedulerService(session, scheduler_client)
    try:
        await service.toggle_schedule(schedule_id, body.enabled)
        await record_audit_log(
            session=session,
            action="toggle_schedule",
            actor_email=user.email,
            actor_role=user.role,
            entity_type="schedule",
            entity_id=str(schedule_id),
            metadata={"enabled": body.enabled},
        )
        log_feature_end("admin_toggle_schedule")
        return {"message": f"Schedule {'enabled' if body.enabled else 'disabled'}"}
    except ScheduleNotFoundError as e:
        log_feature_fail("admin_toggle_schedule", f"Not found: {schedule_id}")
        raise HTTPException(status_code=404, detail=str(e)) from e
    except SchedulerError as e:
        log_feature_fail("admin_toggle_schedule", str(e))
        raise HTTPException(status_code=400, detail=str(e)) from e
