<div align="center">
  <img src="https://img.shields.io/badge/Nexloop-AI-7c3aed?style=for-the-badge&logoScale=1.2" alt="Nexloop AI" />
  <p><strong>기업의 브랜드 가치와 데이터를 비즈니스 자산으로 전환하는 엔터프라이즈 AI 플랫폼</strong></p>
  <p>
    <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=Python&logoColor=white" />
    <img src="https://img.shields.io/badge/Vertex_AI-4285F4?style=for-the-badge&logo=google-cloud&logoColor=white" />
    <img src="https://img.shields.io/badge/Next.js-16-000000?style=for-the-badge&logo=next.js&logoColor=white" />
    <img src="https://img.shields.io/badge/FastAPI-0.109+-009688?style=for-the-badge&logo=fastapi&logoColor=white" />
  </p>
  <p align="center">
    <a href="#-서비스-소개">서비스 소개</a> •
    <a href="#-시스템-구조">시스템 구조</a> •
    <a href="#-기술-스택">기술 스택</a> •
    <a href="#-로컬-실행">로컬 실행</a> •
    <a href="#-코드-품질--리뷰">코드 품질</a> •
    <a href="#-문서--개발-가이드">문서</a>
  </p>
</div>

---

## 👀 서비스 소개

**Nexloop AI**는 Google Cloud Vertex AI(Gemini, Veo, Discovery Engine) 기반의 마케팅·크리에이티브 자동화 플랫폼입니다.

- **데이터 수집·인사이트**: YouTube·네이버 등 소스 수집 → **X-Algorithm Pipeline**으로 인사이트 추출
- **크리에이티브**: Veo 영상·Gemini 썸네일 생성, Brand Kit 연동
- **거버넌스**: 감사 로그(Audit Log), 팀/권한 관리, 스케줄 모니터링
- **결제·구독**: Stripe 연동(체크아웃, 웹훅), FREE/PRO/BUSINESS 요금제

---

## 📅 프로젝트 기간

**2024.01 ~ 진행 중** (Active Development)

---

## ⚙️ 시스템 구조

### 아키텍처 개요

```
[User] ←→ [Next.js 16 Frontend] ←→ [FastAPI Backend]
                                          ↓
                    [X-Algorithm Pipeline] ←→ [Gemini / Veo / Discovery Engine]
                                          ↓
                                    [GCS / SQLite·Cloud SQL]
```

- **백엔드**: FastAPI, 라우터는 `/` 및 `/api/v1` 이중 노출(기존 클라이언트·웹훅 호환). 인증은 쿠키 기반 세션 + **CSRF 보호**(Double Submit Cookie).
- **파이프라인**: Source → Hydration → Filter → Scorer → Selector. 결과는 인메모리·파일·GCS 동기화, 감사는 RDB `audit_logs`.
- **프론트**: Next.js 16 App Router, React 19, Zustand, Tailwind v4.

### 데이터·저장

| 용도 | 저장소 |
|------|--------|
| 파이프라인 결과·미디어 메타 | 인메모리 캐시, `outputs/metadata/*.json`, Cloud Run 시 GCS |
| 감사·거버넌스 | RDB `audit_logs` (SQLAlchemy, SQLite/Cloud SQL) |
| 사용자·세션·요금제 | RDB `users`, `user_sessions` 등 (Alembic 마이그레이션) |

### Use Case 요약

- **마케터**: 데이터 수집·마이닝, 인사이트 승인/반려, Veo 영상 생성, Notion 내보내기
- **시스템 관리자**: 스케줄·작업 모니터링, 팀/권한·감사 로그

---

## ⛏ 기술 스택

| 구분 | 기술 |
|------|------|
| **Backend** | Python 3.10+, FastAPI, SQLAlchemy 2, Pydantic v2, aiosqlite, Stripe |
| **Frontend** | Next.js 16, React 19, TypeScript, Tailwind CSS v4, Zustand |
| **AI·Infra** | Vertex AI, Gemini, Veo, Discovery Engine, GCS, Cloud Scheduler |
| **품질** | pytest, pytest-asyncio, ruff, black, mypy (백엔드), ESLint (프론트) |

---

## 🚀 로컬 실행

**처음 프로젝트를 실행하는 경우**는 **[docs/GETTING_STARTED.md](docs/GETTING_STARTED.md)** 를 따라 진행하세요. (가상환경·DB 마이그레이션·환경 변수·트러블슈팅 포함)

### 요약

- **백엔드**: `./start_backend.sh` (또는 `PYTHONPATH=src uvicorn app:app --reload --host 0.0.0.0 --port 8000`) → http://localhost:8000, http://localhost:8000/docs
- **프론트엔드**: `cd frontend && npm install && npm run dev` → http://localhost:3000 (필수: `NEXT_PUBLIC_API_URL=http://localhost:8000`, 루트 `.env` 에 `CORS_ORIGINS=http://localhost:3000`)

### 인사이트 승인/반려

- **동작 조건**: 파이프라인 실행이 끝나 해당 결과가 존재할 때, 로그인 사용자 **role** 이 **admin** 또는 **approver** 인 경우에만 승인/거부 버튼이 노출되며 API 호출이 가능합니다. 기본 가입 role 은 `editor` 이므로 테스트 시 DB 에서 role 을 변경하거나 admin 계정을 사용하세요. 자세한 조건과 플로우는 [docs/CODEBASE.md](docs/CODEBASE.md) §5.1 참고.

---

## 🔍 코드 품질 & 리뷰

AI 기반 코드 리뷰 관점에서 정리한 품질 요약입니다.

### 보안 (Security)

- **CSRF**: 쿠키 기반 인증 구간에 Double Submit Cookie 미들웨어 적용. 웹훅·헬스 등 예외 경로 명시. (`src/api/middleware/csrf.py`, `docs/CSRF_POLICY.md`)
- **인증·세션**: 패스워드 bcrypt, 세션 DB 저장, 401 시 클라이언트 세션·채팅 초기화.
- **Stripe**: 웹훅 서명 검증, 시크릿은 환경 변수로 주입.
- **권장**: API 키·시크릿 로그/에러 메시지에 포함 금지(현재 PII 마스킹·민감 정보 가이드 있음).

### 아키텍처 (Architecture)

- **계층 분리**: `api/` → `services/` → `core/`(인터페이스·모델) → `infrastructure/`. 내부 계층이 외부에 의존하지 않는 방향 유지.
- **파이프라인**: 단일 오케스트레이터 + 단계별 스테이지(Source, Hydration, Filter, Scorer, Selector), 단위 테스트·메트릭 평가 가능.
- **일관 로깅**: `[FEATURE]` 태그와 `log_feature_start`/`log_feature_end`/`log_feature_fail`로 기능 단위 추적. (`docs/.../logging-strategy.md`)

### 성능 (Performance)

- **파이프라인**: 대량 데이터 시 배치·스트리밍 고려. GCS는 Signed URL로 클라이언트 직접 다운로드 유도.
- **챗봇**: 비로그인 IP·FREE tier 일일 한도(규칙·DB 집계), PRO/BUSINESS 무제한. 남은 횟수 API로 서버와 동기화.

### 테스트 (Testing)

- **백엔드**: pytest, pytest-asyncio, conftest 기반. API(인증, admin evaluate, 스트라이프 웹훅), 서비스(챗봇, 파이프라인, CTR, 시맨틱 스코어 등), CSRF·CORS·코어 모델 등 다수 커버.
- **실행**: `python -m pytest tests/ -v` (가상환경 활성화 필수).  
- **권장**: 신규 기능·버그 수정 시 실패하는 테스트 먼저 작성 후 구현(TDD).

### 유지보수성 (Maintainability)

- **타입**: Python 타입 힌트·mypy, TypeScript strict. API 스키마(Pydantic)·프론트 타입 정리.
- **예외**: `raise ... from e` 패턴, 도메인별 예외·HTTP 변환 정리.
- **문서**: `RULES.md`, `CLAUDE.md`, `docs/` 하위에 워크플로·로깅·결제·CSRF·챗봇 등 정리.

---

## 📚 문서 & 개발 가이드

| 문서 | 내용 |
|------|------|
| [RULES.md](./RULES.md) | 프로젝트 규칙, Git 워크플로우, 커밋 컨벤션 |
| [CLAUDE.md](./CLAUDE.md) | Claude·에이전트 작업 가이드, 구조·테스트·환경 변수 |
| [docs/CSRF_POLICY.md](./docs/CSRF_POLICY.md) | CSRF 보호 정책·예외 경로·개발 체크리스트 |
| `docs/2026-02-08/cursor/logging-strategy.md` | [FEATURE] 로깅 전략·기능 목록·적용 현황 |
| `docs/2026-02-08/cursor/git-strategy.md` | 브랜치 전략(main/develop), 배포 워크플로우 |

---

## 🖥 화면 구성

- **랜딩·요금제**: 메인, 가격 플랜, 결제 성공/취소 플로우
- **파이프라인**: 제품별 실행·상태·결과 조회
- **챗봇**: 무료 한도·로그인 연동·Discovery Engine RAG
- **관리자**: 감사 로그, 스케줄·팀 관리(권한에 따라)

---

## 🗺 로드맵 요약

- **Phase 1 (현재)**: X-Algorithm 파이프라인, Veo·Gemini 크리에이티브, 감사·권한, Stripe 구독
- **Phase 2**: RAG·챗봇 고도화, Brand Kit 강화, 멀티 채널 확장
- **Phase 3**: 외부 API·CRM 연동, 커스텀 모델·피드백 루프

---

## 👨‍👩‍👧‍👦 기여

- **Lead Architect / AI Engineer**: 류훈민 (HUNMINRYU)  
  전계층 설계·인프라, X-Algorithm 파이프라인, Gemini/Veo 연동, Next.js B2B 대시보드.

---

<div align="center">
  <strong>Built with Intelligence, Driven by Marketing Value — Nexloop AI</strong>
</div>
