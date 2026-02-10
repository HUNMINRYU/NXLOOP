"""
Pipeline status 엔드포인트의 [FEATURE] 로깅 throttle 동작을 최소 단위로 검증한다.

주의: 이 리포지토리 환경에서는 Starlette/FastAPI TestClient가 간헐적으로 hang 될 수 있어
ASGI 레이어를 우회하고 엔드포인트 함수를 직접 호출해 검증합니다.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from api.v1.endpoints.pipeline import get_pipeline_status
from core.state import PIPELINE_STATUS


@pytest.mark.asyncio
async def test_pipeline_status_throttle_skips_start_end_but_not_fail():
    task_id = "task-test-throttle-routing-miss"

    with (
        # 1) pipeline_status start/end -> False (skip)
        # 2) routing_miss fail log -> True (emit once)
        patch(
            "api.v1.endpoints.pipeline.should_log_throttled",
            side_effect=[False, True],
        ),
        patch("api.v1.endpoints.pipeline.log_feature_start") as start,
        patch("api.v1.endpoints.pipeline.log_feature_end") as end,
        patch("api.v1.endpoints.pipeline.log_feature_fail") as fail,
        patch(
            "api.v1.endpoints.pipeline.get_services",
            return_value=SimpleNamespace(pipeline_task_service=None),
        ),
    ):
        resp = await get_pipeline_status(task_id)

    assert resp["task_id"] == task_id
    start.assert_not_called()
    end.assert_not_called()
    fail.assert_called_once()


@pytest.mark.asyncio
async def test_pipeline_status_throttle_can_skip_routing_miss_fail_when_throttled():
    task_id = "task-test-throttle-routing-miss-skip-fail"

    with (
        # 1) pipeline_status start/end -> False (skip)
        # 2) routing_miss fail log -> False (throttled)
        patch(
            "api.v1.endpoints.pipeline.should_log_throttled",
            side_effect=[False, False],
        ),
        patch("api.v1.endpoints.pipeline.log_feature_start") as start,
        patch("api.v1.endpoints.pipeline.log_feature_end") as end,
        patch("api.v1.endpoints.pipeline.log_feature_fail") as fail,
        patch(
            "api.v1.endpoints.pipeline.get_services",
            return_value=SimpleNamespace(pipeline_task_service=None),
        ),
    ):
        resp = await get_pipeline_status(task_id)

    assert resp["task_id"] == task_id
    start.assert_not_called()
    end.assert_not_called()
    fail.assert_not_called()


@pytest.mark.asyncio
async def test_pipeline_status_throttle_allows_start_end_when_should_log_true():
    task_id = "task-test-throttle-allowed"
    PIPELINE_STATUS[task_id] = {
        "task_id": task_id,
        "status": "running",
        "message": "테스트",
        "progress": {"percentage": 1, "message": "시작", "step": "start"},
        "process_logs": [],
    }

    try:
        with (
            patch("api.v1.endpoints.pipeline.should_log_throttled", return_value=True),
            patch("api.v1.endpoints.pipeline.log_feature_start") as start,
            patch("api.v1.endpoints.pipeline.log_feature_end") as end,
            patch("api.v1.endpoints.pipeline.log_feature_fail") as fail,
        ):
            resp = await get_pipeline_status(task_id)

        assert resp["task_id"] == task_id
        start.assert_called_once_with("pipeline_status", task_id)
        end.assert_called_once_with("pipeline_status", extra_detail="")
        fail.assert_not_called()
    finally:
        PIPELINE_STATUS.pop(task_id, None)
