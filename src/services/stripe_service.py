import stripe
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import get_settings
from infrastructure.database.models import User
from services.notification_service import send_email, send_slack_notification
from utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


class StripeService:
    """Stripe 웹훅 이벤트 처리 서비스"""

    def __init__(self) -> None:
        if settings.stripe_secret_key:
            stripe.api_key = settings.stripe_secret_key
        else:
            logger.warning("Stripe Secret Key가 설정되지 않았습니다.")

    async def process_webhook_event(
        self, event: stripe.Event, db: AsyncSession
    ) -> None:
        """Stripe Webhook 이벤트를 처리합니다."""
        event_type = event.get("type")
        logger.info("Stripe 이벤트 처리 시작: %s", event_type)

        handlers = {
            "checkout.session.completed": self._handle_checkout_completed,
            "invoice.payment_succeeded": self._handle_payment_succeeded,
            "invoice.payment_failed": self._handle_payment_failed,
            "customer.subscription.deleted": self._handle_subscription_deleted,
        }

        handler = handlers.get(event_type)
        if handler:
            await handler(event["data"]["object"], db)
        else:
            logger.info("처리하지 않는 이벤트 타입: %s", event_type)

    async def _find_user_by_stripe_customer(
        self, customer_id: str, db: AsyncSession
    ) -> User | None:
        """stripe_customer_id로 사용자를 조회합니다."""
        stmt = select(User).where(User.stripe_customer_id == customer_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def _find_user_by_email(
        self, email: str, db: AsyncSession
    ) -> User | None:
        """이메일로 사용자를 조회합니다."""
        stmt = select(User).where(User.email == email)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def _handle_checkout_completed(
        self, session: dict, db: AsyncSession
    ) -> None:
        """checkout.session.completed: 최초 결제 성공 처리"""
        customer_id = session.get("customer")
        customer_email = session.get("customer_email") or session.get(
            "customer_details", {}
        ).get("email")

        # 사용자 매핑: stripe_customer_id → email fallback
        user = None
        if customer_id:
            user = await self._find_user_by_stripe_customer(customer_id, db)
        if not user and customer_email:
            user = await self._find_user_by_email(customer_email, db)

        if not user:
            logger.warning(
                "결제 완료 이벤트: 매칭되는 사용자 없음 (customer=%s, email=%s)",
                customer_id,
                customer_email,
            )
            return

        # 사용자 구독 정보 업데이트
        if customer_id and not user.stripe_customer_id:
            user.stripe_customer_id = customer_id
        user.tier = "PRO"
        user.subscription_status = "active"
        await db.commit()
        logger.info(
            "구독 활성화: user=%s, tier=PRO, customer=%s",
            user.email,
            customer_id,
        )

        # 알림 전송
        send_slack_notification(
            f"💳 Checkout completed\n"
            f"User: {user.email}\n"
            f"Plan: PRO\n"
            f"Customer: {customer_id}"
        )
        send_email(
            to=user.email,
            subject="Payment succeeded - Subscription activated",
            body=(
                "Your payment was successful.\n"
                "Plan: PRO\n"
                "Thank you for subscribing!"
            ),
        )

    async def _handle_payment_succeeded(
        self, invoice: dict, db: AsyncSession
    ) -> None:
        """invoice.payment_succeeded: 정기 결제 갱신 성공"""
        customer_id = invoice.get("customer")
        if not customer_id:
            return

        user = await self._find_user_by_stripe_customer(customer_id, db)
        if not user:
            logger.warning("결제 갱신: 매칭 사용자 없음 (customer=%s)", customer_id)
            return

        user.subscription_status = "active"
        await db.commit()
        logger.info("구독 갱신 확인: user=%s", user.email)

        # 알림 전송
        amount_paid = invoice.get("amount_paid", 0)
        send_slack_notification(
            f"🔄 Payment succeeded (renewal)\n"
            f"User: {user.email}\n"
            f"Amount: {amount_paid / 100}"
        )
        send_email(
            to=user.email,
            subject="Payment succeeded - Subscription renewed",
            body=(
                f"Your subscription renewal payment was successful.\n"
                f"Plan: {user.tier}\n"
                f"Amount: {amount_paid / 100}"
            ),
        )

    async def _handle_payment_failed(
        self, invoice: dict, db: AsyncSession
    ) -> None:
        """invoice.payment_failed: 결제 실패 (유예 상태로 전환)"""
        customer_id = invoice.get("customer")
        if not customer_id:
            return

        user = await self._find_user_by_stripe_customer(customer_id, db)
        if not user:
            logger.warning("결제 실패: 매칭 사용자 없음 (customer=%s)", customer_id)
            return

        user.subscription_status = "past_due"
        await db.commit()
        logger.error("결제 실패 → past_due: user=%s", user.email)

        # 알림 전송
        send_slack_notification(
            f"⚠️ Payment failed\n"
            f"User: {user.email}\n"
            f"Status: past_due\n"
            f"Customer: {customer_id}"
        )
        send_email(
            to=user.email,
            subject="Payment failed - Action required",
            body=(
                "Your latest payment could not be processed.\n"
                "Please update your payment method to keep your subscription active."
            ),
        )

    async def _handle_subscription_deleted(
        self, subscription: dict, db: AsyncSession
    ) -> None:
        """customer.subscription.deleted: 구독 취소/만료"""
        customer_id = subscription.get("customer")
        if not customer_id:
            return

        user = await self._find_user_by_stripe_customer(customer_id, db)
        if not user:
            logger.warning("구독 취소: 매칭 사용자 없음 (customer=%s)", customer_id)
            return

        user.tier = "FREE"
        user.subscription_status = "canceled"
        await db.commit()
        logger.info("구독 취소 → FREE: user=%s", user.email)

        # 알림 전송
        send_slack_notification(
            f"🚫 Subscription canceled\n"
            f"User: {user.email}\n"
            f"Status: canceled → FREE\n"
            f"Customer: {customer_id}"
        )
        send_email(
            to=user.email,
            subject="Subscription canceled",
            body=(
                "Your subscription has been canceled.\n"
                "Your plan has been downgraded to FREE.\n"
                "You can re-subscribe anytime from the pricing page."
            ),
        )
