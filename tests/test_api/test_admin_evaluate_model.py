"""
관리자 모델 평가 엔드포인트 로직 테스트

주의: 이 리포지토리 환경에서는 Starlette/FastAPI TestClient가 간헐적으로 hang 될 수 있어
라우트 함수를 직접 호출해 응답 스키마를 검증합니다.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from api.v1.endpoints.admin import (
    EvaluatePredictionsRequest,
    evaluate_model_predictions,
)


@pytest.mark.asyncio
async def test_evaluate_model_predictions_returns_metrics():
    admin_user = MagicMock()
    admin_user.role = "admin"

    req = EvaluatePredictionsRequest(
        predictions=[1.0, 2.0, 3.0],
        actuals=[1.1, 2.1, 2.9],
    )
    data = await evaluate_model_predictions(req, user=admin_user)
    assert "mae" in data
    assert "rmse" in data
    assert "mape" in data
    assert "r_squared" in data
    assert data["sample_count"] == 3
