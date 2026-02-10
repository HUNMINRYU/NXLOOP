# PR 트리거 테스트 가이드 (초보자용) — Nexloop

- 작성일: 2026-02-10
- 목적: Cloud Build PR 트리거(`nexloop-pr-validate`)가 **실제로 PR에서 실행되는지** 빠르게 검증한다.
- 전제:
  - 레포: `HUNMINRYU/NXLOOP`
  - base 브랜치: `main`
  - PR 트리거: `nexloop-pr-validate` (이벤트: pull request, base branch `^main$`, config `cloudbuild.pr.yaml`)

> 핵심: PR은 “브랜치 간 diff”가 있어야 의미가 있다. 보통 **커밋이 1개라도 필요**하다.

## `^main$`이 맞나?

- 네. `^main$`은 **브랜치 이름이 정확히 `main`인 경우만** 매칭한다.
- `main`만 받는 게 목적이면 `^main$`을 권장한다. (오타/의도치 않은 브랜치 매칭 방지)
- `main` 및 `main-*` 같은 변형까지 허용하려면 정규식을 바꿔야 한다.

---

## 1) 가장 빠른 방법(권장): WIP 커밋 1개 만들고 PR

### 1. 새 브랜치 생성

```bash
git checkout -b ci/pr-test
```

### 2. PR 테스트용으로 “안전한 파일 1개만” 스테이징 + 커밋

> 중요한 원칙: 변경 파일이 많을 수 있으니 **파일 단위로만 `git add`** 한다.

예시(문서 파일 1개만 커밋). 이 파일 자체가 “PR 트리거 테스트용 파일”로 제일 안전하다:

```bash
git add docs/2026-02-10/codex/pr-trigger-test-guide.md
git commit -m "chore: pr trigger test"
```

또는(이미 이 파일을 건드리기 싫으면) 다른 문서 파일 1개만 커밋:

```bash
git add docs/2026-02-10/codex/ci-cd-cloudbuild-triggers.md
git commit -m "chore: pr trigger test"
```

만약 위 문서 파일이 없거나, 이미 커밋하기 애매하면:
- 아주 작은 “no-op” 문서 변경(공백 1줄 추가/삭제)만 하고 커밋해도 된다.
- 또는 `docs/` 아래에 `ci test`용 파일 1개를 새로 만들어도 된다.

### 3. 푸시

```bash
git push -u origin ci/pr-test
```

### 4. GitHub에서 PR 생성

- base: `main`
- compare: `ci/pr-test`

PR을 만들면 `nexloop-pr-validate` 트리거가 돌기 시작한다.

---

## 2) “의미 없는 커밋”이 싫으면(대안)

다음 중 하나를 추천:

1. 문서 파일에 공백 1줄만 추가/삭제(기능 영향 없음)
2. `docs/` 또는 `.github/` 아래에 테스트용 파일 1개 추가

목표는 기능 개발이 아니라 “PR 이벤트로 트리거가 돈다”를 확인하는 것이다.

---

## 3) 주의사항(실수 방지)

- 작업 트리에 변경 파일이 많을 때 `git add .` 는 금지(원치 않는 대규모 커밋이 생김)
- 반드시 아래처럼 “파일 단위”로 add 한다:

```bash
git add path/to/one-file.md
```

---

## 4) 트리거가 도는지 확인하는 방법

### 4.0 GitHub PR 화면에서 확인(제일 쉬움)

1. GitHub PR 페이지에서 “Checks” 탭 확인
2. Cloud Build App / Checks가 뜨는지 확인
3. 해당 체크를 클릭해서 로그로 이동

### 4.1 Cloud Build History에서 확인

1. GCP Console → Cloud Build → History
2. 방금 생성한 PR 시점 이후로 새 빌드가 생겼는지 확인
3. “Trigger” 또는 “트리거 이름”에 `nexloop-pr-validate`가 보이면 정상

### 4.2 gcloud로 확인(추천)

1. 트리거 ID 확인:

```bash
gcloud builds triggers list --region=us-central1 \
  --format="table(id,name,filename,disabled)"
```

2. 최근 실행 빌드 조회:

```bash
gcloud builds list --region=us-central1 \
  --filter="buildTriggerId=TRIGGER_ID" \
  --sort-by="~createTime" --limit=10 \
  --format="table(id,status,createTime,logUrl)"
```

3. 로그 스트리밍(가장 확실):

```bash
gcloud builds log --region=us-central1 --stream BUILD_ID
```

---

## 5) 잘 안 될 때(가장 흔한 원인)

- PR의 base branch가 `main`이 아님
- 트리거 이벤트가 “pull 요청”이 아니라 “브랜치로 푸시”로 되어 있음
- 브랜치 정규식이 `^main$`이 아닌 다른 값으로 설정됨
- 저장소가 `HUNMINRYU-NXLOOP`가 아닌 다른 repo로 선택됨
- 트리거의 “Cloud Build 구성 파일 위치”가 `cloudbuild.pr.yaml`가 아닌 다른 값으로 설정됨(또는 파일이 레포에 없음)

---

## 6) 테스트 끝나고 정리(선택)

1. PR 닫기(merge 하지 않음)
2. GitHub에서 테스트 브랜치 삭제
3. 로컬에서도 브랜치 삭제:

```bash
git checkout main
git branch -D ci/pr-test
```
