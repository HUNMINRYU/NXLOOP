import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import stripe
from services.stripe_service import StripeService

@pytest.fixture
def mock_stripe_service():
    with patch("services.stripe_service.settings") as mock_settings:
        mock_settings.stripe_secret_key.get_secret_value.return_value = "sk_test_mock"
        service = StripeService()
        return service

@pytest.mark.asyncio
async def test_process_webhook_event_checkout_completed(mock_stripe_service):
    # Mock event data
    event_data = {
        "id": "evt_123",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_123",
                "customer": "cus_123"
            }
        }
    }
    event = stripe.Event.construct_from(event_data, key="sk_test_mock")

    # Mock internal handler
    mock_stripe_service._handle_checkout_session_completed = AsyncMock()

    # Act
    await mock_stripe_service.process_webhook_event(event)

    # Assert
    mock_stripe_service._handle_checkout_session_completed.assert_called_once_with(event.data.object)

@pytest.mark.asyncio
async def test_process_webhook_event_invoice_succeeded(mock_stripe_service):
    # Mock event data
    event_data = {
        "id": "evt_456",
        "type": "invoice.payment_succeeded",
        "data": {
            "object": {
                "id": "in_123",
                "customer": "cus_123"
            }
        }
    }
    event = stripe.Event.construct_from(event_data, key="sk_test_mock")

    # Mock internal handler
    mock_stripe_service._handle_invoice_payment_succeeded = AsyncMock()

    # Act
    await mock_stripe_service.process_webhook_event(event)

    # Assert
    mock_stripe_service._handle_invoice_payment_succeeded.assert_called_once_with(event.data.object)

@pytest.mark.asyncio
async def test_process_webhook_event_unhandled_type(mock_stripe_service):
    # Mock event data
    event_data = {
        "id": "evt_789",
        "type": "unhandled.event",
        "data": {
            "object": {}
        }
    }
    event = stripe.Event.construct_from(event_data, key="sk_test_mock")

    # Act (Should not raise error)
    await mock_stripe_service.process_webhook_event(event)
