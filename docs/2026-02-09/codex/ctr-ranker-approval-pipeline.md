# CTR Ranker 승인(Approve) 워크플로우: 데이터 흐름과 자동화 파이프라인

이 문서는 Nexloop의 CTR Ranker 결과를 “대시보드에서 상위 후보를 보고 1개를 채택(승인)한다”는 운영 흐름으로 녹여내기 위한 최소 설계를 설명합니다.

핵심 원칙:

- **승인 결과는 `run_id`(실행) 단위로 귀속**됩니다. (2026-02-09 기준 결정)
- 승인 단위는 **“제목 + 썸네일 URL(=세트)”** 입니다.
- CTR Ranker의 before/after는 “온라인 CTR”이 아니라, **오프라인 ranking을 위한 proxy relevance** 기반 비교입니다.

---

## 1) Before/After가 의미하는 것

CTR Ranker 리포트에서:

- **Before**: 기존 휴리스틱 점수(예: `CTRPredictor.extract_features(...).total_score`)로 정렬한 결과
- **After**: 경량 랭킹 모델(artifact)로 다시 스코어링하여 정렬한 결과

주의:

- Before/After 스코어는 **스케일이 다를 수 있습니다**(예: Before는 70~80대, After는 0~1).
- 따라서 “score 차이” 자체보다는,
  - TopK 내 후보 구성 변화(entered/dropped)
  - Top1/TopK hit, NDCG@K 같은 ranking metric 변화
  - 그리고 최종적으로 사람이 승인(approve)한 결과의 품질
  를 중심으로 “유의미한 성과”를 보여주는 것이 안전합니다.

---

## 2) 실제 데이터 수집은 무엇을 했나

YouTube 모드 기준(2026-02-09):

1. 제품명(product_name)으로 쿼리 생성
2. YouTube 검색 결과를 가져오고
3. 각 영상의 `title`, `thumbnail` 등 메타데이터를 raw dataset으로 저장

산출물(로컬 기준):

- raw dataset: `outputs/ctr_ranker/datasets/{DATE}-youtube-raw.json`
- TopK CSV: `outputs/ctr_ranker/reports/{DATE}-top5.csv`

운영에서는 위 산출물을 GCS에 업로드해 **영구 저장**하는 것을 권장합니다.

---

## 3) 승인 워크플로우를 위한 DB 모델

추가된 테이블(최소 3개):

- `ctr_ranker_runs`
  - 실행(run) 메타데이터(제품, 날짜, 모드, 원본 경로, 메트릭 요약)
- `ctr_ranker_candidates`
  - 대시보드에서 보여줄 후보(제목/썸네일/랭킹 정보)
- `ctr_ranker_approvals`
  - 해당 run에서 **채택(승인)된 후보 1개**

마이그레이션:

- `alembic/versions/h3i4j5k6l7m8_add_ctr_ranker_approval_workflow.py`

---

## 4) Import(적재) -> Dashboard(조회) -> Approve(승인) API

엔드포인트(관리자/에디터 권한):

1. run import
   - `POST /api/v1/admin/ctr-ranker/runs/import`
   - 입력: `product_name`, `report_date`, (선택) GCS/로컬 경로들
   - 동작: raw dataset + TopK CSV를 조합해 `run/candidates`를 DB에 적재

2. run 목록
   - `GET /api/v1/admin/ctr-ranker/runs?product_name=...`

3. 후보 목록(승인 상태 포함)
   - `GET /api/v1/admin/ctr-ranker/runs/{run_id}/candidates`

4. 후보 승인(교체 가능, 항상 1개 유지)
   - `POST /api/v1/admin/ctr-ranker/runs/{run_id}/approve`
   - 입력: `candidate_id`, `note`

구현 파일:

- `src/api/v1/endpoints/ctr_ranker.py`
- `src/services/ctr_ranker_approval_service.py`

---

## 5) 자동화 파이프라인에 “어떻게” 녹일까 (추천)

운영은 2단계로 나누는 것이 안전합니다.

1. Warm-up Job (수집/리포트 생성)
   - 네트워크가 필요한 작업(YouTube 데이터 수집)
   - 산출물(raw/topK/report)을 GCS에 저장

2. Gate + Import Job (재현/적재)
   - GCS 산출물로 “재현 가능한 상태”인지 검증
   - 성공하면 `runs/import`로 DB 적재

이렇게 하면:

- Cloud Run의 ephemeral filesystem 의존을 줄이고
- “대시보드가 보는 데이터”가 항상 DB에 남아
- 승인(approve)도 audit 가능한 상태로 유지됩니다.

---

## 6) 다음 확장(선택)

- 후보를 Top5가 아니라 Top20까지 확장
- 후보 단위를 “제목+썸네일 세트” 외에도 “훅/카피/썸네일 스타일”까지 확장
- 승인 결과를 downstream 생성(썸네일 생성/영상 생성/Notion export) 파이프라인의 input으로 연결

