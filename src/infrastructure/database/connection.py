from __future__ import annotations

import os
from collections.abc import AsyncIterator
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///./data/auth.db")


def _ensure_sqlite_dir(database_url: str) -> None:
    if not database_url.startswith("sqlite+aiosqlite:///"):
        return
    raw_path = database_url.split("sqlite+aiosqlite:///", 1)[1]
    if not raw_path:
        return
    path = Path(raw_path).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)


_ensure_sqlite_dir(DATABASE_URL)

engine = create_async_engine(DATABASE_URL, echo=False, future=True)
AsyncSessionFactory = async_sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)


async def get_db_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionFactory() as session:
        yield session


def _is_postgresql() -> bool:
    """현재 데이터베이스가 PostgreSQL인지 확인"""
    return DATABASE_URL.startswith("postgresql")


def _migrate_users_columns(sync_conn):
    """기존 users 테이블에 role/role_id/team_id 컬럼이 없으면 추가 (스키마 이전 대응).

    Note: SQLite 전용 마이그레이션. PostgreSQL에서는 건너뜁니다.
    """
    # PostgreSQL에서는 이 마이그레이션을 건너뜀 (Alembic 사용 권장)
    if _is_postgresql():
        return

    try:
        result = sync_conn.execute(text("PRAGMA table_info(users)"))
        rows = result.fetchall()
    except Exception:
        return
    # SQLite table_info: (cid, name, type, notnull, dflt_value, pk)
    names = [row[1] for row in rows] if rows else []
    if "role" not in names:
        sync_conn.execute(
            text("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'editor' NOT NULL")
        )
    if "role_id" not in names:
        sync_conn.execute(
            text("ALTER TABLE users ADD COLUMN role_id INTEGER REFERENCES roles(id)")
        )
    if "team_id" not in names:
        sync_conn.execute(
            text("ALTER TABLE users ADD COLUMN team_id INTEGER REFERENCES teams(id)")
        )
    if "phone_number" not in names:
        sync_conn.execute(text("ALTER TABLE users ADD COLUMN phone_number TEXT"))
    if "job_title" not in names:
        sync_conn.execute(text("ALTER TABLE users ADD COLUMN job_title TEXT"))
    # Stripe 구독 관련 컬럼
    if "stripe_customer_id" not in names:
        sync_conn.execute(
            text("ALTER TABLE users ADD COLUMN stripe_customer_id TEXT")
        )
        # SQLite는 ALTER TABLE ADD COLUMN에서 UNIQUE를 지원하지 않으므로 인덱스로 대체
        sync_conn.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_users_stripe_customer_id "
                "ON users (stripe_customer_id)"
            )
        )
    if "tier" not in names:
        sync_conn.execute(
            text("ALTER TABLE users ADD COLUMN tier TEXT DEFAULT 'FREE' NOT NULL")
        )
    if "subscription_status" not in names:
        sync_conn.execute(
            text(
                "ALTER TABLE users ADD COLUMN subscription_status TEXT DEFAULT 'none' NOT NULL"
            )
        )
    if "subscription_end_date" not in names:
        sync_conn.execute(
            text("ALTER TABLE users ADD COLUMN subscription_end_date TEXT")
        )


async def _seed_initial_data(async_conn):
    """기본 역할(role) 데이터를 삽입합니다."""
    from datetime import datetime, timedelta, timezone

    roles = [
        ("admin", "System Administrator with full access"),
        ("editor", "Content Editor with create/edit access"),
        ("viewer", "Read-only access to analytics and assets"),
    ]

    # PostgreSQL과 SQLite에서 다른 구문 사용
    if _is_postgresql():
        # PostgreSQL: ON CONFLICT DO NOTHING
        sql = text(
            "INSERT INTO roles (name, description, created_at) "
            "VALUES (:name, :desc, :now) "
            "ON CONFLICT (name) DO NOTHING"
        )
    else:
        # SQLite: INSERT OR IGNORE
        sql = text(
            "INSERT OR IGNORE INTO roles (name, description, created_at) "
            "VALUES (:name, :desc, :now)"
        )

    for name, desc in roles:
        await async_conn.execute(
            sql,
            {
                "name": name,
                "desc": desc,
                "now": datetime.now(timezone(timedelta(hours=9))),
            },
        )


async def init_db() -> None:
    from infrastructure.database.models import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_migrate_users_columns)
        # 기본 데이터 시딩 (Async로 실행)
        await _seed_initial_data(conn)
