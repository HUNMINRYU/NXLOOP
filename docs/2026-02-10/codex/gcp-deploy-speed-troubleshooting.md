# GCP 배포 속도 최적화 + 트러블슈팅 로그 (Nexloop)

- 작성일: 2026-02-10
- 작성자: Codex (로컬 워크스페이스 `/home/amoo/projects/nexloop`)
- 대상: Cloud Run + Cloud Build 기반의 “수정 → 배포 → 확인” 루프 단축
- 주의: 이 문서에는 **시크릿 값(Stripe webhook secret 등)을 절대 기록하지 않는다.** 예시는 `whsec_***` 형태로 마스킹한다.

## 0) 현재 운영/배포 컨텍스트 요약

- Backend (Cloud Run): `nexloop-backend`
- Frontend (Cloud Run): `nexloop-frontend`
- Region: `asia-northeast3`
- Cloud SQL 연결: `--add-cloudsql-instances=$PROJECT_ID:asia-northeast3:nexloop-db`
- 배포 파이프라인: Cloud Build (`cloudbuild.backend.yaml`, `cloudbuild.frontend.yaml`)

### (참고) Cloud Scheduler / Cloud Functions 사용 여부

- Cloud Scheduler: 사용 중
  - Job: `pipeline-4a1473aa51e9` (ENABLED)
  - Target(HTTP): `/api/v1/webhooks/scheduler`
  - OIDC SA: `blueguard-admin@jnu-rise-edu-149.iam.gserviceaccount.com`
- Cloud Functions: 일부 사용 중
  - `function-thumbnail`: ACTIVE (Storage finalize trigger, runtime `python310`)
  - `thumbnail-generator`: FAILED (v2 기준으로 실패 표시)

## 1) 타임라인 (시간/날짜 포함)

> 시간 기준은 Cloud Build가 출력하는 UTC 타임스탬프를 우선으로 하고,
> 한국 시간(KST=UTC+9)을 함께 표기한다.

### 2026-02-10 (UTC 03:20, KST 12:20) — 백엔드/프론트 배포 수행

- Backend Cloud Build
  - Build ID: `08a6ff11-2c6c-4a6b-944d-83845e559689`
  - Create Time(UTC): `2026-02-10T03:20:10Z` (KST 12:20:10)
  - Status: SUCCESS
  - Deployed revision: `nexloop-backend-00054-47x`
  - Service URL: `https://nexloop-backend-225483801144.asia-northeast3.run.app`
  - 경고: `Setting IAM policy failed` (런타임 실패 아님)

- Frontend Cloud Build
  - Build ID: `80229844-7583-4b29-91af-ec92b9f8271e`
  - Create Time(UTC): `2026-02-10T03:20:10Z` (KST 12:20:10)
  - Status: SUCCESS
  - Deployed revision: `nexloop-frontend-00021-dnh`
  - Service URL: `https://nexloop-frontend-225483801144.asia-northeast3.run.app`
  - 경고: `Setting IAM policy failed` (런타임 실패 아님)

### 2026-02-10 (배포 직후) — IAM 경고 해결

- 증상
  - Cloud Build 배포 단계에서 아래 경고가 반복적으로 출력됨:
    - `Setting IAM policy failed, try "gcloud beta run services add-iam-policy-binding ... --member=allUsers --role=roles/run.invoker ..."`
- 의미
  - 배포 자체는 성공해도, `--allow-unauthenticated`에 따른 invoker 바인딩이 CI 계정 권한 부족으로 실패할 수 있음.
- 조치(수동 보정)
  - `gcloud run services add-iam-policy-binding ... --member=allUsers --role=roles/run.invoker` 실행으로 해결.
  - 백엔드/프론트 모두 적용.

## 2) “배포가 느린 이유”를 분해해서 보는 관점 (가장 빠른 문제 해결 루트)

배포가 느리다고 느껴질 때는 보통 아래 4개 중 하나가 병목이다.

1. 소스 업로드(archive/upload) 시간이 길다
2. Docker build 시간이 길다 (특히 의존성 설치 단계)
3. 이미지 push 시간이 길다
4. Cloud Run revision 생성/헬스체크(Startup probe) 대기 시간이 길다

각 병목별로 대응이 다르다.

## 3) Nexloop에서 실제로 겪었던 대표 트러블 + 재발 방지

### 3.0 Cloud Build PR 체크에서 `cloudbuild.pr.yaml not found`

- 발생(실제): 2026-02-10 (PST 기준) PR Checks에서 즉시 실패
  - 메시지: `File cloudbuild.pr.yaml not found`
- 원인
  - 트리거는 repo 루트(`/cloudbuild.pr.yaml`)에서 config를 찾는데,
    해당 파일이 **로컬에만 있고 PR 브랜치 커밋에 포함되지 않음**(untracked/미커밋).
- 해결
  - `cloudbuild.pr.yaml`을 파일 단위로 add/commit/push:
    - `git add cloudbuild.pr.yaml`
    - `git commit -m "chore: add cloudbuild.pr for pr validation"`
    - `git push`
- 검증 결과(성공)
  - Trigger: `nexloop-pr-validate`
  - Build: `91af4ad8-cf8f-4dd8-a87a-ef81c397ea0b`
  - Status: `SUCCESS`
  - 캐시 힌트: 빌드 로그에 `CACHED`가 표시됨(레이어 캐시가 실제로 동작)
- 후속 조치(재발 방지)
  - `cloudbuild.pr.yaml`을 `main`에도 포함시키기 위해 브랜치 생성/푸시:
    - branch: `ci/add-cloudbuild-pr-yaml`
    - commit: `6e71195`

### 3.1 Cloud Run “reserved env name PORT”로 프론트 배포 실패

- 증상
  - `ERROR: (gcloud.run.deploy) spec.template.spec.containers[0].env: The following reserved env names were provided: PORT. These values are automatically set by the system.`
- 원인
  - Cloud Run은 `PORT` 환경변수를 시스템이 주입한다.
  - 배포 시 `--set-env-vars=PORT=...` 같은 형태로 사용자가 덮어쓰면 실패한다.
- 해결
  - Cloud Run 서비스 env에는 `PORT`를 설정하지 않는다.
  - 컨테이너는 `process.env.PORT`를 사용하도록 하고(이미 Dockerfile에서 `${PORT:-8080}`), Cloud Run이 주입하는 값을 그대로 따른다.
- 재발 방지 체크리스트
  - `cloudbuild.frontend.yaml` / `cloudbuild.backend.yaml` / `gcloud run deploy`에 `PORT`가 들어가 있지 않은지 확인.

### 3.2 Cloud Run “startup probe failed”로 백엔드 배포 실패

- 증상
  - `The user-provided container failed the configured startup probe checks`
- 흔한 원인 후보
  - 앱이 `0.0.0.0:$PORT`를 리슨하지 않음
  - 부팅 시 마이그레이션/외부 네트워크 호출/시크릿 누락 등으로 부팅이 지연/실패
  - Cloud SQL 연결/권한 문제로 앱 부팅이 블로킹
- Nexloop 쪽 대응(배포 설정 상)
  - `--startup-probe`가 `/health`로 체크하도록 구성
  - 과거 설정에서 `AUTO_MIGRATE_ON_STARTUP`가 남아 부팅 시 DB 작업을 수행할 수 있어 제거(`--remove-env-vars=AUTO_MIGRATE_ON_STARTUP`)

### 3.3 파이프라인 상태 `/api/v1/pipeline/status/{task_id}`가 200/404 섞이는 문제

- 증상
  - 동일 task_id인데 어떤 요청은 200, 어떤 요청은 404
  - 프론트 폴링 UX가 “안 도는 것처럼” 보임
- 근본 원인
  - `PIPELINE_STATUS/PIPELINE_RESULTS`가 in-memory dict라서 Cloud Run 다중 인스턴스에서 다른 인스턴스로 라우팅되면 상태가 없음.
- 해결 방향(권장)
  - 공유 저장소(DB)에 status/result를 영속화하고, API에서 DB fallback 조회.
- 응급 처치(비권장, 임시)
  - `--max-instances=1`로 내려서 라우팅 분산을 막음 (성능/비용/확장성 tradeoff 큼)

### 3.4 운영 DB 마이그레이션이 적용되지 않아 테이블이 없던 문제 (예: pipeline_tasks)

- 증상(운영 로그)
  - `UndefinedTableError: relation \"pipeline_tasks\" does not exist` 류의 오류/경고
- 배경
  - `alembic.ini` 기본 `sqlalchemy.url`은 sqlite로 되어 있어, 그대로 `alembic upgrade head`를 실행하면 운영 DB에 반영되지 않음.
  - 과거에는 `AUTO_MIGRATE_ON_STARTUP=1`로 Cloud Run 웹 프로세스 시작 시 마이그레이션을 실행했지만,
    - 콜드스타트 지연
    - 동시 실행 경쟁(race)
    - 실패 시 startup probe 실패
    리스크가 커서, 운영 배포 파이프라인에서는 제거하는 것이 안전함.
- 권장 해결(재발 방지)
  - Cloud Run Job로 `alembic upgrade head`를 실행한다.
  - Job은 `--add-cloudsql-instances`를 통해 Cloud SQL unix socket(`/cloudsql`) 환경을 그대로 재현할 수 있다.
- 코드/설정(예시)
  - `src/run_migrations.py` : `DATABASE_URL`을 사용해 Alembic `upgrade head` 수행
  - `cloudbuild.backend.yaml` : `nexloop-backend-migrate` Job deploy + execute 후 서비스 배포

## 4) 배포 시간을 “확실하게” 줄이는 방법 (우선순위 순)

### 4.1 (최우선) 배포 횟수 자체를 줄인다: 로컬/프리플라이트 검증

목표: “배포하고 나서야 깨짐을 아는” 상황을 줄이면, 체감 속도는 즉시 개선된다.

- Backend
  - 최소: `python -m py_compile ...` / `mypy` / 핵심 단위 테스트
  - Docker로 Cloud Run과 동일하게 띄워서 `/health` 확인
- Frontend
  - 최소: `npm run build` (이미 Cloud Build 내에서도 수행됨)
  - 로컬에서 `next start`로 production 모드 확인

### 4.2 업로드 시간 단축: `.gcloudignore` 정비

Cloud Build는 기본적으로 로컬 폴더를 tar로 올린다. 불필요한 파일이 많을수록 업로드가 느리다.

- 권장 제외 항목 예시
  - `**/node_modules`
  - `.git`
  - `.next`, `dist`, `build`
  - `**/__pycache__`, `**/*.pyc`
  - `outputs/` 등 대용량 산출물

#### Nexloop 적용(2026-02-10)
- `.gcloudignore`를 프로젝트 루트에 추가하여 Cloud Build 소스 업로드 용량을 줄였다.
- 효과: `gcloud builds submit` 단계의 tar 생성/업로드 시간이 줄어든다.

### 4.3 Docker build 시간 단축: 레이어 캐시 극대화

핵심 원칙:
- “자주 바뀌는 파일(CODE)”은 Dockerfile의 아래로,
- “덜 바뀌는 파일(의존성 목록)”은 위로.

체크:
- Backend Dockerfile
  - `requirements`/`pyproject`/`uv.lock` 같은 파일을 먼저 COPY → 설치
  - 그 다음 소스 COPY
- Frontend Dockerfile
  - `package*.json` 먼저 COPY → `npm ci/install`
  - 그 다음 소스 COPY → `next build`

#### Nexloop 적용(2026-02-10)
- `Dockerfile.backend` / `Dockerfile.frontend`에 BuildKit 캐시를 적용했다.
  - `# syntax=docker/dockerfile:1.7`
  - `RUN --mount=type=cache,target=/root/.cache/pip ...`
  - `RUN --mount=type=cache,target=/root/.npm ...`
- `Dockerfile.frontend`는 `npm ci`로 전환 + `npm prune --omit=dev`로 런타임 이미지/푸시를 줄였다.

### 4.4 Cloud Build 자체 속도: 머신 타입 상향

빌드가 CPU-bound(특히 Next build, pip/npm install)라면 체감이 크게 난다.

- Cloud Build `options.machineType`을 상향:
  - 예: `E2_HIGHCPU_8`
- 비용은 증가하지만 “개발 리듬”이 목적이면 충분히 투자 가치가 있다.

#### Nexloop 적용(2026-02-10)
- `cloudbuild.backend.yaml`, `cloudbuild.frontend.yaml`에 `options.machineType: E2_HIGHCPU_8`를 추가했다.

### 4.5 Cloud Run 기동 시간: startup CPU boost / min instances

- `--cpu-boost`: cold start 구간 단축
- `--min-instances=1`: 완전 cold start 방지(비용 증가)

## 5) Nexloop 기준 “가장 빠르게 체감되는” 권장 조합

1. `.gcloudignore`를 제대로 잡아 업로드 시간을 깎는다.
2. Dockerfile 레이어를 의존성 캐시 친화적으로 정리한다.
3. Cloud Build 머신 타입을 올린다(개발 기간 동안만).
4. Cloud Run은 `--cpu-boost` + `--min-instances=1`로 cold start 체감 제거.

## 6) 체크리스트 (배포 직전/직후)

### 배포 직전

- [ ] 프론트: `PORT` env를 Cloud Run에 설정하지 않았는가?
- [ ] 백엔드: `/health`가 빠르게 200을 반환하는가?
- [ ] 시크릿: Secret Manager에 “선택 시크릿”도 최소 더미라도 존재하는가?
- [ ] CORS: `CORS_ORIGINS`가 실제 프론트 Origin과 일치하는가?

### 배포 직후

- [ ] Backend: `GET /health` 200
- [ ] Frontend: `/` 200
- [ ] Stripe webhook: 이벤트 수신/로그가 찍히는가(시크릿은 마스킹 관리)
- [ ] Pipeline: status/result가 다중 인스턴스에서도 404 튐이 사라졌는가?

---

## 8) 단계별 사용 가이드 (초보자용)

> 목표: “수정 → 배포 → 확인” 루프를 빠르게 만든다.  
> 전제: Cloud Build + Cloud Run 배포를 `cloudbuild.*.yaml`로 수행한다.

### 8.1 준비(한 번만)

1. `.gcloudignore`가 존재하는지 확인한다.
2. `cloudbuild.backend.yaml` / `cloudbuild.frontend.yaml`가 최신인지 확인한다.
   - `options.machineType: E2_HIGHCPU_8`
   - `docker pull ...:latest || true`
   - `--cache-from=...:latest`
   - `DOCKER_BUILDKIT=1`
3. Dockerfile 상단에 syntax 라인이 있는지 확인한다.
   - `Dockerfile.backend` / `Dockerfile.frontend` 첫 줄: `# syntax=docker/dockerfile:1.7`

### 8.2 배포(매번)

1. (권장) 배포 전에 로컬에서 빠른 검증을 한다.
   - Backend: `python -m compileall -q src`
   - Frontend: `cd frontend && npm run typecheck`
2. Cloud Build를 실행한다.
   - Backend:
     - `gcloud beta builds submit --config=cloudbuild.backend.yaml .`
   - Frontend:
     - `gcloud beta builds submit --config=cloudbuild.frontend.yaml .`
3. 결과가 느리면 병목을 분해해서 본다.
   - 업로드가 느리면: `.gcloudignore`에 누락된 대용량 디렉터리가 있는지 확인
   - 빌드가 느리면: `--cache-from`가 제대로 먹는지(이전 이미지가 존재하는지) 확인
   - push가 느리면: 이미지가 과도하게 커졌는지 확인(특히 frontend는 `npm prune --omit=dev` 유지)
4. 배포 후 바로 확인한다.
   - Backend: `GET /health` 200
   - Frontend: `/` 200

### 8.3 “캐시가 안 먹는” 흔한 원인

- 이전 이미지가 없어서 `--cache-from`가 무의미한 경우(첫 빌드)
- Dockerfile에서 `COPY . .`가 너무 일찍 실행되어 레이어 캐시가 깨지는 경우
- 소스 업로드에 `outputs/`, `docs/` 같은 대용량이 포함되어 매번 오래 걸리는 경우

### 8.4 비용/안전 주의

- `E2_HIGHCPU_8`는 빌드 비용이 증가한다. 개발 기간에만 유지하고, 안정화 후 낮출 수 있다.
- BuildKit 캐시는 “첫 빌드 이후”부터 효과가 커진다.

## 7) 부록: Cloud Build 설정 파일 위치

- Backend: `cloudbuild.backend.yaml`
- Frontend: `cloudbuild.frontend.yaml`
- Backend Dockerfile: `Dockerfile.backend`
- Frontend Dockerfile: `Dockerfile.frontend`
