# Git 전략·로깅 전략 적용 진행 (2026-02-08 ~ 2026-02-09)

> **참조:** `git-strategy.md`, `logging-strategy.md`

---

## 1. Git 전략 적용

- **브랜치:** `develop` 기준 feature 브랜치에서 작업 후 `develop`로 통합.
- **워크플로:** 커밋 → `develop` fast-forward/merge → `git push origin develop`.

---

## 2. 로깅 전략 적용 내용

### 2.1 추가된 [FEATURE] 로깅

| feature | 위치 | 설명 |
|---------|------|------|
| `leads_capture` | POST /leads | 리드 캡처 (이메일 수집). 실패 시 invalid email / 예외 로깅 |
| `refresh_signed_url` | POST /refresh-url | GCS 서명 URL 재발급. 실패 시 fail 로깅 |
| `search_discovery` | GET /search/discovery | Discovery Engine 검색 (PRO). 완료 시 results 개수 extra_detail |
| `studio_draft` | POST /studio/draft | 스튜디오 초안 프롬프트 생성 (PRO). detail에 product_name |
| `studio_refine` | POST /studio/refine | 스튜디오 프롬프트 고도화 (PRO) |
| `pipeline_select_output` | POST /pipeline/result/{task_id}/select-output | Create 산출물(썸네일/비디오) 채택 |
| `pipeline_generate_video_selected_thumbnail` | POST /pipeline/result/{task_id}/generate-video-from-selected-thumbnail | 선택 썸네일 기반 I2V 비디오 재생성 + 자동 채택 |

### 2.2 수정 파일

- `src/api/v1/endpoints/misc.py`: leads, refresh-url, search/discovery 핸들러에 `log_feature_start` / `log_feature_end` / `log_feature_fail` 추가.
- `src/api/v1/endpoints/studio.py`: draft, refine 핸들러에 동일 적용. `utils.logger` import 추가.
- `src/api/v1/endpoints/pipeline.py`: select-output, generate-video-from-selected-thumbnail 핸들러에 동일 패턴 적용.

### 2.3 문서 갱신

- **`logging-strategy.md`**
  - 기능 이름 목록에 `leads_capture`, `refresh_signed_url`, `search_discovery`, `studio_draft`, `studio_refine` 추가.
  - **§3 적용 현황** 신설: 라우터별 적용 feature 및 미적용(추후 확장) 정리.
  - 섹션 번호 조정: 3 적용 현황, 4 로그 검색, 5 적용 원칙.

---

## 3. 다음 단계 (권장)

1. `feature/logging-and-docs` 에서 커밋 후 `develop` 병합.
2. 필요 시 `pipeline.py`, `content.py`, `insights.py` 등에 동일 패턴으로 [FEATURE] 로깅 확장 (logging-strategy §3 적용 현황 참고).

---

## 4. 2026-02-09 업데이트

- `pipeline.py`에 Create 산출물 채택/선택 썸네일 기반 I2V 생성 플로우가 추가되면서, 해당 진입점에 [FEATURE] 로깅을 최소 적용.
- 문서 `logging-strategy.md`의 “적용 현황” 날짜를 2026-02-09로 갱신하고 pipeline 적용 상태를 “부분 적용”으로 변경.

---

**문서 위치:** `docs/2026-02-08/cursor/logging-and-git-strategy-progress.md`
