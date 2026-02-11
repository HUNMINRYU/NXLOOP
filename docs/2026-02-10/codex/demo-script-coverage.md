# 시연 대본 커버리지 (프론트/백엔드/로그 매핑)

목표: “로그만 보고도 시연을 설명”할 수 있도록, 시연 대본의 단계별로
프론트 화면(경로) / 백엔드 엔드포인트 / 기대 로그(`[FEATURE]`)를 1:1로 매핑한다.

## 1) 시연 대본(요약)

1. YouTube + 네이버에서 실시간 데이터를 수집
2. 스팸/중복/의미 없는 데이터 제거(1차 관문)
3. Gemini로 감정/반응 강도/구매 의도 등 마케팅 신호 추출
4. 행동 예측 점수(CTR 등) + 유사 콘텐츠 제거 + 성과 후보만 남김(2차 관문)
5. 결과 화면: 전략/썸네일/비디오 생성
6. 관리자 화면: 실행 이력 추적, 자동 스케줄, 기준 통제

## 2) 단계별 매핑 표

| 시연 단계 | 프론트 페이지(경로) | 백엔드 엔드포인트 | 기대 로그(`[FEATURE]`) | 비고(누락/불필요) |
|---|---|---|---|---|
| 파이프라인 실행(엔드투엔드) | `/pipeline/create` | `POST /api/v1/pipeline/run` | `pipeline_run` | task_id 생성 |
| 진행률/상태 표시 | `/pipeline/create` | `GET /api/v1/pipeline/status/{task_id}` | `pipeline_status` | throttle 적용됨 |
| 실시간 상태 스트림(SSE) | `/pipeline/create` | `GET /api/v1/pipeline/status-stream/{task_id}` | `pipeline_status_stream` | SSE 정상 시 polling 중단 |
| YouTube/네이버 “외부 인사이트 강제 수집” | `/insights` | `POST /api/v1/insights/external/youtube` / `POST /api/v1/insights/external/naver` | `insights_ingest_youtube` / `insights_ingest_naver` | 수집 결과를 Insights Hub에서 확인 |
| 1차 관문: 스팸/중복 제거 | (파이프라인 내부) | (파이프라인 내부) | `xalgo_pre_filter` / `xalgo_post_filter` | 전용 UI는 없음(로그로 설명) |
| Gemini 신호 추출(하이드레이션) | (파이프라인 내부) | (파이프라인 내부) | `xalgo_hydration` | 전용 UI는 없음(로그로 설명) |
| 스코어링/다양성/최종 선택 | (파이프라인 내부) | (파이프라인 내부) | `xalgo_scoring` / `xalgo_diversity` / `xalgo_selection` | 전용 UI는 없음(로그로 설명) |
| 전략 생성(별도 요청) | `/pipeline/create` | `POST /api/v1/pipeline/analysis/strategy` | `analysis_strategy` | 캐시 히트 시 `cached` |
| 댓글 분석(기본/심화) | `/pipeline/create` | `POST /api/v1/pipeline/analysis/comments/basic` / `POST /api/v1/pipeline/analysis/comments/deep` | `analysis_comments_basic` / `analysis_comments_deep` | |
| CTR 예측 | `/pipeline/create` | `POST /api/v1/pipeline/analysis/ctr-predict` | `ctr_predict_input` / `ctr_predict_basic` / `ctr_predict_ai` | “학습 모델”이 아니라 rule+AI 조합(데모 설명 시 명확히) |
| 썸네일 스튜디오 | `/pipeline/thumbnail` | `GET /api/v1/thumbnail/styles` / `POST /api/v1/thumbnail/compare-styles` 등 | `thumbnail_generate*` | |
| 비디오 스튜디오 | `/pipeline/video` | `GET /api/v1/video/presets` / `POST /api/v1/video/generate` / `POST /api/v1/video/extend` | `video_generate*` | |
| 결과 선택(썸네일 선택 등) | `/pipeline/create` | `POST /api/v1/pipeline/result/{task_id}/select-output` | `pipeline_select_output`(내부) | |
| 선택 썸네일 기반 비디오 생성 | `/pipeline/create` | `POST /api/v1/pipeline/result/{task_id}/generate-video-from-selected-thumbnail` | `pipeline_generate_video_from_selected_thumbnail` | |
| Notion export | `/pipeline/create` | `POST /api/v1/pipeline/export/notion` | `export_notion` | |
| 실행 이력 | `/storage/prompt-log` | `GET /api/v1/pipeline/history` | `pipeline_history` | |
| 관리자: 스케줄 | `/admin/scheduler` | `/api/v1/admin/schedules` + `POST /api/v1/webhooks/scheduler` | `admin_*_schedule*` / `webhook_pipeline` | |
| 관리자: 감사 로그/프롬프트 로그/캐시 | `/admin/*` | `/api/v1/admin/*` | `admin_*` | |

## 3) “로그만 보고 설명”을 위한 로그 필터 예시

Cloud Run 로그에서 아래 조건으로 필터링하면 시연 단계가 역추적 가능하다.

- `[FEATURE]` 포함
- `pipeline_run` 이후 `task_id`로 추적

### 실전 필터(Cloud Logging Query)

```text
resource.type="cloud_run_revision"
resource.labels.service_name="nexloop-backend"
textPayload:"[FEATURE]"
```

특정 시연 실행(task_id)만 추적:

```text
resource.type="cloud_run_revision"
resource.labels.service_name="nexloop-backend"
textPayload:"[FEATURE]"
textPayload:"task_id=YOUR_TASK_ID"
```

### 기대 로그 순서(핵심 Happy Path)

1. `pipeline_run` (task_id 발급)
2. `pipeline_status` / `pipeline_status_stream` (진행률)
3. `xalgo_source` → `xalgo_pre_filter` → `xalgo_hydration` → `xalgo_post_filter`
4. `xalgo_scoring` → `xalgo_diversity` → `xalgo_selection`
5. `analysis_strategy` / `analysis_comments_*` / `ctr_predict*` (선택 호출)
6. `pipeline_select_output` → `pipeline_generate_video_from_selected_thumbnail` (선택 재생성 흐름)
7. `export_notion` (선택 시)

## 4) 시연 문구 보강 포인트(오해 방지)

- “필터링에서 40% 제거”, “19개 시그널”은 **상황별 변동값**이다.  
  고정 수치처럼 말하기보다 “보통 n% 수준, 실행마다 달라짐”으로 표현한다.
- CTR 예측은 현재 **rule 기반 + AI 보조** 결합이다.  
  “완전 학습모델 단독”으로 소개하지 않는다.
- Filter/Hydration/Scoring/Diversity는 별도 UI보다 **운영 로그 기반 증명**이 핵심이다.

## 5) 정리 (현재 시연에 “없는 것/정리 후보”)

- “필터링/하이드레이션/스코어링/다양성”은 전용 UI가 없다: 시연에서는 **로그 기반 설명**으로 충분.
- CTR 예측은 “학습된 모델”이 아니라 “rule + LLM 보조” 형태로 보임: 발표에서 **정직하게 포지셔닝** 필요.
