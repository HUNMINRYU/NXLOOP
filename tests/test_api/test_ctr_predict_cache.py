"""
CTR 예측 엔드포인트 캐시/고정 동작 테스트.

주의: 이 리포지토리 환경에서는 Starlette/FastAPI TestClient가 간헐적으로 hang 될 수 있어
ASGI 레이어를 우회하고 엔드포인트 함수를 직접 호출해 검증합니다.
"""

from __future__ import annotations

import types

import pytest

import api.v1.endpoints.pipeline as pipeline_endpoint
from core.state import PIPELINE_RESULTS, PIPELINE_STATUS
from schemas.requests import CTRPredictRequest


class _DummyPipelineTaskService:
    def __init__(self) -> None:
        self.upsert_calls: list[tuple[str, dict]] = []

    async def upsert_result(self, task_id: str, result: dict) -> None:
        self.upsert_calls.append((task_id, result))


class _DummyCtrPredictor:
    def __init__(self) -> None:
        self.basic_calls = 0
        self.ai_calls = 0

    def predict_ctr(self, **kwargs):
        self.basic_calls += 1
        return {
            "predicted_ctr": 0.05,
            "grade": "B",
            "total_score": 80,
            "ctr_range": "3%~7%",
            "breakdown": {"title_quality": 40, "hook": 40},
        }

    async def predict_with_ai(self, **kwargs):
        self.ai_calls += 1
        return {"ai_rationale": "dummy"}


@pytest.mark.asyncio
async def test_ctr_predict_is_cached_and_persisted(monkeypatch):
    task_id = "task-test-ctr-cache"
    PIPELINE_STATUS[task_id] = {"task_id": task_id, "status": "running"}
    PIPELINE_RESULTS[task_id] = {"task_id": task_id, "collected_data": {"top_insights": ["a"]}}

    predictor = _DummyCtrPredictor()
    pipeline_task_service = _DummyPipelineTaskService()

    mock_services = types.SimpleNamespace(
        ctr_predictor=predictor,
        pipeline_task_service=pipeline_task_service,
    )
    monkeypatch.setattr(pipeline_endpoint, "get_services", lambda: mock_services)

    try:
        req = CTRPredictRequest(
            task_id=task_id,
            title="hello",
            thumbnail_description="thumb",
            competitor_titles=["c1", "c2"],
        )

        first = await pipeline_endpoint.predict_ctr(req, user=None)  # type: ignore[arg-type]
        assert first["cache"]["hit"] is False
        assert predictor.basic_calls == 1
        assert predictor.ai_calls == 1
        assert pipeline_task_service.upsert_calls

        second = await pipeline_endpoint.predict_ctr(req, user=None)  # type: ignore[arg-type]
        assert second["cache"]["hit"] is True
        assert predictor.basic_calls == 1
        assert predictor.ai_calls == 1
        assert second["prediction"]["predicted_ctr"] == first["prediction"]["predicted_ctr"]
    finally:
        PIPELINE_STATUS.pop(task_id, None)
        PIPELINE_RESULTS.pop(task_id, None)

