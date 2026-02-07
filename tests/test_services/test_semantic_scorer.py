from __future__ import annotations

from datetime import datetime

import pytest

from services.pipeline.stages.scorer import SemanticScorer
from services.pipeline.types import AuthorInfo, Candidate
from utils.logger import add_log_callback, clear_log_callbacks


class _FakeGemini:
    def __init__(self, response_text: str) -> None:
        self._response_text = response_text

    async def generate_content_async(self, prompt: str) -> str:  # noqa: ARG002
        return self._response_text


def _candidate(content: str = "hello world") -> Candidate:
    return Candidate(
        id="c1",
        title="t",
        content=content,
        author=AuthorInfo(username="u1"),
        created_at=datetime.now(),
        like_count=0,
        category="general",
    )


@pytest.mark.asyncio
async def test_semantic_scorer_computes_final_score_and_marks_slop():
    # 0.8*0.5 + 0.6*0.3 + 0.4*0.2 = 0.66  -> slop
    gemini = _FakeGemini('{"p_dwell": 0.8, "p_share": 0.6, "p_action": 0.4}')
    scorer = SemanticScorer(gemini)  # type: ignore[arg-type]

    logs: list[str] = []
    clear_log_callbacks()
    add_log_callback(logs.append)

    cand = _candidate("some content")
    scored = await scorer.score([cand])

    assert scored[0].score.final_score == pytest.approx(0.66, abs=1e-4)
    assert scored[0].is_slop is True
    assert "p_dwell" in scored[0].metadata.get("semantic_probabilities", {})

    # 콜백 핸들러로 수집한 로그에 확률/score/is_slop 정보가 포함되는지 확인
    joined = "\n".join(logs)
    assert "SemanticScorer result" in joined
    assert "p_dwell=0.8000" in joined
    assert "p_share=0.6000" in joined
    assert "p_action=0.4000" in joined
    assert "is_slop=True" in joined


@pytest.mark.asyncio
async def test_semantic_scorer_not_slop_when_score_high_enough():
    gemini = _FakeGemini('{"p_dwell": 0.9, "p_share": 0.9, "p_action": 0.9}')
    scorer = SemanticScorer(gemini)  # type: ignore[arg-type]

    cand = _candidate("great content")
    scored = await scorer.score([cand])

    assert scored[0].score.final_score == pytest.approx(0.9, abs=1e-4)
    assert scored[0].is_slop is False


@pytest.mark.asyncio
async def test_semantic_scorer_clamps_out_of_range_probs():
    gemini = _FakeGemini('{"p_dwell": 2, "p_share": -1, "p_action": "0.5"}')
    scorer = SemanticScorer(gemini)  # type: ignore[arg-type]

    cand = _candidate("edge content")
    scored = await scorer.score([cand])

    # clamp: dwell=1.0, share=0.0, action=0.5 -> 0.5 + 0.0 + 0.1 = 0.6
    assert scored[0].score.final_score == pytest.approx(0.6, abs=1e-4)
    assert scored[0].is_slop is True
