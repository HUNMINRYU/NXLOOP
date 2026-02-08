"""
Auth API 엔드포인트 테스트

FastAPI dependency_overrides를 사용하여 DB/서비스 의존성을 mock 처리
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def mock_services():
    """서비스 계층 mock"""
    services = MagicMock()

    # mock user 객체
    mock_user = MagicMock()
    mock_user.email = "test@example.com"
    mock_user.role = "editor"
    mock_user.name = "테스터"
    mock_user.tier = "FREE"
    mock_user.subscription_status = "none"

    # mock session 객체
    mock_session = MagicMock()
    mock_session.id = "session-12345678-abcd"

    services.auth_service.signup = AsyncMock(return_value={"user": mock_user})
    services.auth_service.login = AsyncMock(return_value={"user": mock_user})
    services.auth_service.create_session = AsyncMock(return_value=mock_session)
    services.auth_service.new_csrf_token = MagicMock(return_value="csrf-token-abc")
    services.auth_service.delete_session = AsyncMock()
    services.auth_service.get_user_by_session_id = AsyncMock(return_value=mock_user)

    return services


@pytest.fixture
def client(mock_services):
    """TestClient with dependency overrides"""
    with patch("config.dependencies.get_services", return_value=mock_services):
        # DB 초기화를 건너뛰기 위해 lifespan을 override
        with patch("infrastructure.database.connection.init_db", new_callable=AsyncMock):
            from app import app
            from infrastructure.database.connection import get_db_session

            # FastAPI dependency override로 DB 세션 mock
            mock_db = AsyncMock()

            async def override_get_db_session():
                return mock_db

            app.dependency_overrides[get_db_session] = override_get_db_session

            try:
                yield TestClient(app, raise_server_exceptions=False)
            finally:
                app.dependency_overrides.clear()


class TestSignup:
    """회원가입 엔드포인트 테스트"""

    def test_signup_success(self, client):
        """정상 회원가입"""
        response = client.post(
            "/api/v1/auth/signup",
            json={
                "email": "test@example.com",
                "password": "password123",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"
        assert "role" in data
        assert "name" in data

    def test_signup_sets_cookies(self, client):
        """회원가입 시 세션/CSRF 쿠키 설정"""
        response = client.post(
            "/api/v1/auth/signup",
            json={
                "email": "test@example.com",
                "password": "password123",
            },
        )
        assert response.status_code == 200
        assert "nexloop_session" in response.cookies
        assert "nexloop_csrf" in response.cookies


class TestLogin:
    """로그인 엔드포인트 테스트"""

    def test_login_success(self, client):
        """정상 로그인"""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "password123",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"
        assert "role" in data
        assert "name" in data

    def test_login_returns_user_fields(self, client):
        """로그인 응답에 필수 필드 포함 확인"""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "password123",
            },
        )
        data = response.json()
        assert "email" in data
        assert "name" in data
        assert "role" in data


class TestLogout:
    """로그아웃 엔드포인트 테스트"""

    def test_logout_without_session(self, client):
        """세션 없이 로그아웃"""
        response = client.post("/api/v1/auth/logout")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data

    def test_logout_with_session(self, client):
        """세션이 있는 상태에서 로그아웃"""
        # 로그인 시 클라이언트에 세션/CSRF 쿠키가 자동 저장됨 (per-request cookies 미사용)
        client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "password123"},
        )
        response = client.post("/api/v1/auth/logout")
        assert response.status_code == 200


class TestMe:
    """현재 사용자 정보 엔드포인트 테스트"""

    def test_me_without_auth(self, client):
        """인증 없이 /me 접근 시 401"""
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401

    def test_me_with_session(self, client):
        """세션 쿠키로 /me 접근"""
        # 로그인 시 클라이언트에 세션/CSRF 쿠키가 자동 저장됨 (per-request cookies 미사용)
        client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "password123"},
        )
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"
        assert "role" in data
