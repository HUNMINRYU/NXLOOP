"""
관리자 모델 평가 API 테스트 (POST /api/v1/admin/evaluate-model/*)

admin 권한으로 evaluate-model 엔드포인트 응답 스키마 검증.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def admin_user():
    """admin 역할 mock user"""
    user = MagicMock()
    user.email = "admin@example.com"
    user.role = "admin"
    user.name = "Admin"
    user.tier = "FREE"
    user.subscription_status = "none"
    return user


@pytest.fixture
def client_admin(admin_user):
    """TestClient with get_current_user overridden to admin (auth 테스트와 동일하게 deps 사용처 기준 패치)."""
    with patch("infrastructure.database.connection.init_db", new_callable=AsyncMock):
        from app import app
        from api.deps import get_current_user
        from infrastructure.database.connection import get_db_session

        mock_db = AsyncMock()

        async def override_get_db_session():
            return mock_db

        async def override_get_current_user():
            return admin_user

        app.dependency_overrides[get_db_session] = override_get_db_session
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            yield TestClient(app, raise_server_exceptions=False)
        finally:
            app.dependency_overrides.clear()


def test_evaluate_model_predictions_returns_metrics(client_admin):
    """POST /api/v1/admin/evaluate-model/predictions 응답에 mae, rmse 등 포함"""
    response = client_admin.post(
        "/api/v1/admin/evaluate-model/predictions",
        json={
            "predictions": [1.0, 2.0, 3.0],
            "actuals": [1.1, 2.1, 2.9],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "mae" in data
    assert "rmse" in data
    assert "mape" in data
    assert "r_squared" in data
    assert data["sample_count"] == 3
