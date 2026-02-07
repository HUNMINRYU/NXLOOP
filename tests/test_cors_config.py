from __future__ import annotations

from config.cors import resolve_cors_origins


def test_resolve_cors_origins_cloud_run_defaults_to_wildcard_when_missing() -> None:
    # 세션 쿠키 인증을 쓰는 서비스에서는 allow_credentials=True가 기본이므로
    # Cloud Run에서도 wildcard(*) fallback은 안전하지 않다.
    # 운영 환경에서는 CORS_ORIGINS를 명시하도록 로컬 기본값으로 fallback 한다.
    assert resolve_cors_origins(None, is_cloud_run=True) == ["http://localhost:3000"]


def test_resolve_cors_origins_cloud_run_defaults_to_wildcard_when_empty() -> None:
    assert resolve_cors_origins("", is_cloud_run=True) == ["http://localhost:3000"]
    assert resolve_cors_origins("   ", is_cloud_run=True) == ["http://localhost:3000"]
    assert resolve_cors_origins(",", is_cloud_run=True) == ["http://localhost:3000"]


def test_resolve_cors_origins_local_defaults_to_localhost_when_missing() -> None:
    assert resolve_cors_origins(None, is_cloud_run=False) == ["http://localhost:3000"]


def test_resolve_cors_origins_parses_comma_separated_list() -> None:
    assert resolve_cors_origins(
        "https://a.example, https://b.example",
        is_cloud_run=False,
    ) == ["https://a.example", "https://b.example"]
