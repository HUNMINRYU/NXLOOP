# 경량(ML 1단계) CTR Ranking: 구현 로그 + 트러블슈팅 + Before/After 산출물

- 작성일: 2026-02-09 (KST)
- 작성 시각: 2026-02-09 09:25:56 KST
- 타임존: KST(Asia/Seoul)
- 범위: “before(기존 휴리스틱/임베딩)” vs “after(경량 선형 모델)” 비교가 재현되도록 구현/검증/산출물 위치를 정리
- 보안: API Key/Secret, `.env` 값은 어떤 형태로도 기록하지 않음

---

## 1) 이번에 추가된 것(핵심)

### 1.1 Feature 재사용을 위한 API

- 변경: `src/services/ctr_predictor.py`
- 추가: `CTRPredictor.extract_features(...)`
  - 기존 CTRPredictor 내부의 rule tower(5개) + embedding_similarity(1개) + 집계 점수(rule/embedding/total)를 **학습/평가에서 그대로 재사용**할 수 있게 함
  - 기존 `predict_ctr(...)` 로직은 `extract_features(...)` 결과를 사용하도록 리팩터링

### 1.2 경량 랭킹 모델 아티팩트/스코어링

- 추가: `src/services/ctr_ranker_artifact.py`
  - 표준화(mean/std) + 선형 스코어(w·x + b)
  - JSON 로드/덤프 지원 (`CTRRankerArtifact.load_json`, `CTRRankerArtifact.dump_json`)
- 추가: `src/services/ctr_ranker.py`
  - baseline(기존 total_score)과 after(ML score)를 한 번에 계산하기 위한 wrapper (`CTRRanker.score`)

### 1.3 오프라인 평가 메트릭(외부 의존성 없이)

- 추가: `src/services/ctr_ranker_metrics.py`
  - `ndcg_at_k`, `spearman_corr`, `top1_hit`

### 1.4 sklearn 없이도 학습 가능한 ridge trainer

- 추가: `src/services/ctr_ranker_training.py`
  - numpy 기반 폐형 해로 Ridge 회귀 학습(`train_linear_ridge_ranker`)
  - 학습 산출물을 `CTRRankerArtifact`로 반환

### 1.5 before/after 리포트 생성(재현 가능한 형태)

- 추가: `src/services/ctr_ranker_report.py`
  - 데모 데이터셋을 생성하고(네트워크/API 없이), 학습→평가→리포트를 자동 생성
  - 실행 예:
    - `.venv/bin/python -m services.ctr_ranker_report --mode demo --alpha 2.0 --k 5`

### 1.6 YouTube 실데이터 모드 + 디스크 캐시(재현성/쿼터 절약)

- 변경: `src/services/ctr_ranker_report.py`
  - `--mode youtube` 실행 시 **디스크 캐시**(`data/ctr_ranker/youtube_cache`)를 기본 사용
  - `--cache-only` 옵션으로 **네트워크 호출을 금지**하고 캐시만으로 재현 가능
  - `--write-raw-dataset` 옵션으로 수집 원본을 `outputs/ctr_ranker/datasets/*.json`에 저장(리포트 재현/감사 목적)
- 추가: `src/services/ctr_ranker_youtube_cache.py`
  - `DiskCachedYouTubeClient`: `search`, `get_video_details` 결과를 파일로 캐싱
  - 캐시 키는 입력(query/video_id)을 SHA-256으로 해시해서 저장(파일명 안정성)

---

## 2) Before / After 결과(산출물 경로)

### 2.1 리포트(Markdown)

- `docs/2026-02-09/codex/ctr-ranker-before-after.md`
  - 전체 지표 요약(NDCG@K, Spearman, Top-1 hit)
  - 그룹별 Top-5 예시(“원래는 이 정도였는데 → 모델링 후 이 정도로 변했다”를 표로 확인)

### 2.2 아티팩트(JSON)

- `outputs/ctr_ranker/artifacts/ctr_ranker_v1.json`
  - feature_names, scaler(mean/std), weights, intercept, training_meta 포함

### 2.3 평가 결과(JSON)

- `outputs/ctr_ranker/reports/2026-02-09-before-after.json`
  - 그룹별/전체 지표를 머신리더블로 저장(추후 시각화/대시보드 연결 가능)

### 2.4 그래프(PDF)

- `outputs/ctr_ranker/charts/2026-02-09-before-after.pdf`
  - HTML 대신 PDF로 Summary + Group별 Rank Shift(Top-5)를 출력
  - 생성 커맨드:
    - `.venv/bin/python -m services.ctr_ranker_charts --date 2026-02-09`

---

## 3) 트러블슈팅 노트(이번 작업에서 실제로 걸린 이슈)

### 3.1 “pytest 실행 시 오래 걸리거나 멈춘 것처럼 보임”

- 상황:
  - 시스템 `pytest` 커맨드는 없었고, `.venv/bin/python -m pytest`로 실행해야 했음.
  - 전체 테스트(`.venv/bin/python -m pytest -q`)는 일부 환경에서 진행이 길어질 수 있어, 이번 작업은 **변경 파일 관련 테스트만 타겟 실행**으로 검증함.
- 해결:
  - `.venv/bin/python -m pytest -q tests/test_ctr_predictor.py ...`처럼 타겟 실행

### 3.2 “ruff를 전체 프로젝트에 돌리면 기존 이슈가 많이 나옴”

- 상황:
  - 프로젝트 전체에 기존 lint 이슈가 다수 존재(이번 작업의 범위를 넘어섬).
- 해결:
  - 이번 변경 파일(신규/수정)만 대상으로 ruff/mypy를 통과시키는 방식으로 검증.
  - 커맨드 예:
    - `.venv/bin/python -m ruff check src/services/ctr_ranker_report.py ...`
    - `.venv/bin/python -m mypy src/services/ctr_ranker_report.py ...`

---

## 4) 검증(실행한 커맨드)

- KST 시각 확인:
  - `TZ=Asia/Seoul date '+%Y-%m-%d %H:%M:%S %Z'`
- 타겟 테스트:
  - `.venv/bin/python -m pytest -q tests/test_ctr_predictor.py`
  - `.venv/bin/python -m pytest -q tests/test_ctr_ranker_artifact.py tests/test_ctr_ranker_metrics.py tests/test_ctr_ranker_training.py`
- 타겟 lint/typecheck:
  - `.venv/bin/python -m ruff check src/services/ctr_ranker_*.py tests/test_ctr_ranker_*.py`
  - `.venv/bin/python -m mypy src/services/ctr_ranker_*.py`
- before/after 리포트 생성(데모):
  - `.venv/bin/python -m services.ctr_ranker_report --mode demo --alpha 2.0 --k 5`
- YouTube 모드(캐시 warm-up, 네트워크 필요):
  - `.venv/bin/python -m services.ctr_ranker_report --mode youtube --write-raw-dataset`
- YouTube 모드(완전 재현: 캐시만 사용):
  - `.venv/bin/python -m services.ctr_ranker_report --mode youtube --cache-only --write-raw-dataset`

---

## 5) 다음 단계(실데이터로 “진짜” before/after 만들기)

이번 산출물은 “데모 데이터셋(피처 기반 합성 proxy)”로 before/after를 보여줍니다.

실데이터 기반 개선을 하려면 아래가 필요합니다.

1. YouTube Data API v3로 영상 통계(view/like/comment/published_at)를 포함해 데이터셋 구축
2. proxy_score 정의 고정(시간 보정, 로그 스케일 등)
3. 동일한 리포트 포맷으로 “실데이터 before/after”를 생성

주의:
- 스크래핑 대신 공식 API만 사용한다는 원칙은 유지합니다.
- embedding_similarity를 피처로 포함하려면, 학습 데이터 생성 시 임베딩 호출 비용/속도 최적화(캐시)가 필요합니다.
