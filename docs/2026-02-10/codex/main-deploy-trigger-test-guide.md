# main 자동 배포 트리거 테스트 가이드 (초보자용) — Nexloop

- 작성일: 2026-02-10
- 목적: `main` 브랜치 push 이벤트로 Cloud Build 트리거가 실제로 실행되는지(backend/frontend) **안전하게 검증**한다.
- 전제:
  - 트리거(리전 `us-central1`)가 이미 존재:
    - `nexloop-backend-deploy-main` (push `^main$`, config `/cloudbuild.backend.yaml`)
    - `nexloop-frontend-deploy-main` (push `^main$`, config `/cloudbuild.frontend.yaml`)
  - 프로젝트: `jnu-rise-edu-149`

> 핵심: “트리거 테스트”는 기능 개발이 아니라 **이벤트가 제대로 연결됐는지** 확인하는 것이다.  
> 그래서 **노옵(no-op) 커밋 1개만** 만든다. 그리고 `git add .`는 금지한다.

---

## 1) 안전한 테스트 커밋 만들기(딱 1개 파일만)

> 자주 막히는 지점: “작업 중 변경사항이 많아서 `git checkout main`이 거절”되는 경우가 흔하다.  
> 이때는 강제 체크아웃/리셋을 하지 말고, **stash로 임시 보관** 후 진행한다.

### 0. (필요 시) 변경사항 stash로 임시 보관

`git checkout main`에서 아래처럼 뜨면:
- `Your local changes to the following files would be overwritten by checkout ...`

아래로 임시 보관:

```bash
git status --porcelain
git stash push -u -m "wip: before main deploy trigger test"
```

> `-u`는 untracked 파일까지 함께 보관한다(대화 중 생성된 임시 파일/문서 등).

### 1. 현재 브랜치 확인

```bash
git branch --show-current
```

`main`이 아니면:

```bash
git checkout main
```

### 2. 원격 main 최신화(충돌 방지)

```bash
git fetch origin --prune
git pull --ff-only origin main
```

### 3. 테스트용 “노옵 파일” 1개 생성

> 주의: 이 레포는 `.gitignore`에서 `docs/` 및 일부 `*.txt`를 무시할 수 있다.
> 그래서 테스트 파일은 **레포 루트에 확장자 없이 1개 생성**하는 것을 권장한다.

```bash
echo "CI deploy trigger test: $(date -Iseconds)" > ci-deploy-trigger-test
```

### 4. 그 파일만 add/commit (중요: `git add .` 금지)

```bash
git add -f ci-deploy-trigger-test
git commit -m "chore: trigger main deploy"
```

### 5. 푸시(이때 자동 배포 트리거가 실행되어야 함)

```bash
git push origin main
```

### 6. (stash를 썼다면) 원래 작업 복원

```bash
git stash list
git stash pop stash@{0}
```

충돌이 나면, 먼저 상태 확인:

```bash
git status
```

그리고 충돌 해결 후:

```bash
git add -A
git commit -m "chore: resolve stash pop conflicts"
```

---

## 2) 트리거 실행 여부 확인

### 2.1 Cloud Console에서 확인(가장 쉬움)

1. GCP Console → Cloud Build → History
2. Location: `us-central1` 확인(중요)
3. 방금 푸시 시점 이후로 새 빌드가 생겼는지 확인
4. `Trigger` 컬럼에 아래가 찍히면 정상:
   - `nexloop-backend-deploy-main`
   - `nexloop-frontend-deploy-main`

### 2.2 gcloud로 확인(추천)

> 주의: 명령어 줄바꿈을 잘못 넣으면 `--format=...: command not found` 같은 에러가 납니다.  
> 아래 커맨드는 “한 줄씩” 그대로 복붙하세요.

최근 빌드 20개:

```bash
gcloud builds list --project=jnu-rise-edu-149 --region=us-central1 --limit=20 \
  --format="table(id,status,createTime,buildTriggerId,logUrl)"
```

특정 트리거만 필터링해서 보기(권장):

- 백엔드(main deploy 트리거)

```bash
gcloud builds list --project=jnu-rise-edu-149 --region=us-central1 --limit=10 --filter="buildTriggerId=9b383501-1a90-4a70-a66a-f6582fbaebe2" --format="table(id,status,createTime,logUrl)"
```

- 프론트(main deploy 트리거)

```bash
gcloud builds list --project=jnu-rise-edu-149 --region=us-central1 --limit=10 --filter="buildTriggerId=c88379f5-abdb-496d-91c0-1a946024b62a" --format="table(id,status,createTime,logUrl)"
```

빌드 로그 스트리밍(빌드 ID를 확인한 뒤):

```bash
gcloud builds log --project=jnu-rise-edu-149 --region=us-central1 --stream BUILD_ID
```

Cloud Run이 새 리비전으로 전환됐는지 확인(배포 검증):

```bash
gcloud run services describe nexloop-backend --project=jnu-rise-edu-149 --region=asia-northeast3 --format="value(status.latestReadyRevisionName,status.url)"
gcloud run services describe nexloop-frontend --project=jnu-rise-edu-149 --region=asia-northeast3 --format="value(status.latestReadyRevisionName,status.url)"
```

---

## 3) 자주 실패하는 원인(빠른 진단)

1. 콘솔 History에서 Location이 `global`/다른 리전으로 되어 있어 안 보임
2. 트리거가 disable 상태
3. 트리거의 브랜치 정규식이 `^main$`이 아님
4. 트리거의 구성 파일 경로가 잘못됨
   - 권장: `/cloudbuild.backend.yaml`, `/cloudbuild.frontend.yaml`
5. push가 `main`에 실제로 발생하지 않음(로컬에서 커밋만 하고 푸시를 안 한 케이스)

---

## 4) 테스트 끝나고 정리(선택)

이 노옵 파일이 거슬리면, 트리거 검증이 끝난 뒤에 삭제 커밋을 추가로 만들면 된다.

```bash
git rm -f ci-deploy-trigger-test
git commit -m "chore: remove deploy trigger test file"
git push origin main
```
