import os

from infrastructure.database.connection import _postgres_engine_kwargs_for_env


def test_postgres_engine_kwargs_defaults(monkeypatch):
    monkeypatch.delenv("DB_POOL_SIZE", raising=False)
    monkeypatch.delenv("DB_MAX_OVERFLOW", raising=False)
    monkeypatch.delenv("DB_POOL_TIMEOUT", raising=False)
    monkeypatch.delenv("DB_CONNECT_TIMEOUT", raising=False)

    kwargs = _postgres_engine_kwargs_for_env(os.environ)
    assert kwargs["pool_size"] == 5
    assert kwargs["max_overflow"] == 2
    assert kwargs["pool_timeout"] == 10
    assert kwargs["connect_args"]["timeout"] == 10


def test_postgres_engine_kwargs_env_override(monkeypatch):
    monkeypatch.setenv("DB_POOL_SIZE", "7")
    monkeypatch.setenv("DB_MAX_OVERFLOW", "3")
    monkeypatch.setenv("DB_POOL_TIMEOUT", "4")
    monkeypatch.setenv("DB_CONNECT_TIMEOUT", "6")

    kwargs = _postgres_engine_kwargs_for_env(os.environ)
    assert kwargs["pool_size"] == 7
    assert kwargs["max_overflow"] == 3
    assert kwargs["pool_timeout"] == 4
    assert kwargs["connect_args"]["timeout"] == 6

