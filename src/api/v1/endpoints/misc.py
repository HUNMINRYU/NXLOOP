import asyncio
import json
from datetime import datetime, time, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import OptionalUser, require_tier
from config.constants import TIER_POLICIES
from config.dependencies import get_services
from config.settings import get_settings
from infrastructure.database.connection import get_db_session
from infrastructure.database.models import KST, UserDailyChatUsage, now_kst
from schemas.requests import ChatRequest, LeadRequest, RefreshUrlRequest
from utils.file_store import ensure_output_dir
from utils.logger import log_feature_end, log_feature_fail, log_feature_start
from utils.rate_limit import check_rate_limit, get_remaining_requests

router = APIRouter()

# 평가/발표용: Nexloop에서 사용하는 GCP 서비스 요약 (문서·헬스 응답용)
GCP_SERVICES_USED = [
    "Cloud Run",
    "Cloud SQL",
    "GCS",
    "Secret Manager",
    "Vertex AI",
    "Cloud Scheduler",
]


@router.get("/health")
async def health_check():
    """헬스 체크. 사용 중인 GCP 서비스 요약 포함 (평가/발표용)."""
    log_feature_start("health_check", "")
    log_feature_end("health_check")
    return {
        "status": "ok",
        "message": "Nexloop API is running",
        "gcp_services": GCP_SERVICES_USED,
    }


@router.post("/leads")
async def create_lead(request: LeadRequest):
    log_feature_start("leads_capture", "")
    if "@" not in request.email:
        log_feature_fail("leads_capture", "invalid email")
        raise HTTPException(status_code=400, detail="Invalid email")
    try:
        out_dir = ensure_output_dir()
        lead_path = out_dir / "leads.jsonl"
        payload = {
            "email": request.email,
            "created_at": datetime.now().isoformat(),
        }

        def _append_lead_sync(path: str, data: dict[str, Any]) -> None:
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(data, ensure_ascii=False) + "\n")

        await asyncio.to_thread(_append_lead_sync, str(lead_path), payload)
        log_feature_end("leads_capture")
        return {"status": "ok"}
    except Exception as e:
        log_feature_fail("leads_capture", str(e)[:200])
        raise


GUEST_CHAT_LIMIT = 3


def _free_chat_limit() -> int:
    """FREE tier 일일 챗 한도 (정책 상 10회/일)."""
    return int(
        TIER_POLICIES.get("FREE", {}).get("chatbot", {}).get("max_messages_per_day", 10)
    )


def _next_midnight_kst_iso() -> str:
    """다음 날 자정(KST) ISO 문자열. 24시간 기준 리필 시점."""
    n = now_kst()
    next_midnight = datetime.combine(
        n.date() + timedelta(days=1), time(0, 0), tzinfo=KST
    )
    return next_midnight.isoformat()


async def _get_free_user_chat_usage_today(session: AsyncSession, user_id: int) -> int:
    """FREE tier 로그인 사용자의 오늘(KST) 챗 사용 횟수."""
    today = now_kst().date()
    result = await session.execute(
        select(UserDailyChatUsage).where(
            UserDailyChatUsage.user_id == user_id,
            UserDailyChatUsage.usage_date == today,
        )
    )
    row = result.scalar_one_or_none()
    return row.count if row else 0


async def _increment_free_user_chat_usage(session: AsyncSession, user_id: int) -> None:
    """FREE tier 로그인 사용자의 오늘 사용 횟수 1 증가 (없으면 생성)."""
    today = now_kst().date()
    result = await session.execute(
        select(UserDailyChatUsage).where(
            UserDailyChatUsage.user_id == user_id,
            UserDailyChatUsage.usage_date == today,
        )
    )
    row = result.scalar_one_or_none()
    if row:
        row.count += 1
    else:
        session.add(UserDailyChatUsage(user_id=user_id, usage_date=today, count=1))
    await session.commit()


@router.get("/chat/remaining")
async def chat_remaining(
    http_request: Request,
    user: OptionalUser = None,
    session: AsyncSession = Depends(get_db_session),
):
    """
    비로그인: IP 기준 남은 횟수 (서버 재시작 시 초기화).
    로그인 FREE: 일 10회 한도, 남은 횟수 반환.
    로그인 PRO/BUSINESS: null(무제한).
    """
    log_feature_start("chat_remaining", "guest" if user is None else "auth")
    if user is not None:
        tier = getattr(user, "tier", "FREE")
        if tier in ("PRO", "BUSINESS"):
            log_feature_end("chat_remaining", extra_detail="remaining=null(unlimited)")
            return {"remaining": None}
        # FREE tier: DB 기준 오늘 사용량, 24시간(자정 KST) 기준 다음 리필 시각
        limit = _free_chat_limit()
        used = await _get_free_user_chat_usage_today(session, user.id)
        remaining = max(0, limit - used)
        log_feature_end("chat_remaining", extra_detail=f"free_remaining={remaining} (used={used})")
        return {
            "remaining": remaining,
            "resets_at": _next_midnight_kst_iso(),
            "limit_per_day": limit,
        }

    client_ip = http_request.client.host if http_request.client else "unknown"
    forwarded_for = http_request.headers.get("X-Forwarded-For")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()

    remaining = get_remaining_requests(client_ip, max_requests=GUEST_CHAT_LIMIT)
    log_feature_end("chat_remaining", extra_detail=f"remaining={remaining}")
    return {
        "remaining": remaining,
        "resets_at": _next_midnight_kst_iso(),
        "limit_per_day": GUEST_CHAT_LIMIT,
    }


@router.post("/chat")
async def chat(
    chat_request: ChatRequest,
    http_request: Request,
    user: OptionalUser = None,
    session: AsyncSession = Depends(get_db_session),
):
    """
    Chat endpoint with optional authentication.
    - 비로그인: IP당 3회/일, guest 데이터스토어
    - 로그인 FREE: 10회/일 한도, DB 집계
    - 로그인 PRO/BUSINESS: 무제한
    """
    log_feature_start("chat_reply", "guest" if user is None else "auth")
    services = get_services()
    settings = get_settings()

    client_ip = http_request.client.host if http_request.client else "unknown"
    forwarded_for = http_request.headers.get("X-Forwarded-For")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()

    if user is None:
        if not check_rate_limit(client_ip, max_requests=GUEST_CHAT_LIMIT):
            remaining = get_remaining_requests(client_ip, max_requests=GUEST_CHAT_LIMIT)
            log_feature_fail("chat_reply", "rate limit exceeded")
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. {remaining} requests remaining.",
            )
        data_store_id = settings.rag_data_stores.get("guest")
        if not data_store_id:
            data_store_id = settings.rag_data_stores.get("editor")
    else:
        tier = getattr(user, "tier", "FREE")
        if tier == "FREE":
            limit = _free_chat_limit()
            used = await _get_free_user_chat_usage_today(session, user.id)
            if used >= limit:
                log_feature_fail("chat_reply", "free daily limit exceeded")
                raise HTTPException(
                    status_code=429,
                    detail=f"오늘 무료 질문 한도({limit}회)를 모두 사용했습니다. 내일 다시 이용해 주세요.",
                )
            await _increment_free_user_chat_usage(session, user.id)
        data_store_id = settings.rag_data_stores.get(getattr(user, "role", "editor"))

    try:
        reply = await services.chatbot_service.generate_reply(
            message=chat_request.message,
            session_id=chat_request.session_id or "",
            data_store_id=data_store_id,
        )
        log_feature_end("chat_reply")
        return reply
    except Exception as e:
        log_feature_fail("chat_reply", str(e))
        raise


@router.post("/chat/stream")
async def chat_stream(
    chat_request: ChatRequest,
    http_request: Request,
    user: OptionalUser = None,
    session: AsyncSession = Depends(get_db_session),
):
    """
    Chat streaming endpoint (SSE). 한도 정책은 /chat과 동일.
    """
    from fastapi.responses import StreamingResponse

    log_feature_start("chat_reply_stream", "guest" if user is None else "auth")
    services = get_services()
    settings = get_settings()

    client_ip = http_request.client.host if http_request.client else "unknown"
    forwarded_for = http_request.headers.get("X-Forwarded-For")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()

    if user is None:
        if not check_rate_limit(client_ip, max_requests=GUEST_CHAT_LIMIT):
            remaining = get_remaining_requests(client_ip, max_requests=GUEST_CHAT_LIMIT)
            log_feature_fail("chat_reply_stream", "rate limit exceeded")
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. {remaining} requests remaining.",
            )
        data_store_id = settings.rag_data_stores.get("guest")
        if not data_store_id:
            data_store_id = settings.rag_data_stores.get("editor")
    else:
        tier = getattr(user, "tier", "FREE")
        if tier == "FREE":
            limit = _free_chat_limit()
            used = await _get_free_user_chat_usage_today(session, user.id)
            if used >= limit:
                log_feature_fail("chat_reply_stream", "free daily limit exceeded")
                raise HTTPException(
                    status_code=429,
                    detail=f"오늘 무료 질문 한도({limit}회)를 모두 사용했습니다. 내일 다시 이용해 주세요.",
                )
            await _increment_free_user_chat_usage(session, user.id)
        data_store_id = settings.rag_data_stores.get(getattr(user, "role", "editor"))

    log_feature_end("chat_reply_stream", extra_detail="stream started")
    return StreamingResponse(
        services.chatbot_service.generate_reply_stream(
            message=chat_request.message,
            session_id=chat_request.session_id or "",
            data_store_id=data_store_id,
        ),
        media_type="text/event-stream",
    )


@router.post("/refresh-url")
async def refresh_signed_url(request: RefreshUrlRequest):
    log_feature_start("refresh_signed_url", "")
    services = get_services()
    storage = services.storage_service

    raw_path = request.gcs_path.strip()
    path = raw_path
    if raw_path.startswith("gs://"):
        parts = raw_path[5:].split("/", 1)
        if len(parts) == 2:
            path = parts[1]
    url = storage.get_signed_url(path)
    if not url:
        log_feature_fail("refresh_signed_url", "failed to generate URL")
        raise HTTPException(status_code=404, detail="Failed to generate signed URL")
    log_feature_end("refresh_signed_url")
    return {"url": url}


@router.get("/search/discovery")
async def search_discovery(
    q: str,
    user: Annotated[Any, Depends(require_tier("PRO"))],
    background_tasks: BackgroundTasks,
    max_results: int = 5,
):
    log_feature_start("search_discovery", "")
    try:
        services = get_services()
        settings = get_settings()
        data_store_id = settings.rag_data_stores.get(getattr(user, "role", ""))
        results = await services.discovery_engine_client.search(
            q,
            max_results=max_results,
            data_store_id=data_store_id,
        )
        background_tasks.add_task(
            services.rag_ingestion_service.ingest_search_log,
            q,
            results,
            user,
        )
        log_feature_end("search_discovery", extra_detail=f"results={len(results)}")
        return {"results": results}
    except Exception as e:
        log_feature_fail("search_discovery", str(e)[:200])
        raise
