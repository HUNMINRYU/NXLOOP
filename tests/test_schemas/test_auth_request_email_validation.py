import pytest
from pydantic import ValidationError

from schemas.requests import AuthLoginRequest, AuthSignupRequest


def test_auth_signup_request_rejects_invalid_email():
    with pytest.raises(ValidationError):
        AuthSignupRequest(
            email="asdf@asdf@asdf",
            password="secret123",
        )


def test_auth_login_request_rejects_invalid_email():
    with pytest.raises(ValidationError):
        AuthLoginRequest(
            email="asdf@asdf@asdf",
            password="secret123",
        )
