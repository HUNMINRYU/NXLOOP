# CI/CD 자동배포 실행 로그 (2026-02-11)

## 목적
- 로컬 `gcloud` 권한/네트워크 의존도를 줄이고, GitHub push 기반 자동배포 경로를 사용한다.
- 시연 대본 기준 정합성 수정(엔드포인트/로그 키/문서 보강)을 `main`에 반영해 자동배포를 트리거한다.

## 기준 문서
- `docs/2026-02-10/codex/ci-cd-cloudbuild-triggers.md`
- `docs/2026-02-10/codex/ci-cd-github-actions-cloudbuild.md`
- `docs/2026-02-10/codex/main-deploy-trigger-test-guide.md`

## 핵심 정책 요약
1. PR -> `main`: 빌드 검증만 (`cloudbuild.pr.yaml`)
2. `main` push/merge: 자동배포
   - backend: `cloudbuild.backend.yaml`
   - frontend: `cloudbuild.frontend.yaml`

## 이번 반영 항목
1. `status-stream`의 `[FEATURE]` 로그 정합성 보강
   - feature: `pipeline_status_stream`
   - 시작/종료/실패 로그를 명시적으로 남김
2. 선택 썸네일 기반 비디오 생성 feature 키 정합성 수정
   - `pipeline_generate_video_from_selected_thumbnail`
3. 시연 커버리지 문서 보강
   - Cloud Logging 실전 필터
   - Happy Path 로그 순서
   - 시연 문구(오해 방지) 보강
4. 테스트 추가(TDD)
   - `tests/test_api/test_pipeline_status_stream.py`

## 검증 결과(로컬)
- Backend: `pytest` 통과 (`176 passed, 1 skipped`)
- Frontend: `npm run lint`, `npm run typecheck` 통과

## 배포/운영 메모
- 로컬 직접 배포(`gcloud builds submit`)는 서비스 계정 권한 부족으로 실패 가능.
- 운영 반영은 `main` push 기반 CI/CD를 우선 사용한다.
- 배포 후 검증 포인트:
  - Cloud Build History에서 `main` 배포 파이프라인 실행 확인
  - Cloud Run 최신 revision 변경 확인
  - Cloud Logging에서 `[FEATURE] pipeline_status_stream` 로그 확인

## 변경 파일
- `src/api/v1/endpoints/pipeline.py`
- `tests/test_api/test_pipeline_status_stream.py`
- `docs/2026-02-10/codex/demo-script-coverage.md`
- `docs/2026-02-11/codex/ci-cd-auto-deploy-log-2026-02-11.md`
