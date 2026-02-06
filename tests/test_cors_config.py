from __future__ import annotations

from config.cors import resolve_cors_origins


def test_resolve_cors_origins_cloud_run_defaults_to_wildcard_when_missing() -> None:
    assert resolve_cors_origins(None, is_cloud_run=True) == ["*"]


def test_resolve_cors_origins_cloud_run_defaults_to_wildcard_when_empty() -> None:
    assert resolve_cors_origins("", is_cloud_run=True) == ["*"]
    assert resolve_cors_origins("   ", is_cloud_run=True) == ["*"]
    assert resolve_cors_origins(",", is_cloud_run=True) == ["*"]


def test_resolve_cors_origins_local_defaults_to_localhost_when_missing() -> None:
    assert resolve_cors_origins(None, is_cloud_run=False) == ["http://localhost:3000"]


def test_resolve_cors_origins_parses_comma_separated_list() -> None:
    assert resolve_cors_origins(
        "https://a.example, https://b.example",
        is_cloud_run=False,
    ) == ["https://a.example", "https://b.example"]

