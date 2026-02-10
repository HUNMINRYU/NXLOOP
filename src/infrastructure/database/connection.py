from __future__ import annotations

import os
from collections.abc import AsyncIterator
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///./data/auth.db")


def _is_postgresql() -> bool:
    """현재 데이터베이스가 PostgreSQL인지 확인"""
    return DATABASE_URL.startswith("postgresql")

def _env_int(env: "os._Environ[str]", key: str, default: int) -> int:
    raw = (env.get(key) or "").strip()
    if not raw:
        return int(default)
    try:
        return int(raw)
    except Exception:
        return int(default)


def _postgres_engine_kwargs_for_env(env: "os._Environ[str]") -> dict[str, object]:
    """Cloud Run + Cloud SQL(Postgres) 운영을 위한 엔진 kwargs.

    db-f1-micro 같은 작은 인스턴스에서 커넥션 폭주를 막기 위해
    기본 풀 크기를 보수적으로 잡고(override 가능), 장애 시 빠르게 실패하도록 timeout을 둔다.
    """
    pool_size = _env_int(env, "DB_POOL_SIZE", 5)
    max_overflow = _env_int(env, "DB_MAX_OVERFLOW", 2)
    pool_timeout = _env_int(env, "DB_POOL_TIMEOUT", 10)
    connect_timeout = _env_int(env, "DB_CONNECT_TIMEOUT", 10)

    return {
        "pool_size": pool_size,
        "max_overflow": max_overflow,
        "pool_timeout": pool_timeout,
        "pool_recycle": 3600,  # Cloud SQL 권장
        "pool_pre_ping": True,
        "connect_args": {"timeout": connect_timeout},
    }



def _ensure_sqlite_dir(database_url: str) -> None:
    if not database_url.startswith("sqlite+aiosqlite:///"):
        return
    raw_path = database_url.split("sqlite+aiosqlite:///", 1)[1]
    if not raw_path:
        return
    path = Path(raw_path).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)


_ensure_sqlite_dir(DATABASE_URL)

# 운영 환경(PostgreSQL) 최적화를 위한 엔진 설정
if _is_postgresql():
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        future=True,
        # NOTE: kwargs는 운영 환경에서 env로 조절 가능.
        **_postgres_engine_kwargs_for_env(os.environ),
    )
else:
    # SQLite 등 로컬 환경용 설정
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        future=True,
        connect_args={"timeout": 60} # 타임아웃을 1분으로 대폭 늘림
    )

    # SQLite WAL(Write-Ahead Logging) 모드는 WSL 환경에서 가끔 'database is locked' 충돌을 일으킬 수 있습니다.
    # 안정성을 최우선으로 하여 설정을 조정합니다.
    from sqlalchemy import event
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        # WAL 모드 대신 안정적인 DELETE 모드 사용 (WSL 파일 시스템 호환성)
        cursor.execute("PRAGMA journal_mode=DELETE")
        cursor.execute("PRAGMA synchronous=FULL")
        # 내부적인 바쁜 대기 시간 설정 (ms)
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()

AsyncSessionFactory = async_sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)


async def get_db_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionFactory() as session:
        yield session




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
        # 운영(PostgreSQL)에서는 스키마 생성/시딩을 앱 프로세스에서 수행하지 않습니다.
        # Cloud Run 환경에서는 동시 기동 경쟁과 콜드스타트 지연을 유발할 수 있고,
        # 마이그레이션은 Alembic(배포 단계)로 관리하는 편이 안전합니다.
        if _is_postgresql():
            await conn.execute(text("SELECT 1"))
            return
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_migrate_users_columns)
        # 기본 데이터 시딩 (Async로 실행)
        await _seed_initial_data(conn)
