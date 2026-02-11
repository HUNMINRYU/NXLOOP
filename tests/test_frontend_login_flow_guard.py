from pathlib import Path


LOGIN_PAGE = Path("frontend/src/app/login/page.tsx")


def _read() -> str:
    return LOGIN_PAGE.read_text(encoding="utf-8")


def test_login_uses_fetchme_fallback_to_login_response() -> None:
    source = _read()
    assert "const loginResult = await login" in source
    assert "me = await fetchMe()" in source
    assert "fetchMe fallback to login response" in source


def test_login_button_is_single_submit_path() -> None:
    source = _read()
    assert 'type="submit"' in source
    assert "onClick={handleLogin}" not in source
