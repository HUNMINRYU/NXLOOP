import asyncio
from typing import TYPE_CHECKING, Annotated, Any

from fastapi import Depends, HTTPException, Request
from sqlalchemy.exc import SQLAlchemyError, TimeoutError as SQLAlchemyTimeoutError

from config.dependencies import get_services
from infrastructure.database.connection import get_db_session
from utils.log_throttle import should_log_throttled
from utils.logger import log_feature_fail

if TYPE_CHECKING:
    from infrastructure.clients.scheduler_client import CloudSchedulerClient


_AUTH_DB_THROTTLE_SEC = 30.0


async def get_current_user(
    session: Annotated[Any, Depends(get_db_session)],
    request: Request,
):
    """세션 쿠키 기반 인증 (HttpOnly)."""
    services = get_services()

    session_id = request.cookies.get("nexloop_session")
    if session_id:
        try:
            return await services.auth_service.get_user_by_session_id(session, session_id)
        except HTTPException:
            # 인증 실패(401/403 등)는 그대로 클라이언트로 전달
            raise
        except (asyncio.TimeoutError, SQLAlchemyTimeoutError, SQLAlchemyError) as e:
            # DB/네트워크 장애는 500 stack trace 대신 503으로 명확히 반환하고,
            # 로그 스팸 방지를 위해 interval 기반 throttle을 적용한다.
            key = f"auth_db_unavailable:{session_id[:8]}"
            if should_log_throttled(key, _AUTH_DB_THROTTLE_SEC):
                log_feature_fail("auth_db_unavailable", f"{type(e).__name__}: {str(e)[:200]}")
            raise HTTPException(status_code=503, detail="Database unavailable") from e
        except Exception as e:
            # 알 수 없는 예외도 500 stack trace 폭주를 막고 메시지를 제한한다.
            key = f"auth_unexpected:{session_id[:8]}"
            if should_log_throttled(key, _AUTH_DB_THROTTLE_SEC):
                log_feature_fail("auth_unexpected", f"{type(e).__name__}: {str(e)[:200]}")
            raise HTTPException(status_code=500, detail="Authentication failed") from e

    raise HTTPException(status_code=401, detail="Authentication required")


CurrentUser = Annotated[Any, Depends(get_current_user)]


async def get_current_user_optional(
    session: Annotated[Any, Depends(get_db_session)],
    request: Request,
):
    """
    Optional authentication dependency.
    Returns user if authenticated, None otherwise (no exception raised).
    """
    services = get_services()
    try:
        session_id = request.cookies.get("nexloop_session")
        if session_id:
            return await services.auth_service.get_user_by_session_id(session, session_id)
        return None
    except HTTPException:
        return None
    except (asyncio.TimeoutError, SQLAlchemyTimeoutError, SQLAlchemyError) as e:
        key = f"auth_optional_db_unavailable:{(request.cookies.get('nexloop_session') or '')[:8]}"
        if should_log_throttled(key, _AUTH_DB_THROTTLE_SEC):
            log_feature_fail("auth_optional_db_unavailable", f"{type(e).__name__}: {str(e)[:200]}")
        return None
    except Exception as e:
        key = f"auth_optional_unexpected:{(request.cookies.get('nexloop_session') or '')[:8]}"
        if should_log_throttled(key, _AUTH_DB_THROTTLE_SEC):
            log_feature_fail("auth_optional_unexpected", f"{type(e).__name__}: {str(e)[:200]}")
        return None


OptionalUser = Annotated[Any | None, Depends(get_current_user_optional)]


TIER_ORDER = {"FREE": 0, "PRO": 1, "BUSINESS": 2}


def require_tier(min_tier: str):
    """최소 구독 tier를 요구하는 의존성"""

    async def _checker(user: CurrentUser):
        user_tier = getattr(user, "tier", "FREE")
        if TIER_ORDER.get(user_tier, 0) < TIER_ORDER.get(min_tier, 0):
            raise HTTPException(
                status_code=403,
                detail=f"This feature requires a {min_tier} subscription or higher.",
            )
        return user

    return _checker


def require_role(roles: list[str]):
    async def _checker(user: CurrentUser):
        user_role = getattr(user, "role", "editor")
        if user_role not in roles:
            raise HTTPException(status_code=403, detail="Forbidden")
        return user

    return _checker


# Dependency for CloudSchedulerClient
def get_scheduler_client() -> "CloudSchedulerClient":
    """CloudSchedulerClient 의존성 주입"""
    import os

    from infrastructure.clients.scheduler_client import CloudSchedulerClient

    project_id = os.getenv("GOOGLE_CLOUD_PROJECT_ID")
    # Cloud Scheduler는 'global'을 지원하지 않으므로 전용 리전 변수 사용
    location = os.getenv("SCHEDULER_LOCATION") or os.getenv("GOOGLE_CLOUD_LOCATION") or "asia-northeast3"
    if location == "global":
        location = "asia-northeast3"

    service_account = os.getenv("SCHEDULER_SERVICE_ACCOUNT", "")

    if not project_id:
        raise HTTPException(
            status_code=500,
            detail="GOOGLE_CLOUD_PROJECT_ID 환경 변수가 설정되지 않았습니다.",
        )
    return CloudSchedulerClient(project_id, location, service_account_email=service_account)
