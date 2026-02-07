import stripe
from config.settings import get_settings
from utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


class StripeService:
    def __init__(self) -> None:
        if settings.stripe_secret_key:
            stripe.api_key = settings.stripe_secret_key
        else:
            logger.warning("Stripe Secret Key is missing. StripeService may not function correctly.")

    async def process_webhook_event(self, event: stripe.Event) -> None:
        """
        Stripe Webhook 이벤트를 처리합니다.
        """
        event_type = event.get("type")
        logger.info(f"Processing Stripe event: {event_type}")

        if event_type == "checkout.session.completed":
            await self._handle_checkout_session_completed(event["data"]["object"])
        elif event_type == "invoice.payment_succeeded":
            await self._handle_invoice_payment_succeeded(event["data"]["object"])
        elif event_type == "invoice.payment_failed":
            await self._handle_invoice_payment_failed(event["data"]["object"])
        else:
            logger.info(f"Unhandled event type: {event_type}")

    async def _handle_checkout_session_completed(self, session: dict) -> None:
        """
        checkout.session.completed 이벤트 핸들링
        """
        session_id = session.get("id")
        customer_id = session.get("customer")
        logger.info(f"Checkout session completed: {session_id}, Customer: {customer_id}")
        # TODO: 결제 완료 후 비즈니스 로직 구현 (예: 사용자 구독 상태 업데이트, 크레딧 지급 등)

    async def _handle_invoice_payment_succeeded(self, invoice: dict) -> None:
        """
        invoice.payment_succeeded 이벤트 핸들링
        """
        invoice_id = invoice.get("id")
        customer_id = invoice.get("customer")
        logger.info(f"Invoice payment succeeded: {invoice_id}, Customer: {customer_id}")
        # TODO: 정기 결제 성공 처리 로직

    async def _handle_invoice_payment_failed(self, invoice: dict) -> None:
        """
        invoice.payment_failed 이벤트 핸들링
        """
        invoice_id = invoice.get("id")
        customer_id = invoice.get("customer")
        logger.error(f"Invoice payment failed: {invoice_id}, Customer: {customer_id}")
        # TODO: 결제 실패 알림 및 재결제 유도 로직
