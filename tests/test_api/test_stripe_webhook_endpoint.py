"""
Stripe Webhook 엔드포인트 테스트

주의: 이 리포지토리 환경에서는 Starlette/FastAPI TestClient가 간헐적으로 hang 될 수 있어
ASGI 레이어를 우회하고 라우트 함수/의존성 함수를 직접 호출해 검증합니다.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException, Request

from api.v1.endpoints.stripe import stripe_webhook


def _make_request(*, body: bytes, headers: dict[str, str] | None = None) -> Request:
    raw_headers: list[tuple[bytes, bytes]] = []
    if headers:
        for k, v in headers.items():
            raw_headers.append((k.lower().encode("latin-1"), v.encode("latin-1")))

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/api/v1/stripe/webhook",
        "raw_path": b"/api/v1/stripe/webhook",
        "query_string": b"",
        "headers": raw_headers,
        "client": ("testclient", 12345),
        "server": ("testserver", 80),
    }

    request = Request(scope)

    async def _body() -> bytes:
        return body

    # Starlette Request.body()를 대체해서 페이로드를 주입한다.
    request.body = _body  # type: ignore[method-assign]
    return request


@pytest.mark.asyncio
async def test_webhook_missing_signature_header_returns_400():
    req = _make_request(body=b"{}")
    db = AsyncMock()

    with patch("api.v1.endpoints.stripe.settings", autospec=True) as mock_settings:
        mock_settings.stripe_webhook_secret = "whsec_test"
        with pytest.raises(HTTPException) as exc:
            await stripe_webhook(request=req, db=db)

    assert exc.value.status_code == 400
    assert exc.value.detail == "Missing Stripe-Signature header"


@pytest.mark.asyncio
async def test_webhook_uses_stripe_signature_header_name():
    req = _make_request(
        body=b"{}",
        headers={"Stripe-Signature": "t=123,v1=sig"},
    )
    db = AsyncMock()

    with (
        patch("api.v1.endpoints.stripe.settings", autospec=True) as mock_settings,
        patch("api.v1.endpoints.stripe.stripe.Webhook.construct_event") as construct_event,
        patch("api.v1.endpoints.stripe.StripeService") as service_cls,
    ):
        mock_settings.stripe_webhook_secret = "whsec_test"
        construct_event.return_value = {"type": "checkout.session.completed"}
        service = service_cls.return_value
        service.process_webhook_event = AsyncMock()

        data = await stripe_webhook(request=req, db=db)

    assert data["status"] == "success"
    construct_event.assert_called_once()
    args = construct_event.call_args.args
    assert args[1] == "t=123,v1=sig"


@pytest.mark.asyncio
async def test_webhook_supports_multiple_secrets_comma_separated():
    req = _make_request(
        body=b"{}",
        headers={"Stripe-Signature": "t=123,v1=sig"},
    )
    db = AsyncMock()

    class _SigError(Exception):
        pass

    with (
        patch("api.v1.endpoints.stripe.settings", autospec=True) as mock_settings,
        patch("api.v1.endpoints.stripe.stripe.Webhook.construct_event") as construct_event,
        patch("api.v1.endpoints.stripe.StripeService") as service_cls,
        patch("api.v1.endpoints.stripe.stripe.SignatureVerificationError", new=_SigError),
    ):
        # 첫 secret은 실패, 두 번째 secret은 성공하는 케이스를 흉내낸다.
        mock_settings.stripe_webhook_secret = "whsec_one, whsec_two"
        construct_event.side_effect = [
            _SigError("bad sig"),
            {"type": "checkout.session.completed"},
        ]
        service = service_cls.return_value
        service.process_webhook_event = AsyncMock()

        data = await stripe_webhook(request=req, db=db)

    assert data["status"] == "success"
