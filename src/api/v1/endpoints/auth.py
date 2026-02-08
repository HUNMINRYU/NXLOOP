from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response

from api.deps import CurrentUser
from config.dependencies import get_services
from infrastructure.database.connection import get_db_session
from schemas.requests import AuthLoginRequest, AuthSignupRequest
from utils.logger import log_feature_end, log_feature_start, log_info, log_warning

router = APIRouter()

SESSION_COOKIE = "nexloop_session"
CSRF_COOKIE = "nexloop_csrf"


def _is_https(request: Request) -> bool:
    # Cloud Run behind proxy: X-Forwarded-Proto is authoritative.
    forwarded = request.headers.get("x-forwarded-proto", "")
    if forwarded:
        return forwarded.lower() == "https"
    return request.url.scheme == "https"


def _set_auth_cookies(response: Response, request: Request, session_id: str, csrf_token: str) -> None:
    secure = _is_https(request) or bool(request.headers.get("x-forwarded-proto")) or bool(
        request.headers.get("x-forwarded-host")
    )
    # SameSite=None은 Secure가 필수다(브라우저 정책).
    # - 운영(HTTPS): cross-site 가능성을 고려해 None 사용
    # - 로컬(HTTP): Lax로 downgrade
    same_site = "none" if secure else "lax"

    # "브라우저 종료 시 만료" 정책: max_age/expires를 설정하지 않는다.
    response.set_cookie(
        key=SESSION_COOKIE,
        value=session_id,
        httponly=True,
        secure=secure,
        samesite=same_site,
        path="/",
    )
    # CSRF 토큰은 JS가 읽어 헤더로 제출해야 하므로 HttpOnly=False
    response.set_cookie(
        key=CSRF_COOKIE,
        value=csrf_token,
        httponly=False,
        secure=secure,
        samesite=same_site,
        path="/",
    )


def _clear_auth_cookies(response: Response, request: Request) -> None:
    secure = _is_https(request)
    same_site = "none" if secure else "lax"
    response.delete_cookie(key=SESSION_COOKIE, path="/", secure=secure, samesite=same_site)
    response.delete_cookie(key=CSRF_COOKIE, path="/", secure=secure, samesite=same_site)


@router.post("/signup")
async def signup(request: AuthSignupRequest, http_response: Response, http_request: Request, session=Depends(get_db_session)):
    log_feature_start("auth_signup", request.email)
    services = get_services()
    if request.name:
        name = request.name
    else:
        name = request.email.split("@")[0] if "@" in request.email else "user"
    result = await services.auth_service.signup(
        session=session,
        name=name,
        email=request.email,
        password=request.password,
        team_name=request.team_name,
        job_title=request.job_title,
        phone_number=request.phone_number,
    )
    user = result["user"]
    sess = await services.auth_service.create_session(session=session, user=user)
    csrf_token = services.auth_service.new_csrf_token()
    _set_auth_cookies(http_response, http_request, session_id=sess.id, csrf_token=csrf_token)
    log_info(f"   🔐 [회원가입] 세션 생성: {user.email}, 세션ID: {sess.id[:8]}...")
    log_feature_end("auth_signup")
    return {
        "email": user.email,
        "role": user.role,
        "name": user.name,
        "tier": getattr(user, "tier", "FREE"),
        "subscription_status": getattr(user, "subscription_status", "none"),
        "csrf_token": csrf_token,
    }


@router.post("/login")
async def login(request: AuthLoginRequest, http_response: Response, http_request: Request, session=Depends(get_db_session)):
    log_feature_start("auth_login", request.email)
    services = get_services()
    result = await services.auth_service.login(
        session=session,
        email=request.email,
        password=request.password,
    )
    user = result["user"]
    sess = await services.auth_service.create_session(session=session, user=user)
    csrf_token = services.auth_service.new_csrf_token()
    _set_auth_cookies(http_response, http_request, session_id=sess.id, csrf_token=csrf_token)
    log_info(f"   🔐 [로그인] 세션 생성: {user.email}, 세션ID: {sess.id[:8]}...")
    log_feature_end("auth_login")
    return {
        "email": user.email,
        "role": user.role,
        "name": user.name,
        "tier": getattr(user, "tier", "FREE"),
        "subscription_status": getattr(user, "subscription_status", "none"),
        "csrf_token": csrf_token,
    }


@router.post("/logout")
async def logout(
    http_response: Response,
    http_request: Request,
    session=Depends(get_db_session),
):
    """세션 쿠키 기반 로그아웃."""
    log_feature_start("auth_logout", "")
    services = get_services()

    session_id = http_request.cookies.get(SESSION_COOKIE)
    if session_id:
        await services.auth_service.delete_session(session=session, session_id=session_id)
        _clear_auth_cookies(http_response, http_request)
        log_info(f"   🔓 [로그아웃] 세션 삭제: 세션ID: {session_id[:8]}...")
        log_feature_end("auth_logout")
        return {"message": "로그아웃 완료"}

    # 세션 쿠키 없으면 이미 로그아웃된 상태
    log_feature_end("auth_logout")
    return {"message": "이미 로그아웃된 상태입니다"}


@router.get("/me")
async def me(user: CurrentUser, http_request: Request):
    """현재 사용자 정보. cross-origin 환경에서 JS가 쿠키를 읽지 못하므로 csrf_token을 본문으로 내려준다."""
    csrf_token = http_request.cookies.get(CSRF_COOKIE) or ""
    return {
        "email": user.email,
        "role": user.role,
        "name": user.name,
        "tier": getattr(user, "tier", "FREE"),
        "subscription_status": getattr(user, "subscription_status", "none"),
        "csrf_token": csrf_token,
    }


@router.post("/ping")
async def ping(user: CurrentUser):
    """세션/CSRF 설정 검증용 엔드포인트(가벼운 보호 API)."""
    return {"ok": True, "email": user.email}

