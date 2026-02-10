import asyncio

import pytest
from fastapi import HTTPException
from starlette.requests import Request

import api.deps as deps


def _make_request_with_cookie(session_id: str) -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [(b"cookie", f"nexloop_session={session_id}".encode("utf-8"))],
    }
    return Request(scope)


@pytest.mark.asyncio
async def test_get_current_user_db_timeout_returns_503(monkeypatch):
    class _AuthService:
        async def get_user_by_session_id(self, session, session_id: str):
            raise asyncio.TimeoutError("connect timeout")

    class _Services:
        auth_service = _AuthService()

    monkeypatch.setattr(deps, "get_services", lambda: _Services())

    request = _make_request_with_cookie("sess_1234567890")
    with pytest.raises(HTTPException) as exc:
        await deps.get_current_user(session=None, request=request)  # type: ignore[arg-type]

    assert exc.value.status_code == 503
    assert "Database unavailable" in str(exc.value.detail)


@pytest.mark.asyncio
async def test_get_current_user_optional_db_timeout_returns_none(monkeypatch):
    class _AuthService:
        async def get_user_by_session_id(self, session, session_id: str):
            raise asyncio.TimeoutError("connect timeout")

    class _Services:
        auth_service = _AuthService()

    monkeypatch.setattr(deps, "get_services", lambda: _Services())

    request = _make_request_with_cookie("sess_1234567890")
    user = await deps.get_current_user_optional(session=None, request=request)  # type: ignore[arg-type]
    assert user is None

