import stripe
from fastapi import APIRouter, Header, Request, HTTPException, Depends
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
        logger.error("Stripe Webhook Secret is not configured.")
        raise HTTPException(status_code=500, detail="Webhook configuration error")

    payload = await request.body()

    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, settings.stripe_webhook_secret
        )
    except ValueError as e:
        logger.error(f"Invalid payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Invalid signature: {e}")
        raise HTTPException(status_code=400, detail="Invalid signature")

    service = StripeService()
    await service.process_webhook_event(event)

    return {"status": "success"}
