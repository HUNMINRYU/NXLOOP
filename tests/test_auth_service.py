from services.auth_service import AuthService


def test_password_hash_roundtrip():
    service = AuthService()
    hashed = service.hash_password("password123")
    assert service.verify_password("password123", hashed)
