# Create 산출물 “채택 → 다음 단계” 미니멀 플로우

## 목적
Create 단계에서 생성되는 여러 썸네일/비디오 산출물 중 **“클릭율(CTR)이 높아 보이는 후보”를 먼저 보여주고**, 사용자가 **대표 1개를 채택(승인)**하면 그 결과물을 **다음 단계(Distribution) 입력으로 고정**한다.

핵심은 2가지다.
1. **정렬**: 후보들을 “CTR이 높아 보이는 순”으로 배치한다.
2. **채택(대표 선택)**: 사용자가 선택한 1개를 `selected_outputs`에 기록하고, 이후 단계에서 그 값만 보게 한다.

---

## 사용자 경험(UX) 요약
1. Create 화면에서 썸네일 후보가 여러 개 보인다.
2. 각 후보에는 예측 점수(가능하면 `predicted_ctr`, 아니면 `total_score`)가 표시되고, 점수 내림차순으로 정렬된다.
3. 사용자는 “채택” 버튼으로 썸네일 1개를 선택한다.
4. (옵션) “선택 썸네일로 비디오 생성” 버튼을 누르면:
   - 채택한 썸네일을 Start Frame으로 사용해 I2V 비디오를 새로 생성한다.
   - 생성된 비디오를 자동으로 `selected_outputs.video`에 채택한다.
5. Distribution 화면에서는 `selected_outputs.thumbnail` / `selected_outputs.video`만 간단히 보여준다.

---

## 데이터 구조(저장 형태)
Pipeline 결과에 아래 형태로 저장한다.

```json
{
  "selected_outputs": {
    "thumbnail": {
      "url": "https://...",
      "meta": {
        "predictedCtr": 3.2,
        "grade": "A",
        "style": "clean",
        "hook_text": "..."
      },
      "selected_by": "user@email",
      "selected_at": "2026-02-09T..."
    },
    "video": {
      "url": "https://...",
      "meta": {
        "source": "selected_thumbnail_i2v",
        "duration_seconds": 8
      },
      "selected_by": "user@email",
      "selected_at": "2026-02-09T..."
    }
  }
}
```

저장은 2단계 폴백을 가진다.
- in-memory 결과(`PIPELINE_RESULTS`)가 있으면 거기에 기록
- 없으면 history metadata 파일(`outputs/**/metadata/{task_id}.json`)에 기록

---

## API 엔드포인트
### 1) 대표 산출물 채택
- `POST /pipeline/result/{task_id}/select-output`

Payload:
- `kind`: `'thumbnail' | 'video'`
- `url`: 선택한 산출물 URL
- `meta`: 점수/훅/스타일 등 UI 표시용 부가 정보

### 2) 선택 썸네일 기반 비디오 재생성(I2V) + 자동 채택
- `POST /pipeline/result/{task_id}/generate-video-from-selected-thumbnail`

동작:
1. `selected_outputs.thumbnail.url`을 다운로드
2. 이미지 기반으로 비디오 프롬프트를 만들고(I2V) 비디오 생성
3. GCS 업로드 후 URL 발급
4. `generated_content.video_url` 업데이트
5. `selected_outputs.video`를 자동 채택으로 업데이트

권한:
- 현재는 `PRO` 티어 필요

---

## “CTR 순 정렬”의 의미(현 구현)
Create 화면에서 각 썸네일 후보에 대해 `/pipeline/analysis/ctr-predict`를 호출해 점수를 만든다.
- 우선 사용: `prediction.predicted_ctr`
- 없으면 폴백: `prediction.total_score`

권한/상태에 따라 예측이 실패하면(예: 403) 정렬 없이 원본 순서로 표시한다.

---

## 왜 이게 “유의미한 성과”인가
이 플로우는 “많이 만들기”에서 “좋아 보이는 1개를 빨리 고르기”로 결정을 압축한다.
- **정렬(CTR 예측)**은 후보를 탐색하는 시간을 줄인다.
- **채택(selected_outputs)**은 다음 단계가 흔들리지 않게 입력을 고정한다.
- **I2V 재생성**은 “선택한 썸네일의 메시지”를 그대로 비디오로 이어붙이는 연결 고리다.

