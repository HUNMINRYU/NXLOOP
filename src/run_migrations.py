from __future__ import annotations

import os

from alembic.config import Config

from alembic import command
from utils.logger import (
    get_logger,
    log_feature_end,
    log_feature_fail,
    log_feature_start,
)

logger = get_logger(__name__)


def _normalize_db_url(url: str) -> str:
    # Alembic은 동기 드라이버를 사용하므로 async 드라이버 표기를 제거한다.
    return (url or "").replace("+aiosqlite", "").replace("+asyncpg", "").strip()


def main() -> None:
    log_feature_start("db_migrate", "alembic upgrade head")
    try:
        db_url = _normalize_db_url(os.environ.get("DATABASE_URL", ""))
        if not db_url:
            raise RuntimeError("DATABASE_URL is not set")

        alembic_cfg = Config("alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", db_url)
        command.upgrade(alembic_cfg, "head")

        log_feature_end("db_migrate")
    except Exception as e:
        log_feature_fail("db_migrate", str(e))
        # Cloud Run Job에서 실패를 확실히 감지하도록 예외를 다시 올린다.
        raise


if __name__ == "__main__":
    main()

