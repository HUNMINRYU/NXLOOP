from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from api.v1.endpoints.stripe import create_checkout_session
from schemas.requests import StripeCreateCheckoutSessionRequest


@pytest.mark.asyncio
async def test_create_checkout_session_missing_secret_returns_500():
    request = StripeCreateCheckoutSessionRequest(plan="PRO")
    user = SimpleNamespace(id=1, email="user@example.com")

    with patch("api.v1.endpoints.stripe.settings", autospec=True) as mock_settings:
        mock_settings.stripe_secret_key = ""

        with pytest.raises(HTTPException) as exc:
            await create_checkout_session(request=request, user=user)

    assert exc.value.status_code == 500
    assert exc.value.detail == "Stripe configuration error"


@pytest.mark.asyncio
async def test_create_checkout_session_fallbacks_to_app_url_when_frontend_url_empty():
    request = StripeCreateCheckoutSessionRequest(plan="PRO")
    user = SimpleNamespace(id=7, email="paid@example.com")
    fake_session = SimpleNamespace(url="https://checkout.stripe.com/session/test")

    with (
        patch("api.v1.endpoints.stripe.settings", autospec=True) as mock_settings,
        patch("api.v1.endpoints.stripe.stripe.checkout.Session.create") as create_session,
    ):
        mock_settings.stripe_secret_key = "sk_test_mock"
        mock_settings.app.frontend_url = ""
        mock_settings.app.app_url = "https://app.example.com"
        create_session.return_value = fake_session

        data = await create_checkout_session(request=request, user=user)

    assert data["url"] == fake_session.url
    kwargs = create_session.call_args.kwargs
    assert kwargs["success_url"].startswith(
        "https://app.example.com/payment/success?session_id="
    )
    assert kwargs["cancel_url"] == "https://app.example.com/pricing"
