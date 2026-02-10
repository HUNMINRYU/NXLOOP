"""
Pipeline status-stream(SSE) 엔드포인트의 최소 동작 보장 테스트.

주의: 이 리포지토리 환경에서는 Starlette/FastAPI TestClient가 간헐적으로 hang 될 수 있어
ASGI 레이어를 우회하고 엔드포인트 함수를 직접 호출해 검증합니다.
"""

from __future__ import annotations

import json

import pytest

import api.v1.endpoints.pipeline as pipeline_endpoint
from core.state import PIPELINE_STATUS


@pytest.mark.asyncio
async def test_status_stream_yields_json_without_nameerror():
    task_id = "task-test-status-stream"
    PIPELINE_STATUS[task_id] = {
        "task_id": task_id,
        "status": "running",
        "message": "테스트",
        "progress": {"percentage": 1, "message": "시작", "step": "start"},
        # datetime 같은 비직렬화 값이 섞여도 PipelineTask.dumps가 방어해야 하지만,
        # 이 테스트는 우선 NameError(미임포트) 회귀를 막는 목적이다.
        "process_logs": [],
    }

    try:
        # PipelineTask 모델이 임포트되지 못하는 배포/환경에서도 SSE가 깨지지 않아야 한다.
        prev_model = getattr(pipeline_endpoint, "_PipelineTaskModel", None)
        pipeline_endpoint._PipelineTaskModel = None

        resp = await pipeline_endpoint.stream_pipeline_status(task_id)
        chunk = await anext(resp.body_iterator)

        # Starlette가 str을 bytes로 인코딩할 수 있으므로 양쪽 대응
        if isinstance(chunk, bytes):
            text = chunk.decode("utf-8", errors="replace")
        else:
            text = str(chunk)

        assert text.startswith("data: ")
        payload = text.removeprefix("data: ").strip()
        payload = payload.removesuffix("\n\n").strip()
        data = json.loads(payload)
        assert data["task_id"] == task_id
        assert data["status"] == "running"
    finally:
        pipeline_endpoint._PipelineTaskModel = prev_model
        PIPELINE_STATUS.pop(task_id, None)
