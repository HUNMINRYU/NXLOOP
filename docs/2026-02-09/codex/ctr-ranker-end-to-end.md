# CTR Ranker: 데이터 수집 → 학습 → 평가 → 리포트 생성 (End-to-End 문서)

- 기준 날짜: `2026-02-09` (KST)
- 목적: “before(기존 휴리스틱 점수)” vs “after(경량 선형 모델 점수)”를 **동일 데이터셋**에서 비교하고, 재현 가능한 리포트를 남긴다.
- 핵심 주의: 여기서의 `proxy_score`는 **실제 CTR이 아니라** 오프라인 랭킹 평가를 위한 “상대적 선호도 라벨”이다.

---

## 1) 한 문장 요약

`services.ctr_ranker_report`가 (1) 데이터셋을 만들고(데모 또는 YouTube API 기반) (2) 기존 점수(`CTRPredictor.total_score`)와 (3) 학습된 점수(`CTRRanker.ml_score`)를 같은 후보군에 계산한 뒤 (4) `ndcg_at_k / spearman_corr / top1_hit`로 before/after를 비교하고 (5) JSON/Markdown/PDF 산출물로 저장한다.

---

## 2) 산출물(결과물)과 위치

리포트 실행이 성공하면 아래 파일들이 생성된다.

- 평가 리포트(JSON)
  - `outputs/ctr_ranker/reports/<YYYY-MM-DD>-before-after.json`
  - 예: `outputs/ctr_ranker/reports/2026-02-09-before-after.json`
- 리포트(Markdown)
  - `docs/<YYYY-MM-DD>/codex/ctr-ranker-before-after.md`
  - 예: `docs/2026-02-09/codex/ctr-ranker-before-after.md`
- 모델 아티팩트(JSON)
  - `outputs/ctr_ranker/artifacts/ctr_ranker_v1.json`
- 그래프(PDF)
  - `outputs/ctr_ranker/charts/<YYYY-MM-DD>-before-after.pdf`
  - 생성: `.venv/bin/python -m services.ctr_ranker_charts --date <YYYY-MM-DD>`

---

## 3) 전체 파이프라인 개요(흐름)

코드 기준: `src/services/ctr_ranker_report.py`

1. 데이터셋 생성
   - `--mode demo`: 네트워크 없이 데모 데이터 생성
   - `--mode youtube`: YouTube Data API v3로 후보 영상을 수집해 데이터셋 생성(디스크 캐시 지원)
2. 학습용 라벨(`proxy_score`) 준비
   - demo: 피처에서 합성(proxy) 라벨 생성
   - youtube: 공개 지표(view/like/comment/published_at)로 proxy 라벨 생성
3. 피처 추출 및 점수 계산(동일 후보군)
   - `CTRPredictor.extract_features(...)`로 피처를 재사용
   - before 점수: `features["total_score"]`
   - after 점수: 학습된 선형 모델의 `CTRRankerArtifact.score_from_features(...)`
4. 학습(경량 Ridge)
   - `train_linear_ridge_ranker(...)` (numpy 기반 폐형해)
   - 산출물을 `CTRRankerArtifact`로 저장
5. 평가(before/after)
   - 그룹 단위로 `ndcg_at_k / spearman_corr / top1_hit` 계산
   - 그룹별 결과를 평균내서 전체 지표를 만든다.
6. 리포트 저장(JSON/MD) + (선택) 차트(PDF)

---

## 4) 데이터 수집/생성 방식(정확히)

### 4.1 `--mode demo`: 네트워크 없는 데모 데이터

코드 기준: `src/services/ctr_ranker_report.py`

- 데이터 생성: `build_demo_dataset(predictor)`
- 후보 타이틀(title)들은 “제품명 × 훅(hook)” 조합으로 만들어진다.
- 각 아이템은 `ReportItem(group_id, item_id, title, proxy_score)`를 가진다.
- `proxy_score`는 데모용으로 **피처에서 합성**한다:
  - `predictor.extract_features(...)`의 `breakdown` 피처를 가져온다.
  - `_proxy_from_features(...)`에서 고정 가중치로 합성 점수를 만들고, 리포트용 스케일로 축소한다(상대순위만 중요).

이 모드의 의도는 “학습 후 개선이 눈에 띄게 나오도록” 설계된 합성 라벨로 파이프라인 전체(학습/평가/리포트)를 재현 가능하게 만드는 것이다.

### 4.2 `--mode youtube`: YouTube Data API v3 기반 실데이터(공개 지표)

코드 기준: `src/services/ctr_ranker_report.py`

- 데이터 생성: `build_youtube_dataset(...)`
- 데이터는 “제품명 + 쿼리” 단위로 수집되고, 그룹은 `"{제품명}::{q_i}"` 형태다.
- YouTube 수집 흐름:
  1. `yt.search(query, max_results=...)`로 후보 영상 목록 수집
  2. 각 영상에 대해 `yt.get_video_details(video_id)`로 상세 지표 조회
  3. 공개 지표로 proxy 라벨 생성:
     - `_proxy_from_youtube_metrics(view_count, like_count, comment_count, published_at, now)`
     - `log1p` 변환과 published_at 기반 age penalty를 적용하고, relevance scale로 축소한다.

#### 인증/설정(중요)

- `--mode youtube`는 설정에서 YouTube API Key를 읽는다.
  - 코드 경로: `get_settings().gcp.google_api_key` (설정 로딩은 `src/config/settings.py` 계열)
- 키 값 자체는 문서/로그에 남기지 않는다(보안 원칙).

#### 재현성/쿼터 절약: 디스크 캐시

관련 코드: `src/services/ctr_ranker_youtube_cache.py`

- 기본 캐시 경로: `data/ctr_ranker/youtube_cache`
  - `data/ctr_ranker/youtube_cache/search/*.json`
  - `data/ctr_ranker/youtube_cache/details/*.json`
- `--cache-only`를 켜면 네트워크 호출을 금지하고 캐시만으로 재현한다(캐시가 없으면 실패).
- `--write-raw-dataset`를 켜면 원본 수집 결과를
  - `outputs/ctr_ranker/datasets/<date>-youtube-raw.json`
  로 저장해 “리포트 생성에 사용한 입력”을 남긴다.

---

## 5) 점수( before / after )가 의미하는 것

관련 코드:
- `src/services/ctr_predictor.py`
- `src/services/ctr_ranker.py`
- `src/services/ctr_ranker_artifact.py`

### 5.1 Before(기존 baseline)

- `CTRPredictor.extract_features(...)`의 결과 중 `total_score`를 사용한다.
- 이 값은 CTRPredictor의 rule tower + embedding_similarity 등을 합친 “휴리스틱 점수”다.

### 5.2 After(학습된 경량 모델)

- `CTRRanker.score(...)`는 같은 피처에 대해 `ml_score`를 계산한다.
- `ml_score`는 `CTRRankerArtifact`(표준화 + 선형 결합)의 결과다.
- 아티팩트에는 대략 아래가 들어간다:
  - `feature_names`
  - `scaler_mean`, `scaler_std`
  - `weights`, `intercept`
  - `training_meta` (버전/하이퍼파라미터 등)

---

## 6) 학습(경량 Ridge) 과정

관련 코드: `src/services/ctr_ranker_training.py`

- 목적: `proxy_score`를 잘 설명(근사)하는 가중치를 학습해, 결과적으로 `proxy_score` 순서에 더 가까운 정렬을 만들기
- 모델: 선형 + Ridge 정규화(폐형 해)
- 결과: `CTRRankerArtifact` 생성 → `outputs/ctr_ranker/artifacts/ctr_ranker_v1.json`에 저장

---

## 7) 평가(정확한 계산 단위와 메트릭)

관련 코드:
- `src/services/ctr_ranker_report.py` (`evaluate_before_after`)
- `src/services/ctr_ranker_metrics.py`

### 7.1 그룹 단위 평가

그룹(`group_id`)별로 후보 아이템들을 묶고, 그 그룹 내부에서:

- `true_scores`: 각 아이템의 `proxy_score`
- `pred_scores_before`: baseline 점수(`total_score`)
- `pred_scores_after`: ML 점수(`ml_score`)

를 같은 아이템 순서로 놓고 비교한다.

또한, 각 아이템의 `competitor_titles`는 “같은 그룹 내 다른 타이틀들” 일부를 사용한다(피처 계산에 경쟁자 맥락을 주기 위함).

### 7.2 메트릭 정의

- `ndcg_at_k(pred_scores, true_scores, k)`
  - Top-k에서 `true_scores(proxy_score)`가 높은 아이템이 더 위에 올수록 증가
- `spearman_corr(pred_scores, true_scores)`
  - 순위 상관(동률은 평균 순위 처리)
- `top1_hit(pred_scores, true_scores)`
  - pred의 1등 아이템이 true의 1등과 일치하면 1, 아니면 0

### 7.3 전체 지표(평균)

리포트 상단의 `ndcg_before/after`, `spearman_before/after`, `top1_before/after`는
**그룹별 점수의 평균(mean)** 이다.

---

## 8) 리포트 JSON 포맷(요약)

파일: `outputs/ctr_ranker/reports/<date>-before-after.json`

- 최상위
  - `group_count`, `item_count`, `k`
  - `ndcg_before`, `ndcg_after`
  - `spearman_before`, `spearman_after`
  - `top1_before`, `top1_after`
  - `groups`: 그룹별 상세 리스트
- `groups[*]`
  - `group_id`
  - `ndcg_before/after`, `spearman_before/after`, `top1_before/after`
  - `top5_before`, `top5_after`
    - 각 원소: `{title, proxy_score, score}`
    - `score`는 before면 baseline 점수, after면 ml 점수

---

## 9) 실행 방법(재현 가능한 커맨드)

### 9.1 데모 모드(네트워크 없이)

```bash
.venv/bin/python -m services.ctr_ranker_report --mode demo --alpha 2.0 --k 5
```

### 9.2 YouTube 모드(warm-up, 네트워크 필요)

```bash
.venv/bin/python -m services.ctr_ranker_report --mode youtube --write-raw-dataset
```

#### (선택) 특정 제품만 실행

```bash
.venv/bin/python -m services.ctr_ranker_report --mode youtube --product-name "벅스델타" --write-raw-dataset
```

주의:
- `--cache-only`와 함께 쓸 경우, 해당 제품/쿼리에 대한 캐시가 디스크에 이미 있어야 합니다. 없으면 실패합니다.

### 9.3 YouTube 모드(완전 재현: cache-only)

```bash
.venv/bin/python -m services.ctr_ranker_report --mode youtube --cache-only --write-raw-dataset
```

### 9.4 YouTube Raw replay(네트워크 없이, raw 입력으로 재현)

이미 생성된 raw dataset(`--write-raw-dataset` 산출물)을 입력으로, 네트워크 없이 동일한 평가 리포트를 재생성합니다.

```bash
.venv/bin/python -m services.ctr_ranker_report \
  --mode youtube-raw \
  --raw-path outputs/ctr_ranker/datasets/2026-02-09-youtube-raw.json \
  --k 5
```

#### (선택) 특정 제품만 raw에서 재생성

```bash
.venv/bin/python -m services.ctr_ranker_report \
  --mode youtube-raw \
  --raw-path outputs/ctr_ranker/datasets/2026-02-09-youtube-raw.json \
  --product-name "벅스델타" \
  --k 5
```

참고:
- 제품명이 한글처럼 ASCII 슬러그로 직접 표현하기 어려운 경우, 산출물 파일명에는 `product-<hash>` 형태의 접미사가 붙습니다(충돌 방지).

### 9.4 차트(PDF) 생성

```bash
.venv/bin/python -m services.ctr_ranker_charts --date 2026-02-09
```

---

## 10) 결과 해석 가이드(무엇이 “개선”인가)

이 파이프라인에서 “개선”은 다음을 의미한다.

- 같은 후보군에 대해, After 정렬이 Before 정렬보다 `proxy_score` 순서(정답 성격)에 더 잘 맞는다.
- 대표 신호:
  - `ndcg_after > ndcg_before`
  - `spearman_after > spearman_before`
  - 그룹별 Top-5에서 After 쪽이 더 높은 `proxy_score` 아이템을 상단에 배치

추가 주의:
- `proxy_score`가 음수일 수 있어, 구현된 NDCG가 1을 넘는 케이스가 생길 수 있다.
  - 따라서 절대값보다 **before 대비 after의 변화 방향** 중심으로 판단하는 것을 권장한다.

---

## 11) 운영/재현 팁(로그/시간)

- 리포트 날짜는 실행 시각의 타임존(KST)을 기준으로 문자열(`YYYY-MM-DD`)이 결정된다.
  - 코드: `KST = timezone(timedelta(hours=9))`, `_kst_date_str(...)`
- 실행 여부는 `[FEATURE]` 로그로 확인할 수 있다.
  - 예: `[FEATURE] ▶ ctr_ranker_report 시작` / `[FEATURE] ■ ctr_ranker_report 완료`
