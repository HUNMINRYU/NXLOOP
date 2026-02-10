# 로깅 전략 — 실행 중인 기능 파악

> **목적:** 항상 **무슨 기능이 실행되고 있는지** 로그만으로 파악할 수 있도록 일관된 태그와 헬퍼 사용.

---

## 1. [FEATURE] 태그

- **접두어:** 모든 기능 진입/완료/실패 시 `[FEATURE]` 로 시작하는 로그를 남긴다.
- **헬퍼:** `utils.logger` 의 `log_feature_start`, `log_feature_end`, `log_feature_fail` 사용.

| 함수 | 용도 |
|------|------|
| `log_feature_start(feature, detail="")` | 기능 진입 시 1회 호출 |
| `log_feature_end(feature, duration_sec=0, extra_detail="")` | 기능 정상 완료 시 |
| `log_feature_fail(feature, error="")` | 기능 실패 시 |

- **feature 이름:** 소문자·스네이크, 예: `auth_login`, `pipeline_run`, `webhook_pipeline`, `app_startup`.

---

## 2. 기능 이름 목록 (권장)

| feature | 설명 | 로그 위치 |
|---------|------|-----------|
| `app_startup` | 앱 기동 완료 | lifespan |
| `app_shutdown` | 앱 종료 | lifespan |
| `health_check` | 헬스 체크 요청 | GET /health |
| `auth_signup` | 회원가입 | POST /auth/signup |
| `auth_login` | 로그인 | POST /auth/login |
| `auth_logout` | 로그아웃 | POST /auth/logout |
| `pipeline_run` | 파이프라인 실행(태스크) | pipeline_runner / execute |
| `webhook_pipeline` | 스케줄러→파이프라인 웹훅 | POST webhooks |
| `ctr_predict` | CTR 예측 API | pipeline/ctr 등 |
| `admin_evaluate_model` | 모델 평가 API (예측/순위/비교) | POST admin/evaluate-model/* |
| `chat_remaining` | 챗봇 남은 횟수 조회 (비로그인 IP / 로그인 FREE 10회·일, 리필 시각 포함) | GET /chat/remaining |
| `chat_reply` | 챗봇 답변 생성 (일반) | POST /chat |
| `chat_reply_stream` | 챗봇 답변 스트리밍 | POST /chat/stream |
| `stripe_create_checkout` | Stripe 결제 세션 생성 | POST /api/v1/stripe/create-checkout-session |
| `stripe_webhook` | Stripe Webhook 수신 | POST /api/v1/stripe/webhook |
| `leads_capture` | 리드 캡처 (이메일 수집) | POST /leads |
| `refresh_signed_url` | GCS 서명 URL 재발급 | POST /refresh-url |
| `search_discovery` | Discovery Engine 검색 (PRO) | GET /search/discovery |
| `studio_draft` | 스튜디오 초안 프롬프트 생성 (PRO) | POST /studio/draft |
| `studio_refine` | 스튜디오 프롬프트 고도화 (PRO) | POST /studio/refine |
| `pipeline_select_output` | Create 산출물(썸네일/비디오) 1개 채택 | POST /pipeline/result/{task_id}/select-output |
| `pipeline_generate_video_selected_thumbnail` | 선택 썸네일 기반 I2V 비디오 재생성 + 자동 채택 | POST /pipeline/result/{task_id}/generate-video-from-selected-thumbnail |
| `content_get_thumbnail_styles` | 썸네일 스타일 목록 조회 | GET /thumbnail/styles |
| `content_generate_hooks` | 훅 문구 생성 (style별) | POST /hooks/generate |
| `content_thumbnail_compare` | 여러 스타일 썸네일 비교 생성 | POST /thumbnail/compare-styles |
| `content_get_hook_styles` | 훅 전략 9종 목록 조회 | GET /hooks/styles |
| `content_get_video_presets` | 비디오 프리셋 조회 | GET /video/presets |
| `content_video_generate` | 비디오 생성 (Standard/Custom) | POST /video/generate |
| `content_video_extend` | 비디오 확장 생성 | POST /video/extend |
| `insights_upload` | 인사이트 수동 업로드 | POST /insights/upload |
| `insights_ingest_naver` | 네이버 인사이트 수집 | POST /insights/external/naver |
| `insights_ingest_youtube` | YouTube 인사이트 수집 | POST /insights/external/youtube |
| `insights_search` | 인사이트 검색 | GET /insights/search |
| `insights_metrics` | 인사이트 지표 조회 | GET /insights/metrics |
| `insights_teams` | 팀 목록 조회 | GET /insights/teams |
| `insights_failures` | 실패 이력 조회 | GET /insights/failures |
| `insights_daily_report` | 일일 리포트 생성 | POST /insights/reports/daily |
| `products_list` | 상품 목록 조회 | GET /products/ |
| `products_detail` | 상품 상세 조회 | GET /products/{name} |

---

## 3. 적용 현황 (2026-02-09 업데이트)

| 라우터/파일 | 적용된 feature | 비고 |
|-------------|----------------|------|
| `app.py` | app_startup, app_shutdown | lifespan |
| `auth.py` | auth_signup, auth_login, auth_logout | |
| `chat.py` | chat_remaining, chat_reply, chat_reply_stream | 독립 라우터로 분리됨 |
| `misc.py` | health_check, leads_capture, refresh_signed_url, search_discovery | chat 관련은 chat.py로 이동 |
| `stripe.py` | stripe_create_checkout, stripe_webhook | |
| `webhooks.py` | webhook_pipeline | |
| `admin.py` | admin_evaluate_model (predictions/ranking/compare) | cache/roles/teams/schedules 등은 추후 확장 |
| `pipeline_runner.py` | pipeline_run | HTTP POST /run 은 runner 내부에서 로깅 |
| `studio.py` | studio_draft, studio_refine | |
| `pipeline.py` | pipeline_select_output, pipeline_generate_video_selected_thumbnail | (부분 적용) 나머지 history/status/run/analysis/export 등은 필요 시 추가 |
| `content.py` | content_get_thumbnail_styles, content_generate_hooks, content_thumbnail_compare, content_get_hook_styles, content_get_video_presets, content_video_generate, content_video_extend | ✅ 전체 적용 완료 |
| `insights.py` | insights_upload, insights_ingest_naver, insights_ingest_youtube, insights_search, insights_daily_report, insights_metrics, insights_teams, insights_failures | ✅ 전체 적용 완료 |
| `products.py` | products_list, products_detail | ✅ 전체 적용 완료 |

---

## 4. 로그 검색

- **실행 중인 기능만 보기:** `grep '\[FEATURE\]'` 또는 Cloud Logging 필터 `textPayload=~"\[FEATURE\]"`.
- **특정 기능만:** `grep '\[FEATURE\].*auth_login'`, `grep '\[FEATURE\].*pipeline_run'`.
- **extra 필드:** `log_feature_*` 는 `extra={"feature": "...", "event": "start|end|fail"}` 를 넣어 두었으므로, JSON 포맷터를 쓰면 `jsonPayload.feature` 로 필터링 가능.

---

## 5. 적용 원칙

- **진입점에서만:** HTTP 핸들러/백그라운드 태스크 **시작 시** `log_feature_start`, **종료 시** `log_feature_end` (또는 실패 시 `log_feature_fail`) 호출.
- **중첩 기능:** 상위에서 `pipeline_run`, 하위 단계는 기존 `[STEP]`/`log_stage_*` 유지.
- **민감 정보:** `detail`/`extra_detail`/`error` 에 비밀번호·토큰·개인정보 넣지 않기.

---

**문서 위치:** `docs/2026-02-08/cursor/logging-strategy.md`
