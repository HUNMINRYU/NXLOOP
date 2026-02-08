"""Add user_daily_chat_usage table for FREE tier 10 messages/day

Revision ID: g2g3h4i5j6k7
Revises: b8c3d4e5f6g7
Create Date: 2026-02-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "g2g3h4i5j6k7"
down_revision: Union[str, None] = "b8c3d4e5f6g7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    tables = insp.get_table_names()
    if "user_daily_chat_usage" in tables:
        return
    op.create_table(
        "user_daily_chat_usage",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("usage_date", sa.Date(), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "usage_date", name="uq_user_daily_chat_usage"),
    )
    op.create_index(op.f("ix_user_daily_chat_usage_user_id"), "user_daily_chat_usage", ["user_id"], unique=False)
    op.create_index(op.f("ix_user_daily_chat_usage_usage_date"), "user_daily_chat_usage", ["usage_date"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_user_daily_chat_usage_usage_date"), table_name="user_daily_chat_usage")
    op.drop_index(op.f("ix_user_daily_chat_usage_user_id"), table_name="user_daily_chat_usage")
    op.drop_table("user_daily_chat_usage")
