# 파이프라인 메트릭 용어 정리 (필터링률/선정률 혼동 방지)

> 작성일: 2026-02-10  
> 대상: Nexloop 파이프라인(X-Algorithm) `PipelineOrchestrator` 결과 `stats`

## TL;DR

- **필터링률(filtering_rate)** = *제거율*입니다.  
  "원본 N건 중 필터 단계에서 몇 건이 **제거**됐는가"를 의미합니다.
- **선정률(selection_rate)** = *top_k 선택율*입니다.  
  "필터 이후 남은 후보 중 최종 결과로 몇 건을 **선정**했는가"를 의미합니다.

따라서 **`20건 → 5건`으로 줄었더라도**, 그 15건이 "필터로 제거"된 게 아니라 "top_k로 선택되지 않은 것"이면 **필터링률은 0%가 정상**입니다.

## 카운트 기준 정의

- `original_count`: Source 단계에서 생성된 원본 후보 건수
- `removed_count`: pre/post filter 단계에서 **제거된** 후보 건수의 합
- `after_filter_count`: 필터 이후 남은 후보 건수(= scoring 입력 건수)
- `selected_count`: 최종 선정(top_k)된 건수(= 결과 건수)

## 비율 기준 정의

모든 rate는 `0.0 ~ 1.0` 범위입니다.

- `filtering_rate`: `removed_count / original_count`  
  이름은 유지하지만 의미는 "필터링(제거) 비율"입니다.
- `removed_rate`: `removed_count / original_count`  
  `filtering_rate`와 동일 의미(혼동 방지용 별칭)
- `selection_rate_of_original`: `selected_count / original_count`  
  원본 대비 최종 선정률
- `selection_rate_of_filtered`: `selected_count / after_filter_count`  
  필터 후 대비 최종 선정률
- `reduction_rate_of_original`: `1 - (selected_count / original_count)`  
  원본 대비 축소율(선정되지 않은 비율)

## 로그에서 확인하는 법

백엔드 로그에 아래 형태가 찍히면 수치 해석은 다음과 같습니다.

- `removed_rate`가 0%: **필터로 제거된 건이 거의 없음**
- `selection_rate`가 25%: **top_k(선정)로 1/4만 남김**
- `reduction`이 75%: **원본 대비 75%는 최종 결과에 포함되지 않음**

## 관련 코드

- `src/services/pipeline/orchestrator.py`
- `src/core/models/pipeline.py`

