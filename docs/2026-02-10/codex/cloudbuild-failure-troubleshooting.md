# Cloud Build 트리거 배포 실패 트러블슈팅 (백엔드/프론트 공통) — Nexloop

- 작성일: 2026-02-10
- 목적: `main` 머지/푸시 이후 Cloud Build 트리거가 `FAILURE`일 때, **최단 시간**으로 원인(빌드/푸시/배포)을 확정하고 조치한다.
- 프로젝트 ID: `jnu-rise-edu-149`
- Cloud Build 리전: `us-central1`
- Cloud Run 리전: `asia-northeast3`

> 중요: 커맨드를 줄바꿈으로 쪼개면 `--region=...: command not found` 같은 에러가 발생한다.  
> 아래 커맨드는 가능하면 **한 줄 그대로** 복붙한다.

---

## 0) 현재 증상 체크리스트

아래 중 하나라도 해당하면 이 문서를 따른다.

- `gcloud builds list`에서 `STATUS=FAILURE`가 보인다.
- Cloud Run 리비전이 최신으로 안 올라간다(`latestReadyRevisionName`이 그대로).
- PR/merge는 성공했는데 배포가 따라오지 않는다.

---

## 1) 실패 빌드 ID 확보(필수)

### 1.1 트리거별 최근 빌드 확인(권장)

백엔드(main deploy 트리거):

```bash
gcloud builds list --project=jnu-rise-edu-149 --region=us-central1 --limit=10 --filter="buildTriggerId=9b383501-1a90-4a70-a66a-f6582fbaebe2" --format="table(id,status,createTime,logUrl)"
```

프론트(main deploy 트리거):

```bash
gcloud builds list --project=jnu-rise-edu-149 --region=us-central1 --limit=10 --filter="buildTriggerId=c88379f5-abdb-496d-91c0-1a946024b62a" --format="table(id,status,createTime,logUrl)"
```

> `createTime`이 “머지/푸시 시각 이후”인 `FAILURE` 빌드 ID를 각각 1개씩 확보한다.

### 1.2 빌드 ID로 존재 확인(옵션)

```bash
gcloud builds list --project=jnu-rise-edu-149 --region=us-central1 --filter="id=BUILD_ID" --format="table(id,status,createTime,logUrl)"
```

---

## 2) 원인 확정(가장 빠른 2가지 방법)

### 방법 A) 콘솔 로그에서 “마지막 ERROR 20줄” 복사(최단)

1. 위 `logUrl`을 브라우저에서 연다
2. 실패한 Step(예: `Step #2`)를 찾는다
3. **마지막 ERROR 20줄**(특히 `Step #0/#1/#2:` 근처)을 복사

이 20줄만 있으면 대부분 즉시 조치가 가능하다.

### 방법 B) CLI로 로그 스트림 보기(Cloud Logging)

Cloud Build가 `logging: CLOUD_LOGGING_ONLY`면 다음으로 봐야 한다.

```bash
gcloud beta builds log --project=jnu-rise-edu-149 --region=us-central1 --stream BUILD_ID
```

---

## 3) 실패 유형별 “즉시 조치” 가이드

아래는 로그에서 자주 나오는 유형을 기준으로 “다음 액션”만 정리한다.

### 3.0 `the --mount option requires BuildKit` (Dockerfile에 `RUN --mount=...` 사용)

증상(예시):
- `the --mount option requires BuildKit`

원인:
- Dockerfile에서 `RUN --mount=type=cache,...` 같은 BuildKit 전용 문법을 사용했는데,
  Cloud Build 단계의 `docker build`가 BuildKit 없이 실행됨.

즉시 조치(권장):
- 해당 `docker build` step에 환경변수 추가:
  - `env: ['DOCKER_BUILDKIT=1']`

대상 파일(예시):
- `cloudbuild.backend.yaml` (백엔드 docker build step)
- `cloudbuild.frontend.yaml` (프론트 docker build step)

검증:
- 동일 트리거 재실행 후 `FAILURE` → `SUCCESS` 확인.

### 3.1 `gcloud run deploy`에서 reserved env (`PORT`) 에러

증상(예시):
- `spec.template.spec.containers[0].env: The following reserved env names were provided: PORT`

원인:
- Cloud Run은 `PORT`를 시스템이 자동 주입하므로 사용자가 설정하면 실패한다.

조치:
- Cloud Run 배포 시 `--set-env-vars=PORT=...` 같은 설정을 제거한다.
- Dockerfile 내부의 `ENV PORT=...`는 보통 허용되지만, **Cloud Run 서비스 env로 넣는 것은 금지**.

검증:
- 동일 커밋/브랜치에서 재배포 트리거가 `SUCCESS`가 되는지 확인.

### 3.2 `Setting IAM policy failed` / `run.services.setIamPolicy` 권한 부족

증상(예시):
- `Setting IAM policy failed`
- `try "gcloud beta run services add-iam-policy-binding ... --role=roles/run.invoker ..."`

원인:
- 배포 단계에서 `--allow-unauthenticated`가 IAM을 변경하는데, Cloud Build 서비스 계정에 권한이 부족.

조치:
- Cloud Build 실행 서비스 계정에 `roles/run.admin`(또는 최소 `run.services.setIamPolicy` 포함 역할)을 부여.
- 이미 서비스는 배포됐는데 경고만 뜨는 케이스가 있으므로, 로그를 보고 “실패인지 경고인지”를 구분.

검증:
- 동일 트리거 재실행 후 `FAILURE` → `SUCCESS` 확인.

### 3.3 `docker build` 실패

증상:
- `npm install`/`pip install`/`next build` 단계에서 실패

조치:
- 실패 Step 로그에서 “첫 번째 에러 5줄”을 확인
- 로컬에서 동일 Dockerfile로 재현:
  - `docker build -f Dockerfile.backend .`
  - `docker build -f Dockerfile.frontend .`

### 3.4 `docker push` 실패

증상:
- `denied: Permission ...`
- `unauthorized: authentication required`

조치:
- Cloud Build 서비스 계정이 Container Registry/Artifact Registry에 push 권한을 갖는지 확인
- 레지스트리 경로(`gcr.io/...` vs `*.pkg.dev/...`) 혼용 여부 확인

---

## 4) 배포 반영(Cloud Run) 확인

배포가 성공하면 Cloud Run의 최신 리비전이 바뀌어야 한다.

```bash
gcloud run services describe nexloop-backend --project=jnu-rise-edu-149 --region=asia-northeast3 --format="value(status.latestReadyRevisionName,status.url)"
gcloud run services describe nexloop-frontend --project=jnu-rise-edu-149 --region=asia-northeast3 --format="value(status.latestReadyRevisionName,status.url)"
```

`latestReadyRevisionName`이 이전보다 증가하지 않으면 배포가 실제로 반영되지 않은 것이다.

---

## 5) 재실행(재트리거) 방법

이 프로젝트는 “main push 시 자동 배포 트리거” 구조다.

1. `main`에 수정 커밋 push
2. Cloud Build History에서 트리거 실행 확인

> 운영에서 즉시 재실행이 필요하면, 가장 안전한 방법은 “노옵 커밋 1개”로 main을 다시 푸시하는 것이다.  
> 자세한 절차는 `docs/2026-02-10/codex/main-deploy-trigger-test-guide.md` 참고.
