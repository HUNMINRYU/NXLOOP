# Stripe 구독 관리 구현 계획

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Stripe 웹훅 이벤트를 처리하여 사용자 구독 상태를 관리하고, 프론트엔드에서 tier 기반 UI를 제공한다.

**Architecture:** User 모델에 구독 필드 추가(심플 모델) → 웹훅 핸들러에서 DB 업데이트 → 구독 상태 API → 프론트엔드 Zustand 스토어 연동

**Tech Stack:** Python (FastAPI, SQLAlchemy, Alembic), stripe>=8.0.0, Next.js 16 (Zustand, TypeScript)

---

## Phase 1: 백엔드 기반

### Task 1: User 모델에 구독 필드 추가

**Files:**
- Modify: `src/infrastructure/database/models.py` (User 클래스)
- Modify: `src/infrastructure/database/connection.py` (_migrate_users_columns)
- Test: `tests/test_services/test_stripe_service.py`

**Step 1: User 모델에 4개 필드 추가**

`src/infrastructure/database/models.py`의 User 클래스에:

```python
# User 클래스 내부, job_title 필드 아래에 추가
stripe_customer_id: Mapped[str | None] = mapped_column(
    String(255), unique=True, nullable=True, index=True
)
tier: Mapped[str] = mapped_column(
    String(20), default="FREE", nullable=False, server_default="FREE"
)
subscription_status: Mapped[str] = mapped_column(
    String(20), default="none", nullable=False, server_default="none"
)
subscription_end_date: Mapped[datetime | None] = mapped_column(
    DateTime(timezone=True), nullable=True
)
```

**Step 2: SQLite 마이그레이션 함수 업데이트**

`src/infrastructure/database/connection.py`의 `_migrate_users_columns` 함수에:

```python
if "stripe_customer_id" not in names:
    sync_conn.execute(text("ALTER TABLE users ADD COLUMN stripe_customer_id TEXT UNIQUE"))
if "tier" not in names:
    sync_conn.execute(text("ALTER TABLE users ADD COLUMN tier TEXT DEFAULT 'FREE' NOT NULL"))
if "subscription_status" not in names:
    sync_conn.execute(text("ALTER TABLE users ADD COLUMN subscription_status TEXT DEFAULT 'none' NOT NULL"))
if "subscription_end_date" not in names:
    sync_conn.execute(text("ALTER TABLE users ADD COLUMN subscription_end_date TEXT"))
```

**Step 3: 테스트 실행으로 기존 테스트 깨지지 않는지 확인**

```bash
.venv/bin/python -m pytest tests/ -v --tb=short
```

Expected: 기존 테스트 모두 PASS

**Step 4: 커밋**

```bash
git add src/infrastructure/database/models.py src/infrastructure/database/connection.py
git commit -m "feat: User 모델에 구독 관련 필드 추가 (stripe_customer_id, tier, subscription_status, subscription_end_date)"
```

---

### Task 2: StripeService 웹훅 비즈니스 로직 구현

**Files:**
- Modify: `src/services/stripe_service.py`
- Test: `tests/test_services/test_stripe_service.py`

**Step 1: 실패하는 테스트 작성**

`tests/test_services/test_stripe_service.py`에 추가:

```python
@pytest.mark.asyncio
async def test_handle_checkout_session_completed_updates_user(mock_stripe_service):
    """checkout.session.completed 이벤트가 사용자 tier를 PRO로 업데이트하는지 검증"""
    # 이 테스트는 DB 세션 mock이 필요하므로 StripeService가 DB를 사용하도록 수정 후 작성
    pass

@pytest.mark.asyncio
async def test_handle_invoice_payment_failed_sets_past_due(mock_stripe_service):
    """invoice.payment_failed 이벤트가 subscription_status를 past_due로 변경하는지 검증"""
    pass
```

**Step 2: StripeService에 DB 세션 의존성 추가 및 핸들러 구현**

`src/services/stripe_service.py` 전체 재작성:

```python
import stripe
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import get_settings
from infrastructure.database.models import User
from utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


class StripeService:
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
```

**Step 3: 웹훅 엔드포인트에 DB 세션 전달**

`src/api/v1/endpoints/stripe.py` 수정:

```python
import stripe
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import get_settings
from infrastructure.database.connection import get_db_session
from services.stripe_service import StripeService
from utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)
settings = get_settings()


@router.post("/webhook", status_code=200)
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None),
    db: AsyncSession = Depends(get_db_session),
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
```

**Step 4: 테스트 재작성 (DB mock 포함)**

```python
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


@pytest.mark.asyncio
async def test_checkout_completed_updates_user_tier(stripe_service, mock_db, mock_user):
    """checkout.session.completed 이벤트가 사용자 tier를 PRO로 업데이트"""
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
    """invoice.payment_failed 이벤트가 subscription_status를 past_due로 변경"""
    mock_user.stripe_customer_id = "cus_123"
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user
    mock_db.execute = AsyncMock(return_value=mock_result)

    invoice_data = {"customer": "cus_123"}
    await stripe_service._handle_payment_failed(invoice_data, mock_db)

    assert mock_user.subscription_status == "past_due"
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_subscription_deleted_resets_to_free(stripe_service, mock_db, mock_user):
    """customer.subscription.deleted 이벤트가 tier를 FREE로, status를 canceled로 변경"""
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
    """매칭 사용자가 없으면 에러 없이 warning 로그만 남기고 종료"""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=mock_result)

    session_data = {"customer": "cus_unknown", "customer_email": "no@match.com"}
    await stripe_service._handle_checkout_completed(session_data, mock_db)
    mock_db.commit.assert_not_called()
```

**Step 5: 테스트 실행**

```bash
.venv/bin/python -m pytest tests/test_services/test_stripe_service.py -v
```

Expected: 8개 테스트 모두 PASS

**Step 6: 린팅 확인 후 커밋**

```bash
.venv/bin/python -m ruff check src/services/stripe_service.py src/api/v1/endpoints/stripe.py
git add src/services/stripe_service.py src/api/v1/endpoints/stripe.py tests/test_services/test_stripe_service.py
git commit -m "feat: Stripe 웹훅 비즈니스 로직 구현 (checkout, payment, subscription 이벤트 처리)"
```

---

### Task 3: 구독 상태 확인 API 엔드포인트

**Files:**
- Modify: `src/api/v1/endpoints/auth.py`
- Test: `tests/test_services/test_stripe_service.py` (또는 별도 테스트)

**Step 1: /auth/me 응답에 구독 정보 포함**

`src/api/v1/endpoints/auth.py`의 `/me` 엔드포인트 수정:

```python
@router.get("/me")
async def me(user: CurrentUser):
    return {
        "email": user.email,
        "role": user.role,
        "name": user.name,
        "tier": getattr(user, "tier", "FREE"),
        "subscription_status": getattr(user, "subscription_status", "none"),
    }
```

**Step 2: require_tier Dependency 추가**

`src/api/deps.py`에 추가:

```python
TIER_ORDER = {"FREE": 0, "PRO": 1, "BUSINESS": 2}

def require_tier(min_tier: str):
    """최소 구독 tier를 요구하는 의존성"""
    async def _checker(user: CurrentUser):
        user_tier = getattr(user, "tier", "FREE")
        if TIER_ORDER.get(user_tier, 0) < TIER_ORDER.get(min_tier, 0):
            raise HTTPException(
                status_code=403,
                detail=f"{min_tier} 이상 구독이 필요합니다.",
            )
        return user
    return _checker
```

**Step 3: 테스트 실행 및 커밋**

```bash
.venv/bin/python -m pytest tests/ -v --tb=short
git add src/api/v1/endpoints/auth.py src/api/deps.py
git commit -m "feat: /auth/me에 구독 정보 포함 및 require_tier Dependency 추가"
```

---

## Phase 2: 프론트엔드 연동

### Task 4: Zustand 스토어에 tier 추가

**Files:**
- Modify: `frontend/src/store/useAuthStore.ts`
- Modify: `frontend/src/components/AuthGate.tsx`

**Step 1: useAuthStore에 tier, subscriptionStatus 추가**

```typescript
interface AuthState {
    email: string | null;
    role: string | null;
    name: string | null;
    tier: string;
    subscriptionStatus: string;
    setAuth: (auth: { email: string | null; role: string | null; name: string | null; tier?: string; subscriptionStatus?: string }) => void;
    clearAuth: () => void;
}

// create 내부:
tier: 'FREE',
subscriptionStatus: 'none',
setAuth: (auth) => set({
    ...auth,
    tier: auth.tier ?? 'FREE',
    subscriptionStatus: auth.subscriptionStatus ?? 'none',
}),
clearAuth: () => {
    sessionStorage.removeItem('auth-storage');
    set({ email: null, role: null, name: null, tier: 'FREE', subscriptionStatus: 'none' });
},
```

**Step 2: AuthGate에서 tier 정보 반영**

`AuthGate.tsx`의 `/auth/me` 응답 처리:

```typescript
const me = await fetchMe();
setAuth({
    email: me.email,
    role: me.role,
    name: me.name,
    tier: me.tier ?? 'FREE',
    subscriptionStatus: me.subscription_status ?? 'none',
});
```

**Step 3: 커밋**

```bash
git add frontend/src/store/useAuthStore.ts frontend/src/components/AuthGate.tsx
git commit -m "feat: 프론트엔드 Zustand 스토어에 tier/subscriptionStatus 추가"
```

---

### Task 5: 결제 성공 페이지 백엔드 연동

**Files:**
- Modify: `frontend/src/app/payment/success/page.tsx`

**Step 1: localStorage 대신 백엔드 API 호출**

```typescript
useEffect(() => {
    if (hasRun.current) return;
    hasRun.current = true;

    // 백엔드에서 구독 상태 확인 (웹훅 처리 대기 포함)
    const checkSubscription = async () => {
        // 웹훅 처리 딜레이를 위해 3초 대기 후 조회
        await new Promise((r) => setTimeout(r, 3000));
        try {
            const me = await fetchMe();
            if (me.tier === 'PRO' || me.tier === 'BUSINESS') {
                setAuth({
                    email: me.email,
                    role: me.role,
                    name: me.name,
                    tier: me.tier,
                    subscriptionStatus: me.subscription_status,
                });
            }
        } catch {
            // 비로그인 상태에서도 결제 성공 화면은 표시
        }
    };

    void checkSubscription();
    // confetti 효과 (기존 유지)
    // ...
}, []);
```

**Step 2: 데모 안내 텍스트 업데이트**

"로컬 저장소에 등급을 기록해두었습니다" → 실제 결제 완료 메시지로 변경

**Step 3: 커밋**

```bash
git add frontend/src/app/payment/success/page.tsx
git commit -m "feat: 결제 성공 페이지를 백엔드 API 연동으로 전환"
```

---

## 검증 체크리스트

- [ ] 기존 테스트 모두 통과
- [ ] Stripe 웹훅 테스트 8개 통과
- [ ] 백엔드 린팅 통과 (`ruff check src/`)
- [ ] `/auth/me` 응답에 tier, subscription_status 포함
- [ ] 프론트엔드 빌드 성공 (`npm run build`)
