"""add model_eval_reports table

Revision ID: j5k6l7m8n9p0
Revises: i4j5k6l7m8n9
Create Date: 2026-02-10

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "j5k6l7m8n9p0"
down_revision: Union[str, Sequence[str], None] = "i4j5k6l7m8n9"
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
    if not _table_exists("model_eval_reports"):
        op.create_table(
            "model_eval_reports",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
            sa.Column("report_type", sa.String(length=50), nullable=False),
            sa.Column("report_date", sa.Date(), nullable=False),
            sa.Column("dataset_counts_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("cls_metrics_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("reg_metrics_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("baseline_metrics_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("artifact_gcs_path", sa.String(length=500), nullable=True),
            sa.Column("notion_url", sa.String(length=500), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )

    if not _index_exists("model_eval_reports", "ix_model_eval_reports_report_type"):
        op.create_index(
            "ix_model_eval_reports_report_type",
            "model_eval_reports",
            ["report_type"],
            unique=False,
        )
    if not _index_exists("model_eval_reports", "ix_model_eval_reports_report_date"):
        op.create_index(
            "ix_model_eval_reports_report_date",
            "model_eval_reports",
            ["report_date"],
            unique=False,
        )


def downgrade() -> None:
    op.drop_index("ix_model_eval_reports_report_date", table_name="model_eval_reports")
    op.drop_index("ix_model_eval_reports_report_type", table_name="model_eval_reports")
    op.drop_table("model_eval_reports")

