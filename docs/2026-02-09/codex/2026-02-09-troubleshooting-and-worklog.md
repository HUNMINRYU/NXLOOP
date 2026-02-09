# 2026-02-09 작업 정리 + 트러블슈팅 로그 (Nexloop)

최종 업데이트: **2026-02-09 14:56:43 KST**

## 배경(요청 의도)
이번 작업의 목표는 2가지였습니다.
1. Create 단계에서 생성되는 산출물(썸네일/비디오)을 **“CTR이 높아 보이는 순”으로 배치**해 빠르게 판단할 수 있게 만들기
2. 사용자가 1개를 **채택(승인)**하면, 그 결과물을 **다음 단계(Distribution)의 입력으로 고정**해서 “다음 단계로 넘어가는 흐름”이 되게 만들기

추가로, 사용자가 선택한 썸네일을 Start Frame으로 사용해 **I2V(Image-to-Video)로 비디오를 재생성**하고 그 결과를 자동 채택하는 최소 기능까지 연결했습니다.

---

## 실행 환경(문제 재현에 필요한 정보)
- OS: WSL2 (Ubuntu 24.04)
- Repo: `/home/amoo/projects/nexloop`
- Python: `/home/amoo/projects/nexloop/.venv/bin/python`
- Jupyter Notebook cwd(문제 당시): `.../docs/2026-02-09/codex`

---

## 트러블슈팅 1) “파일이 있는데 없다고 나옴” (Notebook 상대경로 문제)

### 증상
노트북에서 아래처럼 상대경로로 체크할 때, 파일이 분명 존재함에도 `exists()`가 `False`가 됨.

```py
from pathlib import Path
DATE = "2026-02-09"
REPORT_JSON = Path(f"outputs/ctr_ranker/reports/{DATE}-before-after.json")
assert REPORT_JSON.exists()
```

출력 예시(문제 상황):
- cwd: `/home/amoo/projects/nexloop/docs/2026-02-09/codex`
- resolve: `/home/amoo/projects/nexloop/docs/2026-02-09/codex/outputs/...`
- exists/is_file: `False`

### 원인
노트북의 현재 작업 디렉토리(`Path.cwd()`)가 프로젝트 루트가 아니라 `docs/2026-02-09/codex`여서,
`outputs/...`가 **프로젝트 루트의 outputs가 아니라 “노트북 폴더 아래 outputs”**를 가리켰습니다.

### 해결(권장 패턴)
노트북에서는 `__file__`이 안정적으로 존재하지 않으므로, “프로젝트 루트”를 명시적으로 잡는 방식이 가장 안전합니다.

```py
from pathlib import Path

ROOT = Path("/home/amoo/projects/nexloop")  # 가장 확실한 방법(권장)
REPORT_JSON = ROOT / "outputs/ctr_ranker/reports/2026-02-09-before-after.json"
assert REPORT_JSON.is_file(), f"리포트 JSON이 없습니다: {REPORT_JSON} (cwd={Path.cwd()})"
```

대안(자동 탐색): 상위 디렉토리를 올라가며 `pyproject.toml` 같은 “루트 마커”를 찾는 방식.

```py
from pathlib import Path

def find_repo_root(start: Path) -> Path:
    for p in [start, *start.parents]:
        if (p / "pyproject.toml").exists():
            return p
    return start

ROOT = find_repo_root(Path.cwd())
```

---

## 트러블슈팅 2) VSCode/WSL에서 “커널 선택이 헷갈림”

### 권장 커널
프로젝트 가상환경(`.venv`)의 Python을 커널로 쓰는 것이 가장 안전합니다.
- `/home/amoo/projects/nexloop/.venv/bin/python`

### 체크 포인트
- VSCode Jupyter에서 “Python 환경(Interpreter)”과 “Notebook Kernel”이 **다르게 잡힐 수 있음**
- “pip로 설치한 라이브러리가 안 보인다” 같은 문제는 대부분 커널/인터프리터 불일치에서 발생

---

## 트러블슈팅 3) Create에서 채택했는데 Distribution에 바로 반영이 안 됨

### 원인(전형적)
- 프론트에서 채택 API를 호출해도, 현재 페이지의 로컬 상태만 바뀌고
- 다른 단계(Distribution)에서는 여전히 “이전 pipelineResult”를 보고 있을 수 있음

### 해결(최소 구현)
Create/Distribution에서 채택 이후 또는 필요할 때 **`fetchPipelineResult(task_id)`로 결과를 갱신**해서 store에 반영.

추가로 Distribution에 **`결과 새로고침` 버튼**을 제공해, 클릭 1번으로 최신 `selected_outputs`를 가져오게 했습니다.

---

## 트러블슈팅 4) CTR 순 정렬이 가끔 안 됨

### 원인
썸네일 정렬에 사용되는 CTR 예측 API가 `PRO` 티어 제약을 가질 수 있어(403 등),
예측 호출이 실패하면 점수를 못 받아 정렬이 스킵될 수 있습니다.

### 해결(최소 + 안정성)
정렬이 실패해도 화면이 “들쭉날쭉” 흔들리지 않게 폴백 정렬을 넣었습니다.
- 점수 있는 후보 우선
- 점수는 내림차순
- 점수 없으면 URL 마지막 파일명 기준 고정 정렬(그리고 원래 index로 안정화)

---

## 구현된 기능(최소 기능, 흐름 연결)

### 1) 대표 산출물 채택(selected_outputs)
- Create에서 썸네일/비디오 각각 “채택” 버튼 제공
- 선택 결과를 `selected_outputs.thumbnail` / `selected_outputs.video`에 기록
- 저장 위치는 2단계 폴백:
  - in-memory 결과(`PIPELINE_RESULTS`)
  - history metadata 파일(`outputs/**/metadata/{task_id}.json`)

관련 코드:
- `src/api/v1/endpoints/pipeline.py` (select-output)
- `frontend/src/components/PipelineSlugClient.tsx`
- `frontend/src/lib/api.ts` (`selectPipelineOutput`)

### 2) 선택 썸네일 기반 비디오 재생성(I2V) + 자동 채택
- 버튼: Create > Videos 섹션의 `선택 썸네일로 비디오 생성`
- 동작:
  1. `selected_outputs.thumbnail.url` 다운로드
  2. 이미지 기반 프롬프트 생성(가능하면 vision narrative, 아니면 marketing prompt)
  3. I2V 생성
  4. GCS 업로드 후 URL 발급
  5. 결과를 `generated_content.video_url` 업데이트
  6. `selected_outputs.video`를 자동 채택 처리

권한:
- 현재 `PRO` 티어 필요

관련 코드:
- `src/api/v1/endpoints/pipeline.py` (generate-video-from-selected-thumbnail)
- `src/services/video_service.py` (generate_from_image)
- `frontend/src/lib/api.ts` (`generateVideoFromSelectedThumbnail`)
- `frontend/src/components/PipelineSlugClient.tsx`

### 3) Distribution에서 “대표 산출물만” 단순 노출 + 새로고침
- Distribution 단계에서는 `selected_outputs.thumbnail/video`만 간단하게 보여줌
- `결과 새로고침` 버튼으로 최신 결과를 즉시 반영

관련 코드:
- `frontend/src/components/PipelineSlugClient.tsx`

---

## Rank Shift(노트북에서 헷갈렸던 지표) 해석 가이드
`rank shift`는 “before 랭킹”과 “after 랭킹” 사이에서 **순위가 얼마나 움직였는지**를 의미하는 값입니다.

일반적 정의(구현에 따라 부호는 다를 수 있음):
- `rank_shift = before_rank - after_rank`
  - 양수: after에서 순위가 올라감(숫자가 작아짐, 더 상위)
  - 음수: after에서 순위가 내려감(숫자가 커짐, 더 하위)

실무에서는 “rank shift 자체”보다 아래 요약이 더 직관적입니다.
- `top1_changed`: 1등이 바뀌었는지
- `entered / dropped`: Top-K에 새로 들어온 항목 / 빠진 항목 수
- `NDCG@K`: 상위 랭킹 품질이 얼마나 좋아졌는지(모델/스코어 기반 평가)

---

## 검증(실행한 커맨드)
- 프론트 타입체크:
  - `cd frontend && npm run typecheck`
- 백엔드 변경 파일 린트(ruff):
  - `./.venv/bin/python -m ruff check src/api/v1/endpoints/pipeline.py`
- 단위 테스트(CTR Ranker 승인 서비스):
  - `./.venv/bin/python -m pytest -q tests/test_ctr_ranker_approval_service.py`

---

## 남아있는 리스크/제약(현재 MVP 기준)
- `selected_outputs`는 DB가 아니라 **in-memory + metadata 파일 기반** 저장(운영/동시성/권한 모델을 강하게 하려면 DB화 필요)
- I2V 생성은 `PRO` 티어 필요(권한 정책상 FREE에서 버튼이 실패할 수 있음)
- 썸네일 URL이 “서명 URL”인 경우 만료되면 다운로드 실패 가능
  - 증상: `썸네일 다운로드 실패`
  - 대응: URL refresh(서명 URL 갱신) 또는 다시 채택 처리

---

## 관련 문서
- Create 산출물 채택 플로우: `docs/2026-02-09/codex/pipeline-selected-output-flow.md`

