"""add pipeline_tasks table

Revision ID: i4j5k6l7m8n9
Revises: a2280298719c
Create Date: 2026-02-10

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "i4j5k6l7m8n9"
down_revision: Union[str, Sequence[str], None] = "a2280298719c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(name: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    return name in insp.get_table_names()


def _index_exists(table_name: str, index_name: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    return any(ix.get("name") == index_name for ix in insp.get_indexes(table_name))


def upgrade() -> None:
    # Cloud Run Job 기반 마이그레이션은 같은 revision이 여러 번 실행될 수 있어
    # DDL을 idempotent하게 방어합니다.
    if not _table_exists("pipeline_tasks"):
        op.create_table(
            "pipeline_tasks",
            sa.Column("task_id", sa.String(length=36), primary_key=True),
            sa.Column("product_name", sa.String(length=100), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False),
            sa.Column("message", sa.String(length=500), nullable=False, server_default=""),
            sa.Column("status_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("result_json", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )

    if not _index_exists("pipeline_tasks", "ix_pipeline_tasks_product_name"):
        op.create_index(
            "ix_pipeline_tasks_product_name",
            "pipeline_tasks",
            ["product_name"],
            unique=False,
        )
    if not _index_exists("pipeline_tasks", "ix_pipeline_tasks_status"):
        op.create_index("ix_pipeline_tasks_status", "pipeline_tasks", ["status"], unique=False)
    if not _index_exists("pipeline_tasks", "ix_pipeline_tasks_created_at"):
        op.create_index(
            "ix_pipeline_tasks_created_at",
            "pipeline_tasks",
            ["created_at"],
            unique=False,
        )
    if not _index_exists("pipeline_tasks", "ix_pipeline_tasks_updated_at"):
        op.create_index(
            "ix_pipeline_tasks_updated_at",
            "pipeline_tasks",
            ["updated_at"],
            unique=False,
        )


def downgrade() -> None:
    op.drop_index("ix_pipeline_tasks_updated_at", table_name="pipeline_tasks")
    op.drop_index("ix_pipeline_tasks_created_at", table_name="pipeline_tasks")
    op.drop_index("ix_pipeline_tasks_status", table_name="pipeline_tasks")
    op.drop_index("ix_pipeline_tasks_product_name", table_name="pipeline_tasks")
    op.drop_table("pipeline_tasks")
