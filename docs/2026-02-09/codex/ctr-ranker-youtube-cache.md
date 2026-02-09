# CTR Ranker YouTube 모드: 디스크 캐시로 재현 가능한 실험

- 작성일: 2026-02-09 (KST)
- 목적:
  - YouTube Data API v3 호출 결과를 파일로 남겨서, 동일한 입력으로 **항상 같은 데이터셋/리포트**를 재현
  - 쿼터/네트워크 불안정에 영향을 덜 받도록 구성
- 관련 코드:
  - `src/services/ctr_ranker_report.py` (데이터셋 생성 + 학습/평가 + 리포트 생성)
  - `src/services/ctr_ranker_youtube_cache.py` (디스크 캐시 래퍼)
- 관련 문서(규칙):
  - `docs/2026-02-08/cursor/git-strategy.md` (기능 브랜치 워크플로우)
  - `docs/2026-02-08/cursor/logging-strategy.md` ([FEATURE] 로깅 규칙)

---

## 1) 캐시 디렉터리 구조

기본 캐시 경로: `data/ctr_ranker/youtube_cache`

- `data/ctr_ranker/youtube_cache/search/*.json`
- `data/ctr_ranker/youtube_cache/details/*.json`

각 파일은 아래 형식을 가집니다.

```json
{
  "cached_at_iso": "2026-02-09T00:00:00+00:00",
  "value": ...
}
```

---

## 2) 실행 방법 (Runbook)

### 2.0 브랜치/상태 확인(권장)

```bash
cd /home/amoo/projects/nexloop
git branch --show-current
git status --porcelain=v1
```

- 권장: 기능 브랜치에서 진행 (`feature/ctr-ranker-youtube-cache` 등)

### 2.1 가상환경 확인

```bash
cd /home/amoo/projects/nexloop
ls -la .venv/bin/python
.venv/bin/python -V
```

### 2.2 (중요) YouTube API Key 설정 확인

`--mode youtube`는 `get_settings().gcp.google_api_key`를 사용합니다. 즉 `.env`에 키가 있어야 합니다.

```bash
cd /home/amoo/projects/nexloop
rg -n "google_api_key|GOOGLE_API_KEY" .env .env.example src/config/settings.py
```

주의:
- 키 값 자체는 문서/로그에 남기지 않습니다.

### 2.3 캐시 warm-up(네트워크 필요)

```bash
.venv/bin/python -m services.ctr_ranker_report --mode youtube --write-raw-dataset
```

- 기본적으로 `data/ctr_ranker/youtube_cache`에 `search/details` 결과를 저장합니다.
- 원본 수집 결과는 `outputs/ctr_ranker/datasets/<date>-youtube-raw.json`에 남습니다.

옵션 예시(데이터량 조절):

```bash
.venv/bin/python -m services.ctr_ranker_report \
  --mode youtube \
  --max-results-per-query 10 \
  --queries-per-product 2 \
  --cache-ttl-sec 86400 \
  --write-raw-dataset
```

### 2.4 완전 재현 모드(cache-only)

```bash
.venv/bin/python -m services.ctr_ranker_report --mode youtube --cache-only --write-raw-dataset
```

- 네트워크 호출 없이 캐시만 사용합니다.
- 캐시가 없으면 실패합니다(실험 재현을 위한 의도).

### 2.5 TTL 조절

```bash
.venv/bin/python -m services.ctr_ranker_report --mode youtube --cache-ttl-sec 3600
```

- TTL이 지나면 캐시를 무시하고(가능하면) 다시 호출해 갱신합니다.

### 2.6 PDF 그래프 생성(HTML 대신)

```bash
.venv/bin/python -m services.ctr_ranker_charts --date <YYYY-MM-DD>
```

예:

```bash
.venv/bin/python -m services.ctr_ranker_charts --date 2026-02-09
```

---

## 3) 산출물

- 리포트(JSON): `outputs/ctr_ranker/reports/<date>-before-after.json`
- 리포트(Markdown): `docs/<date>/codex/ctr-ranker-before-after.md`
- 그래프(PDF): `outputs/ctr_ranker/charts/<date>-before-after.pdf`
  - 생성: `.venv/bin/python -m services.ctr_ranker_charts --date <date>`

---

## 4) 트러블슈팅

### 4.1 `YouTube search 실패`

가능한 원인:
- API Key 미설정/오타
- 쿼터 초과
- 네트워크/DNS 문제

확인:
- `src/config/settings.py`에서 키 이름 확인
- `.env`에 동일 키가 들어있는지 확인

### 4.2 `cache_only 모드에서 ... 캐시를 찾지 못했습니다`

의미:
- warm-up이 충분히 수행되지 않았거나
- `--cache-dir`을 다르게 줬는데 경로를 착각했거나
- 캐시 디렉터리를 지워버린 경우

확인:
```bash
ls -la data/ctr_ranker/youtube_cache/search | head
ls -la data/ctr_ranker/youtube_cache/details | head
```

### 4.3 로그로 실행 여부 확인

성공 시 아래 형태의 로그가 남습니다.
- `[FEATURE] ▶ ctr_ranker_report 시작`
- `[FEATURE] ■ ctr_ranker_report 완료`

