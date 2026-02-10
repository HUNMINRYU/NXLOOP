"""
파이프라인 오케스트레이터 테스트 - 성능 메트릭 수집 검증
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from services.pipeline.orchestrator import PipelineOrchestrator
from services.pipeline.types import (
    AuthorInfo,
    Candidate,
    CandidateFeatures,
    CandidateScore,
)


def _make_candidate(content: str = "테스트 댓글 내용입니다") -> Candidate:
    """테스트용 Candidate 생성"""
    from datetime import datetime

    return Candidate(
        id="test-1",
        content=content,
        title="테스트",
        author=AuthorInfo(username="tester"),
        created_at=datetime.now(),
        like_count=0,
        category="general",
        features=CandidateFeatures(),
        score=CandidateScore(raw_score=5.0),
    )


def _make_mock_orchestrator(
    source_output: list[Candidate] | None = None,
    hydration_output: list[Candidate] | None = None,
    scoring_output: list[Candidate] | None = None,
) -> PipelineOrchestrator:
    """Mock 의존성으로 오케스트레이터 생성"""
    candidates = source_output or [_make_candidate(), _make_candidate("다른 댓글 내용입니다")]

    source = MagicMock()
    source.item_to_candidate = AsyncMock(return_value=candidates)

    hydrator = MagicMock()
    hydrator.hydrate = AsyncMock(
        return_value=hydration_output or candidates
    )

    quality_filter = MagicMock()
    quality_filter.filter = MagicMock(side_effect=lambda c: c)

    scorer = MagicMock()
    scorer.score = AsyncMock(
        return_value=scoring_output or candidates
    )

    diversity_scorer = MagicMock()
    diversity_scorer.apply = MagicMock(side_effect=lambda c, _: c)

    selector = MagicMock()
    selector.select = MagicMock(side_effect=lambda c, top_k: c[:top_k])
    selector.format_for_response = MagicMock(
        return_value=[{"id": "test-1", "content": "테스트"}]
    )

    return PipelineOrchestrator(
        source=source,
        hydrator=hydrator,
        quality_filter=quality_filter,
        scorer=scorer,
        diversity_scorer=diversity_scorer,
        selector=selector,
    )


@pytest.mark.asyncio
async def test_pipeline_returns_stage_timings():
    """파이프라인이 단계별 소요 시간을 반환하는지 확인"""
    orchestrator = _make_mock_orchestrator()
    result = await orchestrator.run_pipeline([{"text": "테스트"}])

    stats = result["stats"]
    assert "stage_timings" in stats

    timings = stats["stage_timings"]
    expected_stages = ["source", "pre_filter", "hydration", "post_filter", "scoring", "diversity", "selection"]
    for stage in expected_stages:
        assert stage in timings
        assert isinstance(timings[stage], float)
        assert timings[stage] >= 0


@pytest.mark.asyncio
async def test_pipeline_returns_stage_counts():
    """파이프라인이 단계별 처리 건수를 반환하는지 확인"""
    orchestrator = _make_mock_orchestrator()
    result = await orchestrator.run_pipeline([{"text": "테스트"}])

    stats = result["stats"]
    assert "stage_counts" in stats

    counts = stats["stage_counts"]
    assert "source" in counts
    assert "input" in counts["source"]
    assert "output" in counts["source"]


@pytest.mark.asyncio
async def test_pipeline_returns_total_duration():
    """전체 소요 시간 반환 확인"""
    orchestrator = _make_mock_orchestrator()
    result = await orchestrator.run_pipeline([{"text": "테스트"}])

    stats = result["stats"]
    assert "total_duration" in stats
    assert stats["total_duration"] >= 0


@pytest.mark.asyncio
async def test_pipeline_returns_filtering_rate():
    """필터링률 반환 확인"""
    orchestrator = _make_mock_orchestrator()
    result = await orchestrator.run_pipeline([{"text": "테스트"}])

    stats = result["stats"]
    assert "filtering_rate" in stats
    assert 0.0 <= stats["filtering_rate"] <= 1.0
    # 하위 호환: removed_rate는 filtering_rate와 동일 의미(제거율)
    assert "removed_rate" in stats
    assert stats["removed_rate"] == stats["filtering_rate"]

    # 혼동 방지 지표: 선정률/축소율
    assert "selection_rate_of_original" in stats
    assert "selection_rate_of_filtered" in stats
    assert "reduction_rate_of_original" in stats
    assert 0.0 <= stats["selection_rate_of_original"] <= 1.0
    assert 0.0 <= stats["selection_rate_of_filtered"] <= 1.0
    assert 0.0 <= stats["reduction_rate_of_original"] <= 1.0


@pytest.mark.asyncio
async def test_pipeline_returns_throughput_or_zero_duration():
    """처리량 또는 0초 소요 시 throughput 미포함 확인"""
    orchestrator = _make_mock_orchestrator()
    result = await orchestrator.run_pipeline([{"text": "테스트"}])

    stats = result["stats"]
    # Mock이 즉시 실행되면 total_duration=0.0이므로 throughput_per_sec 미포함 가능
    if stats["total_duration"] > 0:
        assert "throughput_per_sec" in stats
        assert stats["throughput_per_sec"] > 0
    else:
        # duration이 0이면 throughput은 생략됨
        assert stats["total_duration"] == 0.0


@pytest.mark.asyncio
async def test_pipeline_empty_data():
    """빈 데이터 입력 시 정상 처리"""
    orchestrator = _make_mock_orchestrator(source_output=[])
    orchestrator.source.item_to_candidate = AsyncMock(return_value=[])
    # filter가 빈 리스트를 반환하도록 설정
    orchestrator.filter.filter = MagicMock(return_value=[])

    result = await orchestrator.run_pipeline([])

    assert result["insights"] == []
    assert "분석 가능한 데이터가 없습니다" in result["summary"]
    assert "stage_timings" in result["stats"]


@pytest.mark.asyncio
async def test_pipeline_stage_error_uses_backup():
    """단계 에러 시 backup 사용하고 계속 진행"""
    orchestrator = _make_mock_orchestrator()

    # scoring 단계에서 에러 발생시키기
    orchestrator.scorer.score = AsyncMock(side_effect=RuntimeError("테스트 에러"))

    result = await orchestrator.run_pipeline([{"text": "테스트"}])

    # 에러에도 불구하고 결과 반환 (backup 사용)
    assert "stats" in result
    assert "stage_timings" in result["stats"]
