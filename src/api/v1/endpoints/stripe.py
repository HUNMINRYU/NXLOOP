import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import CurrentUser
from config.settings import get_settings
from infrastructure.database.connection import get_db_session
from schemas.requests import StripeCreateCheckoutSessionRequest
from services.stripe_service import StripeService
from utils.logger import (
    get_logger,
    log_feature_end,
    log_feature_fail,
    log_feature_start,
)

router = APIRouter()
logger = get_logger(__name__)
settings = get_settings()
email_validator = TypeAdapter(EmailStr)

# 모듈 로드 시 Stripe API 키 설정
if settings.stripe_secret_key:
    stripe.api_key = settings.stripe_secret_key


@router.post("/create-checkout-session")
async def create_checkout_session(
    request: StripeCreateCheckoutSessionRequest,
    user: CurrentUser,
) -> dict[str, str]:
    """Stripe Checkout Session을 생성하고 결제 URL을 반환합니다."""
    log_feature_start("stripe_create_checkout", user.email)
    if not settings.stripe_secret_key:
        log_feature_fail("stripe_create_checkout", "Stripe Secret Key not configured")
        logger.error("Stripe Secret Key가 설정되지 않았습니다.")
        raise HTTPException(status_code=500, detail="Stripe configuration error")

    try:
        try:
            email_validator.validate_python(user.email)
        except ValidationError as e:
            log_feature_fail("stripe_create_checkout", f"invalid user email: {user.email}")
            logger.error("유효하지 않은 사용자 이메일입니다: %s", user.email)
            raise HTTPException(status_code=400, detail="유효하지 않은 이메일 형식입니다.") from e

        frontend_url = settings.app.frontend_url or settings.app.app_url
        if request.plan == "BUSINESS":
            # Pricing에서 Business는 "Contact Sales" 플로우로 분리한다.
            raise HTTPException(
                status_code=400,
                detail="BUSINESS plan is sales-only. Please contact sales.",
            )

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
            client_reference_id=str(user.id),
            metadata={"user_id": str(user.id), "email": user.email},
            mode="subscription",
            # 결제 완료/취소 후에는 "프론트"로 돌아가야 합니다.
            # Stripe는 CHECKOUT_SESSION_ID 토큰을 success_url에 주입할 수 있습니다.
            success_url=(
                f"{frontend_url}/payment/success"
                f"?session_id={{CHECKOUT_SESSION_ID}}"
            ),
            cancel_url=f"{frontend_url}/pricing",
        )
        log_feature_end("stripe_create_checkout", extra_detail="url created")
        return {"url": session.url}
    except stripe.StripeError as e:
        log_feature_fail("stripe_create_checkout", str(e))
        logger.error("Stripe Checkout Session 생성 실패: %s", e)
        raise HTTPException(status_code=500, detail="결제 세션 생성에 실패했습니다.") from e


@router.post("/webhook", status_code=200)
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    """Stripe Webhook 수신 엔드포인트"""
    log_feature_start("stripe_webhook", "event receive")
    if not settings.stripe_webhook_secret:
        log_feature_fail("stripe_webhook", "Webhook secret not configured")
        logger.error("Stripe Webhook Secret이 설정되지 않았습니다.")
        raise HTTPException(status_code=500, detail="Webhook configuration error")

    payload = await request.body()
    # Stripe는 "Stripe-Signature" 헤더로 서명을 전달한다.
    # FastAPI Header() 매핑에 의존하면 alias 실수로 서명을 못 읽는 케이스가 있어,
    # request.headers에서 직접 추출해 안정적으로 처리한다.
    stripe_signature = request.headers.get("Stripe-Signature") or request.headers.get(
        "stripe-signature"
    )
    if not stripe_signature:
        log_feature_fail("stripe_webhook", "missing signature header")
        logger.error("Stripe-Signature 헤더가 누락되었습니다.")
        raise HTTPException(status_code=400, detail="Missing Stripe-Signature header")

    # 운영 중에는 실수로 동일 URL의 Webhook endpoint를 여러 개 만들어
    # Signing secret(whsec)이 복수로 존재하는 경우가 있다.
    # 빠른 복구를 위해 쉼표로 여러 secret을 설정하면 모두 시도한다.
    raw_secrets = settings.stripe_webhook_secret
    secrets = [s.strip() for s in raw_secrets.split(",") if s.strip()]
    if not secrets:
        secrets = [raw_secrets]

    event = None
    last_sig_error: stripe.SignatureVerificationError | None = None
    for secret in secrets:
        try:
            event = stripe.Webhook.construct_event(payload, stripe_signature, secret)
            last_sig_error = None
            break
        except stripe.SignatureVerificationError as e:
            last_sig_error = e
        except ValueError as e:
            # payload가 아예 JSON이 아니거나 깨진 경우는 secret 재시도해도 의미가 없다.
            log_feature_fail("stripe_webhook", "invalid payload")
            logger.error("잘못된 payload: %s", e)
            raise HTTPException(status_code=400, detail="Invalid payload") from e

    if event is None:
        assert last_sig_error is not None
        log_feature_fail("stripe_webhook", "invalid signature")
        logger.error(
            "잘못된 서명: %s | user_agent=%s | secrets=%d",
            last_sig_error,
            request.headers.get("User-Agent", ""),
            len(secrets),
        )
        raise HTTPException(
            status_code=400, detail="Invalid signature"
        ) from last_sig_error

    service = StripeService()
    await service.process_webhook_event(event, db)
    log_feature_end("stripe_webhook", extra_detail=f"event={event.get('type', '')}")
    return {"status": "success"}
