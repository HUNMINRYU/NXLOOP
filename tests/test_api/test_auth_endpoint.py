"""
Auth 엔드포인트 로직 테스트

주의: 이 리포지토리 환경에서는 Starlette/FastAPI TestClient가 간헐적으로 hang 될 수 있어
ASGI 레이어를 우회하고 라우트 함수/의존성 함수를 직접 호출해 검증합니다.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException, Request, Response

from api.deps import get_current_user
from api.v1.endpoints.auth import (
    CSRF_COOKIE,
    SESSION_COOKIE,
    login,
    logout,
    me,
    signup,
)
from schemas.requests import AuthLoginRequest, AuthSignupRequest


def _make_request(
    *,
    method: str,
    path: str,
    cookies: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
    scheme: str = "http",
) -> Request:
    raw_headers: list[tuple[bytes, bytes]] = []
    if cookies:
        cookie_str = "; ".join([f"{k}={v}" for k, v in cookies.items()])
        raw_headers.append((b"cookie", cookie_str.encode("latin-1")))
    if headers:
        for k, v in headers.items():
            raw_headers.append((k.lower().encode("latin-1"), v.encode("latin-1")))

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method.upper(),
        "scheme": scheme,
        "path": path,
        "raw_path": path.encode("latin-1"),
        "query_string": b"",
        "headers": raw_headers,
        "client": ("testclient", 12345),
        "server": ("testserver", 80),
    }
    return Request(scope)


@pytest.fixture
def mock_services():
    services = MagicMock()

    mock_user = MagicMock()
    mock_user.email = "test@example.com"
    mock_user.role = "editor"
    mock_user.name = "테스터"
    mock_user.tier = "FREE"
    mock_user.subscription_status = "none"

    mock_session = MagicMock()
    mock_session.id = "session-12345678-abcd"

    services.auth_service.signup = AsyncMock(return_value={"user": mock_user})
    services.auth_service.login = AsyncMock(return_value={"user": mock_user})
    services.auth_service.create_session = AsyncMock(return_value=mock_session)
    services.auth_service.new_csrf_token = MagicMock(return_value="csrf-token-abc")
    services.auth_service.delete_session = AsyncMock()
    services.auth_service.get_user_by_session_id = AsyncMock(return_value=mock_user)

    return services


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def patched_services(mock_services):
    # 엔드포인트·deps가 'from config.dependencies import get_services'로 바인딩한 get_services를 호출하므로,
    # 사용처(auth, api.deps)에서 패치해야 mock이 적용된다.
    with (
        patch("api.v1.endpoints.auth.get_services", return_value=mock_services),
        patch("api.deps.get_services", return_value=mock_services),
    ):
        yield


@pytest.mark.asyncio
async def test_signup_success(patched_services, mock_db):
    http_request = _make_request(method="POST", path="/api/v1/auth/signup")
    http_response = Response()
    req = AuthSignupRequest(email="test@example.com", password="password123")

    data = await signup(req, http_response, http_request, session=mock_db)
    assert data["email"] == "test@example.com"
    assert "role" in data
    assert "name" in data


@pytest.mark.asyncio
async def test_signup_sets_cookies(patched_services, mock_db):
    http_request = _make_request(method="POST", path="/api/v1/auth/signup")
    http_response = Response()
    req = AuthSignupRequest(email="test@example.com", password="password123")

    await signup(req, http_response, http_request, session=mock_db)
    set_cookie_headers = http_response.headers.getlist("set-cookie")
    assert any(h.startswith(f"{SESSION_COOKIE}=") for h in set_cookie_headers)
    assert any(h.startswith(f"{CSRF_COOKIE}=") for h in set_cookie_headers)


@pytest.mark.asyncio
async def test_login_success(patched_services, mock_db):
    http_request = _make_request(method="POST", path="/api/v1/auth/login")
    http_response = Response()
    req = AuthLoginRequest(email="test@example.com", password="password123")

    data = await login(req, http_response, http_request, session=mock_db)
    assert data["email"] == "test@example.com"
    assert "role" in data
    assert "name" in data


@pytest.mark.asyncio
async def test_logout_without_session(patched_services, mock_db):
    http_request = _make_request(method="POST", path="/api/v1/auth/logout")
    http_response = Response()

    data = await logout(http_response, http_request, session=mock_db)
    assert "message" in data


@pytest.mark.asyncio
async def test_logout_with_session_deletes_server_session_and_clears_cookies(
    patched_services, mock_services, mock_db
):
    http_request = _make_request(
        method="POST",
        path="/api/v1/auth/logout",
        cookies={SESSION_COOKIE: "session-12345678-abcd", CSRF_COOKIE: "csrf-token-abc"},
    )
    http_response = Response()

    data = await logout(http_response, http_request, session=mock_db)
    assert data["message"] == "로그아웃 완료"
    mock_services.auth_service.delete_session.assert_awaited()
    set_cookie_headers = http_response.headers.getlist("set-cookie")
    assert any(h.startswith(f"{SESSION_COOKIE}=") for h in set_cookie_headers)
    assert any(h.startswith(f"{CSRF_COOKIE}=") for h in set_cookie_headers)


@pytest.mark.asyncio
async def test_get_current_user_without_cookie_raises_401(patched_services, mock_db):
    http_request = _make_request(method="GET", path="/api/v1/auth/me")
    with pytest.raises(HTTPException) as exc:
        await get_current_user(session=mock_db, request=http_request)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_me_with_session_cookie_returns_user(patched_services, mock_services, mock_db):
    http_request = _make_request(
        method="GET",
        path="/api/v1/auth/me",
        cookies={SESSION_COOKIE: "session-12345678-abcd", CSRF_COOKIE: "csrf-token-abc"},
    )
    user = await get_current_user(session=mock_db, request=http_request)
    data = await me(user=user, http_request=http_request)
    assert data["email"] == "test@example.com"
    assert "role" in data
    assert data["csrf_token"] == "csrf-token-abc"
