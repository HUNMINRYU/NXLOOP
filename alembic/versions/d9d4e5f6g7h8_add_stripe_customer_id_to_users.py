"""Add stripe_customer_id to users

Revision ID: d9d4e5f6g7h8
Revises: b8c3d4e5f6g7
Create Date: 2026-02-08 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d9d4e5f6g7h8"
down_revision: Union[str, None] = "b8c3d4e5f6g7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    columns = [c["name"] for c in insp.get_columns("users")]
    if "stripe_customer_id" not in columns:
        op.add_column(
            "users",
            sa.Column("stripe_customer_id", sa.String(255), nullable=True),
        )
        op.create_index(
            "ix_users_stripe_customer_id",
            "users",
            ["stripe_customer_id"],
            unique=True,
        )


def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    columns = [c["name"] for c in insp.get_columns("users")]
    if "stripe_customer_id" in columns:
        op.drop_index(
            "ix_users_stripe_customer_id",
            table_name="users",
        )
        op.drop_column("users", "stripe_customer_id")
