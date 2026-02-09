# CTR Ranker Notebook 실행 가이드 (Jupyter)

- 작성일: 2026-02-09 (KST)
- 노트북: `docs/2026-02-09/codex/ctr-ranker-before-after.ipynb`
- 입력 리포트(JSON): `outputs/ctr_ranker/reports/<date>-before-after.json`

---

## 1) 이 노트북이 하는 일

- Summary 지표(NDCG@K, Spearman, Top-1 hit)를 **SVG 그래프**로 시각화합니다.
- Group별 Top-5 before/after를 **Rank Shift(Slope/Bump) 스타일** SVG로 보여줍니다.
- (선택) matplotlib이 설치돼 있으면 같은 Summary를 matplotlib로도 그릴 수 있습니다.

---

## 2) 실행 전 준비

현재 이 개발 환경에서는 `pip install`이 DNS 문제로 실패할 수 있습니다(특히 `jupyter`, `matplotlib`).

따라서 아래 중 하나를 선택하세요.

### 옵션 A) 이미 Jupyter가 설치된 환경에서 실행 (권장)

- 로컬 PC에 Jupyter/Anaconda/Miniforge 등이 이미 설치되어 있으면 그 환경에서 노트북을 여는 방식

### 옵션 B) 네트워크가 되는 환경에서 설치 후 실행

- `pip`가 PyPI를 정상적으로 접근할 수 있는 환경에서:

```bash
python -m pip install jupyter matplotlib
```

---

## 3) 실행 방법

### 3.1 리포트 JSON이 존재하는지 확인

```bash
ls -la outputs/ctr_ranker/reports | tail
```

예: `2026-02-09-before-after.json`이 있어야 합니다.

### 3.2 노트북 열기

Jupyter가 있는 환경에서 레포 루트(`/home/amoo/projects/nexloop`) 기준으로 열면 됩니다.

노트북 경로:
- `docs/2026-02-09/codex/ctr-ranker-before-after.ipynb`

### 3.3 날짜 바꾸기

노트북 첫 코드 셀에서 아래 값을 바꾸면 다른 날짜 리포트를 볼 수 있습니다.

- `DATE = '2026-02-09'`

---

## 4) matplotlib로 그리고 싶다면

노트북 하단 “(선택) matplotlib로 그리기” 셀을 실행합니다.

- import가 실패하면 먼저 matplotlib을 설치해야 합니다.
- 설치가 어려운 환경이라면, 노트북의 기본 SVG 그래프만으로도 시각화는 가능합니다.

