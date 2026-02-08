"""Add tier, subscription_status, subscription_end_date to users

Revision ID: f1f6g7h8i9j0
Revises: e0e5f6g7h8i9
Create Date: 2026-02-08 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f1f6g7h8i9j0"
down_revision: Union[str, None] = "e0e5f6g7h8i9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    columns = [c["name"] for c in insp.get_columns("users")]

    if "tier" not in columns:
        op.add_column(
            "users",
            sa.Column(
                "tier",
                sa.String(20),
                nullable=False,
                server_default="FREE",
            ),
        )
    if "subscription_status" not in columns:
        op.add_column(
            "users",
            sa.Column(
                "subscription_status",
                sa.String(20),
                nullable=False,
                server_default="none",
            ),
        )
    if "subscription_end_date" not in columns:
        op.add_column(
            "users",
            sa.Column(
                "subscription_end_date",
                sa.DateTime(timezone=True),
                nullable=True,
            ),
        )


def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    columns = [c["name"] for c in insp.get_columns("users")]
    if "subscription_end_date" in columns:
        op.drop_column("users", "subscription_end_date")
    if "subscription_status" in columns:
        op.drop_column("users", "subscription_status")
    if "tier" in columns:
        op.drop_column("users", "tier")
