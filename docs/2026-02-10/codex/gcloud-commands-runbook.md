# gcloud/gh 명령어 런북 (이번 작업에서 사용한 것들)

## 1) Cloud Build 최근 실행 조회

```bash
gcloud builds list \
  --project=jnu-rise-edu-149 \
  --region=us-central1 \
  --limit=10
```

트리거별 실행만 보고 싶으면:

```bash
gcloud builds list \
  --project=jnu-rise-edu-149 \
  --region=us-central1 \
  --limit=10 \
  --filter="buildTriggerId=YOUR_TRIGGER_ID" \
  --format="table(id,status,createTime,logUrl)"
```

주의: 줄바꿈을 할 때는 반드시 줄 끝에 `\`가 있어야 `--format` 같은 플래그가 “다음 명령어”로 인식되지 않는다.

## 2) Cloud Build 상세 조회

```bash
gcloud builds describe BUILD_ID \
  --project=jnu-rise-edu-149 \
  --region=us-central1 \
  --format="yaml(status,statusDetail,logUrl,substitutions)"
```

## 3) Cloud Build 로그 스트리밍

Cloud Logging only 설정이면 기본 `gcloud builds log --stream`에서 NOT_FOUND가 날 수 있다.
이 경우 `gcloud beta builds log --stream` 또는 Cloud Console `logUrl`을 사용한다.

```bash
gcloud beta builds log \
  --project=jnu-rise-edu-149 \
  --region=us-central1 \
  --stream BUILD_ID
```

## 4) Cloud Run 로그 확인(대체: Cloud Logging read)

서비스 로그:

```bash
gcloud logging read \
  --project=jnu-rise-edu-149 \
  --freshness=30m \
  --limit=200 \
  "resource.type=cloud_run_revision AND resource.labels.service_name=\"nexloop-frontend\"" \
  --format="value(timestamp,severity,jsonPayload.message,textPayload,httpRequest.status,httpRequest.requestUrl)"
```

에러만:

```bash
gcloud logging read \
  --project=jnu-rise-edu-149 \
  --freshness=30m \
  --limit=200 \
  "resource.type=cloud_run_revision AND resource.labels.service_name=\"nexloop-backend\" AND severity>=ERROR" \
  --format="value(timestamp,severity,jsonPayload.message,textPayload)"
```

## 5) GitHub PR 생성/머지 (gh)

PR 생성:

```bash
gh pr create \
  --base main \
  --head BRANCH \
  --title "TITLE" \
  --body "BODY"
```

머지:

```bash
gh pr merge PR_NUMBER --merge
```

