import json
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request

from api.deps import OptionalUser, require_tier
from config.dependencies import get_services
from config.settings import get_settings
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
    if "@" not in request.email:
        raise HTTPException(status_code=400, detail="Invalid email")
    out_dir = ensure_output_dir()
    lead_path = out_dir / "leads.jsonl"
    payload = {
        "email": request.email,
        "created_at": datetime.now().isoformat(),
    }
    with open(lead_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    return {"status": "ok"}


GUEST_CHAT_LIMIT = 3


@router.get("/chat/remaining")
async def chat_remaining(
    http_request: Request,
    user: OptionalUser = None,
):
    """
    비로그인 시 현재 IP의 남은 챗봇 요청 횟수 반환 (서버 재시작 시 초기화됨).
    로그인 사용자는 null(무제한).
    """
    log_feature_start("chat_remaining", "guest" if user is None else "auth")
    if user is not None:
        log_feature_end("chat_remaining")
        return {"remaining": None}

    client_ip = http_request.client.host if http_request.client else "unknown"
    forwarded_for = http_request.headers.get("X-Forwarded-For")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()

    remaining = get_remaining_requests(client_ip, max_requests=GUEST_CHAT_LIMIT)
    log_feature_end("chat_remaining", extra_detail=f"remaining={remaining}")
    return {"remaining": remaining}


@router.post("/chat")
async def chat(
    chat_request: ChatRequest,
    http_request: Request,
    user: OptionalUser = None,
):
    """
    Chat endpoint with optional authentication.
    - Authenticated users: unlimited access with role-based data store
    - Non-authenticated users: limited to 3 requests per IP with guest data store
    """
    log_feature_start("chat_reply", "guest" if user is None else "auth")
    services = get_services()
    settings = get_settings()

    # Get client IP address
    client_ip = http_request.client.host if http_request.client else "unknown"
    forwarded_for = http_request.headers.get("X-Forwarded-For")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()

    if user is None:
        # Non-authenticated user - apply rate limiting
        if not check_rate_limit(client_ip, max_requests=GUEST_CHAT_LIMIT):
            remaining = get_remaining_requests(client_ip, max_requests=GUEST_CHAT_LIMIT)
            log_feature_fail("chat_reply", "rate limit exceeded")
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. {remaining} requests remaining.",
            )

        # Use guest data store for non-authenticated users
        data_store_id = settings.rag_data_stores.get("guest")
        if not data_store_id:
            data_store_id = settings.rag_data_stores.get("editor")
    else:
        # Authenticated user - use role-based data store
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
):
    """
    Chat streaming endpoint (SSE).
    Returns text/event-stream.
    """
    from fastapi.responses import StreamingResponse

    log_feature_start("chat_reply_stream", "guest" if user is None else "auth")
    services = get_services()
    settings = get_settings()

    # Get client IP address
    client_ip = http_request.client.host if http_request.client else "unknown"
    forwarded_for = http_request.headers.get("X-Forwarded-For")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()

    if user is None:
        # Non-authenticated user - apply rate limiting
        if not check_rate_limit(client_ip, max_requests=GUEST_CHAT_LIMIT):
            remaining = get_remaining_requests(client_ip, max_requests=GUEST_CHAT_LIMIT)
            log_feature_fail("chat_reply_stream", "rate limit exceeded")
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. {remaining} requests remaining.",
            )

        # Use guest data store for non-authenticated users
        data_store_id = settings.rag_data_stores.get("guest")
        if not data_store_id:
            data_store_id = settings.rag_data_stores.get("editor")
    else:
        # Authenticated user - use role-based data store
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
        raise HTTPException(status_code=404, detail="Failed to generate signed URL")
    return {"url": url}


@router.get("/search/discovery")
async def search_discovery(
    q: str,
    user: Annotated[Any, Depends(require_tier("PRO"))],
    background_tasks: BackgroundTasks,
    max_results: int = 5,
):
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
    return {"results": results}
