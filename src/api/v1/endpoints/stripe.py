import stripe
from fastapi import APIRouter, Header, HTTPException, Request
from services.stripe_service import StripeService
from config.settings import get_settings
from utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)
settings = get_settings()


@router.post("/webhook", status_code=200)
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None),
) -> dict[str, str]:
    """
    Stripe Webhook 수신 엔드포인트
    """
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
    await service.process_webhook_event(event)

    return {"status": "success"}
