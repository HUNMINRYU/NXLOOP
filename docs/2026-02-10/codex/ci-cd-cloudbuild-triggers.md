# CI/CD (Cloud Build Triggers) 설정 가이드 — Nexloop

- 작성일: 2026-02-10
- 목적: PR에서는 “빌드 검증만”, `main` merge 시 “자동 배포”로 개발 루프를 단축한다.
- 대상 레포: GitHub `HUNMINRYU/NXLOOP`
- 대상 프로젝트: `jnu-rise-edu-149`
- 배포 대상: Cloud Run (`nexloop-backend`, `nexloop-frontend`)

> 이 문서는 **초보자도 그대로 따라하면** CI/CD가 동작하도록 단계별로 작성했다.
> 시크릿 값은 문서/로그/커밋에 절대 남기지 않는다.

---

## 0) 우리가 만들 CI/CD 정책(확정)

1. PR → `main` 대상:
   - Cloud Build가 `cloudbuild.pr.yaml`로 **백엔드/프론트 Docker build만** 실행
   - push/deploy 없음
2. `main` 브랜치 merge/push:
   - Backend 자동 배포: `cloudbuild.backend.yaml`
   - Frontend 자동 배포: `cloudbuild.frontend.yaml`

### 중요: `cloudbuild.pr.yaml`은 `main`에도 있어야 한다

- 트리거는 “PR의 커밋”에서 config를 읽는다.
- 그래서 `cloudbuild.pr.yaml`이 `main`에 없으면:
  - 새 브랜치를 `main`에서 파고 PR을 만들었을 때,
  - 브랜치에 `cloudbuild.pr.yaml`을 포함시키지 않으면
  - `File cloudbuild.pr.yaml not found`로 PR 체크가 즉시 실패할 수 있다.
- 결론: `cloudbuild.pr.yaml` 파일은 `main`에 커밋해 두는 것을 권장한다.

---

## 1) 준비물 체크(한 번만)

1. 로컬에서 `gcloud` 로그인 되어 있어야 한다.
   - `gcloud auth list`
2. 프로젝트가 맞아야 한다.
   - `gcloud config set project jnu-rise-edu-149`
3. Cloud Build API가 활성화되어 있어야 한다.
   - `gcloud services enable cloudbuild.googleapis.com`

---

## 2) GitHub 연결(필수)

Cloud Build가 GitHub의 push/PR 이벤트를 받으려면 **GitHub 앱 연결**이 필요하다.

### 2.1 (권장) Cloud Console에서 연결

1. GCP Console → Cloud Build → Triggers
2. “Connect Repository” 선택
3. GitHub 선택 후 OAuth/앱 설치 진행
4. 레포 `HUNMINRYU/NXLOOP` 선택

연결이 끝나면 Triggers 화면에서 repo가 선택 가능해진다.

> 연결이 되어 있지 않으면 아래 `gcloud builds triggers create github ...` 명령이 실패한다.

---

## 3) 트리거 생성(한 번만)

> 권장: **Cloud Console(UI)** 로 생성한다. (2세대 GitHub 연결/Repository를 쓰는 경우 UI가 제일 덜 헷갈림)
> 참고: gcloud로도 만들 수 있지만, 연결 방식/리전/필드 조합에 따라 `INVALID_ARGUMENT`로 막히는 케이스가 있었다.

### 3.0 (권장) Cloud Console(UI)에서 트리거 만들기

공통:
- Cloud Build → Triggers → `Create trigger`
- 리전: `us-central1`
- 소스:
  - 저장소 서비스: `Cloud Build 저장소(2세대)`
  - 저장소: `HUNMINRYU-NXLOOP` 선택
- 구성:
  - 유형: `Cloud Build 구성 파일(YAML 또는 JSON)`
  - 위치: `저장소`
  - Cloud Build 구성 파일 위치:
    - PR 검증: `/cloudbuild.pr.yaml`
    - main backend 배포: `/cloudbuild.backend.yaml`
    - main frontend 배포: `/cloudbuild.frontend.yaml`
- 서비스 계정:
  - 조직 정책상 “사용자 관리형 서비스 계정” 선택이 필수일 수 있다.
  - (권장) 전용 SA를 만들고 필요한 최소 권한만 부여한다.

각 트리거별 이벤트 설정:

1. PR 검증 트리거 `nexloop-pr-validate`
   - 이벤트: `pull 요청`
   - base 브랜치 정규식: `^main$`

2. main 백엔드 배포 트리거 `nexloop-backend-deploy-main`
   - 이벤트: `브랜치로 푸시`
   - 브랜치 정규식: `^main$`

3. main 프론트 배포 트리거 `nexloop-frontend-deploy-main`
   - 이벤트: `브랜치로 푸시`
   - 브랜치 정규식: `^main$`

### 3.1 PR 검증 트리거(빌드만)

```bash
gcloud builds triggers create github \
  --name="nexloop-pr-validate" \
  --repo-owner="HUNMINRYU" \
  --repo-name="NXLOOP" \
  --pull-request-pattern="^main$" \
  --build-config="cloudbuild.pr.yaml"
```

### 3.2 main 백엔드 자동 배포 트리거

```bash
gcloud builds triggers create github \
  --name="nexloop-backend-deploy-main" \
  --repo-owner="HUNMINRYU" \
  --repo-name="NXLOOP" \
  --branch-pattern="^main$" \
  --build-config="cloudbuild.backend.yaml"
```

### 3.3 main 프론트 자동 배포 트리거

```bash
gcloud builds triggers create github \
  --name="nexloop-frontend-deploy-main" \
  --repo-owner="HUNMINRYU" \
  --repo-name="NXLOOP" \
  --branch-pattern="^main$" \
  --build-config="cloudbuild.frontend.yaml"
```

---

## 4) 동작 확인 방법

### 4.1 PR 검증 확인

1. 새 브랜치 생성 → commit → push
2. GitHub에서 `main` 대상으로 PR 생성
3. Cloud Build → History에서 `nexloop-pr-validate`가 뜨는지 확인
4. 결과가 SUCCESS면 “빌드가 깨지지 않는다”는 보장이 생긴다.

#### (실전) PR 체크가 `cloudbuild.pr.yaml not found`로 실패하면

- 의미: 트리거가 repo에서 `/cloudbuild.pr.yaml`을 못 찾는 상태(대부분 “파일이 PR 브랜치 커밋에 없음”)
- 해결: 파일 1개만 add/commit/push

```bash
git add cloudbuild.pr.yaml
git commit -m "chore: add cloudbuild.pr for pr validation"
git push
```

### 4.2 main 자동 배포 확인

1. PR을 merge해서 `main`에 반영
2. Cloud Build → History에서
   - `nexloop-backend-deploy-main`
   - `nexloop-frontend-deploy-main`
   두 빌드가 실행되는지 확인

---

## 5) 자주 터지는 문제(빠른 진단)

### 5.1 트리거 생성이 실패한다

- 원인: GitHub repo 연결이 안 되어 있음
- 해결: Cloud Console에서 repo 연결을 먼저 완료하고 다시 실행

### 5.2 PR 검증이 너무 느리다

- `cloudbuild.pr.yaml`은 “빌드만” 한다. 그래도 느리면:
  - `.gcloudignore` 누락 여부(업로드 병목)
  - Docker 캐시가 먹는지(`--cache-from` 전제: 이전 latest 이미지가 존재)
  - `options.machineType` 조정(E2_HIGHCPU_8 → 더 올리면 비용 증가)

### 5.3 main 배포가 연속으로 2번씩 돈다

- 보통 트리거가 중복 생성된 케이스다.
- `gcloud builds triggers list`로 이름/조건 확인 후 불필요 트리거 삭제:
  - `gcloud builds triggers delete TRIGGER_ID`

---

## 6) 운영 권한(필수)

CI가 Cloud Run에 배포하려면 Cloud Build 서비스 계정에 권한이 필요하다.
이미 논의한대로 최소한 아래가 필요하다:
- `roles/run.admin` (서비스 배포)
- `roles/iam.serviceAccountUser` (서비스 계정 사용)
- `roles/run.invoker` 바인딩을 자동으로 하려면 관련 권한

> 권한이 없으면 build 로그에 “Setting IAM policy failed” 경고가 반복된다.
