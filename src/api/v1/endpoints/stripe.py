import stripe
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import CurrentUser
from config.settings import get_settings
from infrastructure.database.connection import get_db_session
from services.stripe_service import StripeService
from utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)
settings = get_settings()


@router.post("/create-checkout-session")
async def create_checkout_session(user: CurrentUser) -> dict[str, str]:
    """Stripe Checkout Session을 생성하고 결제 URL을 반환합니다."""
    if not settings.stripe_secret_key:
        logger.error("Stripe Secret Key가 설정되지 않았습니다.")
        raise HTTPException(status_code=500, detail="Stripe configuration error")

    try:
        session = stripe.checkout.Session.create(
            customer_email=user.email,
            line_items=[
                {
                    "price_data": {
                        "currency": "krw",
                        "product_data": {"name": "Nexloop PRO"},
                        "unit_amount": 29000,
                        "recurring": {"interval": "month"},
                    },
                    "quantity": 1,
                }
            ],
            mode="subscription",
            success_url="http://localhost:3000/payment/success",
            cancel_url="http://localhost:3000/pricing",
        )
    except stripe.StripeError as e:
        logger.error("Stripe Checkout Session 생성 실패: %s", e)
        raise HTTPException(status_code=500, detail="결제 세션 생성에 실패했습니다.") from e

    return {"url": session.url}


@router.post("/webhook", status_code=200)
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None),
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> dict[str, str]:
    """Stripe Webhook 수신 엔드포인트"""
    if not settings.stripe_webhook_secret:
        logger.error("Stripe Webhook Secret이 설정되지 않았습니다.")
        raise HTTPException(status_code=500, detail="Webhook configuration error")

    payload = await request.body()

    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, settings.stripe_webhook_secret
        )
    except ValueError as e:
        logger.error("잘못된 payload: %s", e)
        raise HTTPException(status_code=400, detail="Invalid payload") from e
    except stripe.SignatureVerificationError as e:
        logger.error("잘못된 서명: %s", e)
        raise HTTPException(status_code=400, detail="Invalid signature") from e

    service = StripeService()
    await service.process_webhook_event(event, db)

    return {"status": "success"}
