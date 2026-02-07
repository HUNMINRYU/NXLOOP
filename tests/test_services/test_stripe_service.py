"""Stripe 웹훅 비즈니스 로직 테스트"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import stripe

from services.stripe_service import StripeService


@pytest.fixture
def stripe_service():
    """StripeService 테스트 fixture"""
    with patch("services.stripe_service.settings") as mock_settings:
        mock_settings.stripe_secret_key = "sk_test_mock"
        service = StripeService()
        yield service


@pytest.fixture
def mock_db():
    """AsyncSession mock fixture"""
    db = AsyncMock()
    db.commit = AsyncMock()
    return db


@pytest.fixture
def mock_user():
    """User mock fixture"""
    user = MagicMock()
    user.email = "test@example.com"
    user.stripe_customer_id = None
    user.tier = "FREE"
    user.subscription_status = "none"
    return user


# --- 이벤트 라우팅 테스트 ---


@pytest.mark.asyncio
async def test_process_webhook_routes_checkout_completed(stripe_service, mock_db):
    """checkout.session.completed 이벤트가 올바른 핸들러로 라우팅되는지 확인"""
    event_data = {
        "type": "checkout.session.completed",
        "data": {"object": {"customer": "cus_123", "customer_email": "t@t.com"}},
    }
    event = stripe.Event.construct_from(event_data, key="sk_test_mock")

    stripe_service._handle_checkout_completed = AsyncMock()
    await stripe_service.process_webhook_event(event, mock_db)
    stripe_service._handle_checkout_completed.assert_called_once()


@pytest.mark.asyncio
async def test_process_webhook_routes_payment_failed(stripe_service, mock_db):
    """invoice.payment_failed 이벤트가 올바른 핸들러로 라우팅되는지 확인"""
    event_data = {
        "type": "invoice.payment_failed",
        "data": {"object": {"customer": "cus_123"}},
    }
    event = stripe.Event.construct_from(event_data, key="sk_test_mock")

    stripe_service._handle_payment_failed = AsyncMock()
    await stripe_service.process_webhook_event(event, mock_db)
    stripe_service._handle_payment_failed.assert_called_once()


@pytest.mark.asyncio
async def test_process_webhook_unhandled_event(stripe_service, mock_db):
    """처리하지 않는 이벤트 타입은 에러 없이 통과"""
    event_data = {
        "type": "unhandled.event",
        "data": {"object": {}},
    }
    event = stripe.Event.construct_from(event_data, key="sk_test_mock")
    await stripe_service.process_webhook_event(event, mock_db)


# --- 핸들러 비즈니스 로직 테스트 ---


@pytest.mark.asyncio
async def test_checkout_completed_updates_user_tier(
    stripe_service, mock_db, mock_user
):
    """checkout.session.completed가 사용자 tier를 PRO로 업데이트"""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user
    mock_db.execute = AsyncMock(return_value=mock_result)

    session_data = {"customer": "cus_123", "customer_email": "test@example.com"}
    await stripe_service._handle_checkout_completed(session_data, mock_db)

    assert mock_user.tier == "PRO"
    assert mock_user.subscription_status == "active"
    assert mock_user.stripe_customer_id == "cus_123"
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_payment_failed_sets_past_due(stripe_service, mock_db, mock_user):
    """invoice.payment_failed가 subscription_status를 past_due로 변경"""
    mock_user.stripe_customer_id = "cus_123"
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user
    mock_db.execute = AsyncMock(return_value=mock_result)

    invoice_data = {"customer": "cus_123"}
    await stripe_service._handle_payment_failed(invoice_data, mock_db)

    assert mock_user.subscription_status == "past_due"
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_subscription_deleted_resets_to_free(
    stripe_service, mock_db, mock_user
):
    """customer.subscription.deleted가 tier→FREE, status→canceled"""
    mock_user.stripe_customer_id = "cus_123"
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user
    mock_db.execute = AsyncMock(return_value=mock_result)

    sub_data = {"customer": "cus_123"}
    await stripe_service._handle_subscription_deleted(sub_data, mock_db)

    assert mock_user.tier == "FREE"
    assert mock_user.subscription_status == "canceled"
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_checkout_no_matching_user(stripe_service, mock_db):
    """매칭 사용자가 없으면 에러 없이 종료, commit 미호출"""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=mock_result)

    session_data = {"customer": "cus_unknown", "customer_email": "no@match.com"}
    await stripe_service._handle_checkout_completed(session_data, mock_db)
    mock_db.commit.assert_not_called()


@pytest.mark.asyncio
async def test_payment_succeeded_updates_status(
    stripe_service, mock_db, mock_user
):
    """invoice.payment_succeeded가 subscription_status를 active로 갱신"""
    mock_user.stripe_customer_id = "cus_123"
    mock_user.subscription_status = "past_due"
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user
    mock_db.execute = AsyncMock(return_value=mock_result)

    invoice_data = {"customer": "cus_123"}
    await stripe_service._handle_payment_succeeded(invoice_data, mock_db)

    assert mock_user.subscription_status == "active"
    mock_db.commit.assert_called_once()
