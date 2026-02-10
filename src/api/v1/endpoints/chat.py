
import json
from datetime import datetime, time, timedelta

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import OptionalUser
from config.constants import TIER_POLICIES
from config.dependencies import get_services
from config.settings import get_settings
from infrastructure.database.connection import get_db_session
from infrastructure.database.models import KST, UserDailyChatUsage, now_kst
from schemas.requests import ChatRequest
from utils.logger import log_feature_end, log_feature_fail, log_feature_start
from utils.rate_limit import check_rate_limit, get_remaining_requests

router = APIRouter()

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


@router.get("/remaining")
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
    # chat_remaining은 프론트에서 자주 조회(대시보드/챗봇 위젯 등)되어 로그 스팸이 발생하기 쉬움.
    # 운영 관점에서 신호 대비 노이즈가 커서 [FEATURE] 로깅은 생략한다.
    if user is not None:
        tier = getattr(user, "tier", "FREE")
        if tier in ("PRO", "BUSINESS"):
            return {"remaining": None}
        # FREE tier: DB 기준 오늘 사용량, 24시간(자정 KST) 기준 다음 리필 시각
        limit = _free_chat_limit()
        used = await _get_free_user_chat_usage_today(session, user.id)
        remaining = max(0, limit - used)
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
    return {
        "remaining": remaining,
        "resets_at": _next_midnight_kst_iso(),
        "limit_per_day": GUEST_CHAT_LIMIT,
    }


@router.post("")
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
            log_feature_end("chat_reply", extra_detail="guest_limit_reached")
            return {
                "session_id": chat_request.session_id or "",
                "message": "무료 질문 3회를 모두 사용하셨습니다. 로그인하시면 매일 10회 더 질문하실 수 있어요!",
                "card": {
                    "title": "로그인하고 계속하기",
                    "bullets": ["로그인 후 일 10회 무료 대화", "나만의 마케팅 인사이트 저장"],
                    "actions": [
                        {"label": "로그인하기", "action": "/login"},
                        {"label": "회원가입", "action": "/signup"},
                    ],
                },
                "sources": [],
            }
        data_store_id = settings.rag_data_stores.get("guest")
        if not data_store_id:
            data_store_id = settings.rag_data_stores.get("editor")
    else:
        tier = getattr(user, "tier", "FREE")
        if tier == "FREE":
            limit = _free_chat_limit()
            used = await _get_free_user_chat_usage_today(session, user.id)
            if used >= limit:
                log_feature_end("chat_reply", extra_detail="free_limit_reached")
                return {
                    "session_id": chat_request.session_id or "",
                    "message": f"오늘 무료 질문 한도({limit}회)를 모두 사용하셨습니다. PRO 플랜으로 업그레이드하고 무제한 대화를 즐겨보세요!",
                    "card": {
                        "title": "무제한 요금제로 업그레이드",
                        "bullets": [
                            "챗봇 무제한 이용",
                            "자동화 파이프라인 우선순위 배정",
                            "심층 데이터 분석 권한",
                        ],
                        "cta": "요금제 보기",
                        "action": "/pricing",
                    },
                    "sources": [],
                }
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


@router.post("/stream")
async def chat_stream(
    chat_request: ChatRequest,
    http_request: Request,
    user: OptionalUser = None,
    session: AsyncSession = Depends(get_db_session),
):
    """
    Chat streaming endpoint (SSE). 한도 정책은 /chat과 동일.
    """
    log_feature_start("chat_reply_stream", "guest" if user is None else "auth")
    services = get_services()
    settings = get_settings()

    client_ip = http_request.client.host if http_request.client else "unknown"
    forwarded_for = http_request.headers.get("X-Forwarded-For")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()

    if user is None:
        if not check_rate_limit(client_ip, max_requests=GUEST_CHAT_LIMIT):
            log_feature_end("chat_reply_stream", extra_detail="guest_limit_reached")

            async def _guest_limit_gen():
                data = {
                    "step": "done",
                    "full_text": "무료 질문 3회를 모두 사용하셨습니다. 로그인하시면 매일 10회 더 질문하실 수 있어요!",
                    "card": {
                        "title": "로그인하고 계속하기",
                        "bullets": ["로그인 후 일 10회 무료 대화", "나만의 마케팅 인사이트 저장"],
                        "actions": [
                            {"label": "로그인하기", "action": "/login"},
                            {"label": "회원가입", "action": "/signup"},
                        ],
                    },
                }
                yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

            return StreamingResponse(_guest_limit_gen(), media_type="text/event-stream")

        data_store_id = settings.rag_data_stores.get("guest")
        if not data_store_id:
            data_store_id = settings.rag_data_stores.get("editor")
    else:
        tier = getattr(user, "tier", "FREE")
        if tier == "FREE":
            limit = _free_chat_limit()
            used = await _get_free_user_chat_usage_today(session, user.id)
            if used >= limit:
                log_feature_end("chat_reply_stream", extra_detail="free_limit_reached")

                async def _free_limit_gen():
                    data = {
                        "step": "done",
                        "full_text": f"오늘 무료 질문 한도({limit}회)를 모두 사용하셨습니다. PRO 플랜으로 업그레이드하고 무제한 대화를 즐겨보세요!",
                        "card": {
                            "title": "무제한 요금제로 업그레이드",
                            "bullets": [
                                "챗봇 무제한 이용",
                                "자동화 파이프라인 우선순위 배정",
                                "심층 데이터 분석 권한",
                            ],
                            "cta": "요금제 보기",
                            "action": "/pricing",
                        },
                    }
                    yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

                return StreamingResponse(_free_limit_gen(), media_type="text/event-stream")

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
