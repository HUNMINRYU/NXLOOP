# CSRF 보호 정책 - Nexloop AI

## 개요

Nexloop AI는 **Double Submit Cookie 패턴**을 사용하여 CSRF(Cross-Site Request Forgery) 공격을 방어합니다.

### 핵심 원리

1. **토큰 발급**: 사용자 로그인 시 무작위 CSRF 토큰 생성
2. **이중 저장**:
   - 쿠키에 저장 (`nexloop_csrf`, HttpOnly=False)
   - 클라이언트가 헤더로 전송 (`X-CSRF-Token`)
3. **검증**: 서버는 쿠키 값과 헤더 값이 일치하는지 확인
4. **차단**: 불일치 시 403 Forbidden 반환

### 왜 안전한가?

- **공격자는 JavaScript로 다른 도메인의 쿠키를 읽을 수 없음** (Same-Origin Policy)
- CSRF 공격은 쿠키는 자동 전송되지만, **커스텀 헤더는 추가할 수 없음**
- 따라서 정상 요청만 헤더와 쿠키 값이 일치하여 통과

---

## 보호 메커니즘

### 토큰 발급 (로그인/회원가입 시)

**위치**: `src/services/auth_service.py`, `src/api/v1/endpoints/auth.py`

```python
# 1. CSRF 토큰 생성
csrf_token = secrets.token_urlsafe(32)  # 256bit 랜덤 토큰

# 2. 쿠키에 저장
response.set_cookie(
    key="nexloop_csrf",
    value=csrf_token,
    httponly=False,      # ← JavaScript가 읽을 수 있어야 헤더 전송 가능
    secure=True,         # HTTPS에서만 전송
    samesite="strict",   # CSRF 추가 방어
    path="/",
)
```

### 토큰 검증 (미들웨어)

**위치**: `src/api/middleware/csrf.py`

**검증 대상**: POST, PUT, PATCH, DELETE 요청 (상태 변경 메서드)

**검증 로직**:
1. 세션 쿠키 존재 여부 확인 (`nexloop_session`)
2. 세션이 있으면:
   - CSRF 쿠키 확인 (`nexloop_csrf`)
   - CSRF 헤더 확인 (`X-CSRF-Token`)
   - **두 값이 일치**해야 통과
3. 불일치 또는 누락 시 → **403 Forbidden**

### 예외 경로 (CSRF 검증 스킵)

다음 경로는 CSRF 검증을 하지 않습니다:

| 카테고리 | 경로 | 이유 |
|---------|------|------|
| **인증** | `/auth/login`, `/auth/signup`, `/auth/logout` | 아직 세션 없음 |
| **Webhook** | `/webhooks/*`, `/api/v1/webhooks/*` | 외부 서비스 (Stripe, Scheduler) |
| **공개** | `/health`, `/docs`, `/openapi.json` | 상태 확인, 문서 |
| **안전한 메서드** | GET, HEAD, OPTIONS | 상태 변경 없음 |

---

## 프론트엔드 개발 가이드

### ✅ 권장: `lib/api.ts` 사용

**자동 CSRF 처리**를 위해 프로젝트의 표준 API 함수를 사용하세요:

```typescript
// frontend/src/lib/api.ts
import { request } from '@/lib/api';

// 자동으로 X-CSRF-Token 헤더 추가됨
const result = await request('/pipeline/run', {
  method: 'POST',
  body: { product_id: 123 },
});
```

**내부 동작**:
```typescript
function getCsrfHeader(): Record<string, string> {
  const csrfToken = getCookie('nexloop_csrf');
  return csrfToken ? { 'X-CSRF-Token': csrfToken } : {};
}
```

### ⚠️ 주의: 커스텀 fetch 사용 시

직접 `fetch`를 사용할 경우 **수동으로 헤더 추가**해야 합니다:

```typescript
// ❌ 잘못된 예 - 403 에러 발생
fetch('/pipeline/run', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ product_id: 123 }),
});

// ✅ 올바른 예 - CSRF 토큰 포함
function getCookie(name: string): string | null {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop()?.split(';').shift() || null;
  return null;
}

const csrfToken = getCookie('nexloop_csrf');
fetch('/pipeline/run', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-CSRF-Token': csrfToken || '',  // ← 반드시 추가
  },
  body: JSON.stringify({ product_id: 123 }),
});
```

### 🐛 403 에러 디버깅 체크리스트

POST/PUT/PATCH/DELETE 요청 시 403 에러가 발생한다면:

1. **개발자 도구 > Application > Cookies** 확인
   - `nexloop_session` 쿠키 존재하는가?
   - `nexloop_csrf` 쿠키 존재하는가?

2. **개발자 도구 > Network > 요청 헤더** 확인
   - `X-CSRF-Token` 헤더가 있는가?
   - 헤더 값 = 쿠키 값인가?

3. **경로 확인**
   - 예외 경로(`/auth/*`, `/webhooks/*`)가 아닌가?
   - 혹시 GET 요청으로 바꿀 수 있는가? (상태 변경 없는 경우)

4. **로그인 상태 확인**
   - 세션이 만료되었는가? → 재로그인 필요

---

## 백엔드 개발 가이드

### Webhook 엔드포인트 추가 시

새로운 Webhook을 추가할 때는 **CSRF 예외 경로에 등록**해야 합니다:

**파일**: `src/api/middleware/csrf.py`

```python
# 기존 코드
skip_prefixes = ("/webhooks/", "/api/v1/webhooks/")

# 새 Webhook 추가 시 자동으로 처리됨
# 예: /webhooks/new-service → CSRF 검증 스킵
```

**주의**: `/webhooks/` 또는 `/api/v1/webhooks/`로 시작하지 않는 경로는 수동 추가 필요:

```python
skip_paths = {
    "/auth/login",
    "/auth/signup",
    "/custom-webhook",  # ← 수동 추가
    # ...
}
```

### 보호 API vs 공개 API 구분

| API 유형 | 세션 필요 | CSRF 검증 | 예시 |
|---------|----------|----------|------|
| **보호 API** | ✅ 필요 | ✅ 검증 | `/pipeline/run`, `/admin/users` |
| **공개 API** | ❌ 불필요 | ❌ 스킵 | `/chat` (게스트), `/webhooks/*` |
| **인증 API** | ❌ 없음 | ❌ 스킵 | `/auth/login`, `/auth/signup` |

**설계 원칙**:
- 세션 쿠키가 있으면 → CSRF 검증 필수
- 세션 쿠키가 없으면 → CSRF 검증 스킵 (공격 대상 없음)

### 새 보호 API 추가 시

특별한 작업 **불필요** - 미들웨어가 자동 처리:

```python
# src/api/v1/endpoints/new_feature.py
@router.post("/protected-action")
async def protected_action(user: CurrentUser):  # ← 세션 인증 필요
    # CSRF 미들웨어가 자동으로 검증
    # 개발자는 비즈니스 로직만 작성
    return {"status": "success"}
```

---

## 보안 권장사항

### 1. HTTPS 필수

**프로덕션 환경에서는 반드시 HTTPS 사용**:
- `Secure` 쿠키 플래그 활성화
- 중간자 공격(MITM) 방지
- Cloud Run 배포 시 자동 HTTPS

### 2. SameSite 속성

현재 설정:
```python
samesite="strict"  # 가장 엄격한 보호
```

**효과**: 다른 사이트에서 발생한 요청은 쿠키를 전송하지 않음

### 3. HttpOnly 플래그

| 쿠키 | HttpOnly | 이유 |
|------|----------|------|
| `nexloop_session` | ✅ True | XSS 공격으로부터 세션 보호 |
| `nexloop_csrf` | ❌ False | JavaScript가 읽어서 헤더로 전송해야 함 |

### 4. 토큰 갱신 (향후 구현 예정)

**현재**: 로그인 시 발급된 토큰이 세션 만료(8시간)까지 유지
**계획**: 1시간마다 자동 갱신으로 XSS 공격 시 토큰 탈취 위험 감소

### 5. XSS 방어 병행

CSRF 토큰은 **XSS 공격에 취약**합니다 (JavaScript로 읽을 수 있음).
반드시 XSS 방어도 함께 구현하세요:

- ✅ 사용자 입력 sanitize (React는 기본 제공)
- ✅ Content-Security-Policy (CSP) 헤더 설정
- ✅ 외부 스크립트 검증
- ✅ HTML 이스케이프

---

## 테스트

### 테스트 커버리지

**파일**: `tests/test_csrf_middleware.py`

- **총 11개 테스트** (100% 커버리지)
- **실행 시간**: 1.2초

**테스트 실행**:
```bash
# CSRF 테스트만 실행
pytest tests/test_csrf_middleware.py -v

# 커버리지 포함
pytest tests/test_csrf_middleware.py --cov=src/api/middleware/csrf --cov-report=term-missing
```

### 테스트 시나리오

| 시나리오 | 예상 결과 |
|---------|----------|
| 세션 없음 + POST | 200 OK (CSRF 스킵) |
| 세션 있음 + CSRF 없음 | 403 Forbidden |
| 세션 있음 + CSRF 일치 | 200 OK |
| 세션 있음 + CSRF 불일치 | 403 Forbidden |
| GET 요청 | 200 OK (항상 스킵) |
| `/webhooks/*` 경로 | 200 OK (항상 스킵) |

---

## FAQ

### Q1. 왜 Double Submit Cookie인가요? JWT 기반 CSRF 토큰은?

**답변**:
- Double Submit Cookie는 **구현이 간단**하고 **서버 부하가 적음** (세션 스토어에 저장 불필요)
- JWT는 서명 검증 오버헤드가 있으며, CSRF 방어에는 과도함
- Nexloop AI는 이미 세션 쿠키 인증을 사용하므로 일관성 유지

### Q2. 게스트 사용자도 CSRF 토큰이 필요한가요?

**답변**:
- 아니요. **세션 쿠키가 없으면 CSRF 검증 스킵**
- 게스트 챗봇(`/chat`) 등은 세션 없이 동작하므로 CSRF 불필요

### Q3. API 키 인증 엔드포인트는?

**답변**:
- API 키 인증은 **CSRF 공격 대상이 아님** (브라우저 쿠키 사용 안 함)
- 필요시 `/api-key/*` 경로를 예외 경로에 추가

### Q4. 403 에러 시 자동 재시도가 필요한가요?

**답변**:
- **불필요**. 403은 명확한 인증 실패이므로 재시도해도 실패
- 대신 **재로그인 유도** 또는 **토큰 갱신** (향후 구현)

### Q5. 토큰 길이(32바이트)는 충분한가요?

**답변**:
- ✅ 충분함. `secrets.token_urlsafe(32)` = 256bit 엔트로피
- 무차별 대입 공격 불가능 (2^256 경우의 수)

---

## 참고 자료

- **OWASP CSRF Prevention Cheat Sheet**: https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html
- **Double Submit Cookie 패턴**: https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html#double-submit-cookie
- **프로젝트 구현**:
  - 미들웨어: `src/api/middleware/csrf.py`
  - 인증 서비스: `src/services/auth_service.py`
  - 인증 엔드포인트: `src/api/v1/endpoints/auth.py`
  - 프론트엔드: `frontend/src/lib/api.ts`
  - 테스트: `tests/test_csrf_middleware.py`

---

**마지막 업데이트**: 2026-02-07
**테스트 커버리지**: 100% (20/20 statements)
**프로덕션 준비**: ✅ 완료
