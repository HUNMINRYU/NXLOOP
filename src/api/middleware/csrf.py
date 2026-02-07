from __future__ import annotations

from fastapi.responses import JSONResponse

from utils.logger import log_warning

SESSION_COOKIE = "nexloop_session"
CSRF_COOKIE = "nexloop_csrf"


async def csrf_protect(request, call_next):
    """쿠키 기반 인증에서 최소 CSRF 방어(Double Submit).

    정책:
    - 상태 변경 요청(POST/PUT/PATCH/DELETE)에서 세션 쿠키가 존재하면,
      `X-CSRF-Token` 헤더와 `nexloop_csrf` 쿠키가 일치해야 통과한다.
    - cross-site 폼 제출 등은 커스텀 헤더를 붙일 수 없으므로 자동으로 차단된다.
    - 로그인/회원가입/로그아웃 및 머신-투-머신(Webhook) 엔드포인트는 제외한다.
    """

    method = request.method.upper()
    if method in {"POST", "PUT", "PATCH", "DELETE"}:
        path = request.url.path or ""

        skip_paths = {
            "/auth/login",
            "/auth/signup",
            "/auth/logout",
            "/api/v1/auth/login",
            "/api/v1/auth/signup",
            "/api/v1/auth/logout",
            "/health",
            "/docs",
            "/openapi.json",
        }
        skip_prefixes = ("/webhooks/", "/api/v1/webhooks/")

        if path not in skip_paths and not path.startswith(skip_prefixes):
            session_id = request.cookies.get(SESSION_COOKIE)
            if session_id:
                csrf_cookie = request.cookies.get(CSRF_COOKIE)
                csrf_header = request.headers.get("x-csrf-token")
                if not csrf_cookie or not csrf_header or csrf_cookie != csrf_header:
                    log_warning(f"   ⚠️ [CSRF] 토큰 불일치 - 경로: {path}, 세션: {session_id[:8]}...")
                    return JSONResponse(
                        status_code=403,
                        content={"detail": "CSRF token missing or invalid"},
                    )

    return await call_next(request)


