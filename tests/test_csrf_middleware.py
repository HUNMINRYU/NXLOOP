from __future__ import annotations

import pytest
from starlette.requests import Request

from api.middleware.csrf import csrf_protect


def _make_request(
    *,
    method: str,
    path: str,
    headers: dict[str, str] | None = None,
    cookies: dict[str, str] | None = None,
) -> Request:
    raw_headers: list[tuple[bytes, bytes]] = []
    for k, v in (headers or {}).items():
        raw_headers.append((k.encode("latin-1"), v.encode("latin-1")))

    # Starlette Request는 cookies를 headers의 Cookie 문자열로 파싱한다.
    if cookies:
        cookie_value = "; ".join([f"{k}={v}" for k, v in cookies.items()])
        raw_headers.append((b"cookie", cookie_value.encode("latin-1")))

    scope = {
        "type": "http",
        "method": method.upper(),
        "path": path,
        "raw_path": path.encode("ascii"),
        "query_string": b"",
        "headers": raw_headers,
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
        "scheme": "http",
    }
    return Request(scope)


async def _ok_response(_request):  # type: ignore[no-untyped-def]
    class DummyResponse:
        status_code = 200

    return DummyResponse()


@pytest.mark.anyio
async def test_csrf_allows_state_change_when_no_session_cookie() -> None:
    req = _make_request(method="POST", path="/pipeline/run")
    res = await csrf_protect(req, _ok_response)
    assert res.status_code == 200


@pytest.mark.anyio
async def test_csrf_blocks_state_change_without_header_when_session_cookie_present() -> None:
    req = _make_request(
        method="POST",
        path="/pipeline/run",
        cookies={"nexloop_session": "sid", "nexloop_csrf": "csrf"},
    )
    res = await csrf_protect(req, _ok_response)
    assert res.status_code == 403


@pytest.mark.anyio
async def test_csrf_allows_state_change_when_header_matches_cookie() -> None:
    req = _make_request(
        method="POST",
        path="/pipeline/run",
        headers={"x-csrf-token": "csrf"},
        cookies={"nexloop_session": "sid", "nexloop_csrf": "csrf"},
    )
    res = await csrf_protect(req, _ok_response)
    assert res.status_code == 200


# === A. 메서드별 검증 ===
@pytest.mark.anyio
async def test_csrf_skips_safe_methods() -> None:
    """GET/HEAD/OPTIONS는 세션 있어도 CSRF 검증 스킵"""
    for method in ["GET", "HEAD", "OPTIONS"]:
        req = _make_request(
            method=method,
            path="/pipeline/status/task123",
            cookies={"nexloop_session": "sid"},  # CSRF 없어도 통과
        )
        res = await csrf_protect(req, _ok_response)
        assert res.status_code == 200


# === B. 경로 예외 처리 ===
@pytest.mark.anyio
async def test_csrf_skips_auth_endpoints() -> None:
    """로그인/회원가입/로그아웃 경로는 CSRF 검증 스킵"""
    auth_paths = [
        "/auth/login",
        "/auth/signup",
        "/auth/logout",
        "/api/v1/auth/login",
        "/api/v1/auth/signup",
        "/api/v1/auth/logout",
    ]
    for path in auth_paths:
        req = _make_request(method="POST", path=path)
        res = await csrf_protect(req, _ok_response)
        assert res.status_code == 200


@pytest.mark.anyio
async def test_csrf_skips_webhook_endpoints() -> None:
    """Webhook 경로는 CSRF 검증 스킵 (외부 서비스)"""
    webhook_paths = [
        "/webhooks/stripe",
        "/webhooks/scheduler",
        "/api/v1/webhooks/stripe",
        "/api/v1/webhooks/scheduler",
    ]
    for path in webhook_paths:
        req = _make_request(method="POST", path=path)
        res = await csrf_protect(req, _ok_response)
        assert res.status_code == 200


@pytest.mark.anyio
async def test_csrf_skips_health_and_docs() -> None:
    """헬스체크/문서 경로는 CSRF 검증 스킵"""
    skip_paths = ["/health", "/docs", "/openapi.json"]
    for path in skip_paths:
        req = _make_request(method="POST", path=path)
        res = await csrf_protect(req, _ok_response)
        assert res.status_code == 200


# === C. 토큰 검증 로직 ===
@pytest.mark.anyio
async def test_csrf_fails_when_token_mismatch() -> None:
    """CSRF 토큰 불일치 시 403 반환"""
    req = _make_request(
        method="POST",
        path="/pipeline/run",
        headers={"x-csrf-token": "csrf_a"},
        cookies={"nexloop_session": "sid", "nexloop_csrf": "csrf_b"},
    )
    res = await csrf_protect(req, _ok_response)
    assert res.status_code == 403


@pytest.mark.anyio
async def test_csrf_fails_when_cookie_missing() -> None:
    """CSRF 쿠키 없을 때 403"""
    req = _make_request(
        method="POST",
        path="/pipeline/run",
        headers={"x-csrf-token": "csrf"},
        cookies={"nexloop_session": "sid"},  # nexloop_csrf 없음
    )
    res = await csrf_protect(req, _ok_response)
    assert res.status_code == 403


@pytest.mark.anyio
async def test_csrf_fails_when_header_missing() -> None:
    """CSRF 헤더 없을 때 403 (명시적 검증)"""
    req = _make_request(
        method="POST",
        path="/pipeline/run",
        cookies={"nexloop_session": "sid", "nexloop_csrf": "csrf"},
    )
    res = await csrf_protect(req, _ok_response)
    assert res.status_code == 403


# === D. 에러 메시지 검증 ===
@pytest.mark.anyio
async def test_csrf_returns_proper_error_message() -> None:
    """403 응답 시 명확한 에러 메시지 반환"""
    req = _make_request(
        method="POST",
        path="/pipeline/run",
        cookies={"nexloop_session": "sid"},
    )
    res = await csrf_protect(req, _ok_response)
    assert res.status_code == 403
    # JSONResponse body 파싱
    import json

    body = json.loads(res.body.decode())
    assert "CSRF" in body["detail"]
    assert "missing or invalid" in body["detail"].lower()
