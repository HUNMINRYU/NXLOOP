from __future__ import annotations

import pytest
from starlette.requests import Request

from api.middleware.csrf import csrf_protect  # type: ignore[no-untyped-call]


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
