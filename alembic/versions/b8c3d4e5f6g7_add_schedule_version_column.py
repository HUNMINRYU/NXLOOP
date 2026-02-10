"""Add version column to pipeline_schedules for optimistic locking

Revision ID: b8c3d4e5f6g7
Revises: a7b2c3d4e5f6
Create Date: 2026-02-04 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b8c3d4e5f6g7"
down_revision: Union[str, None] = "a7b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "pipeline_schedules",
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )


def downgrade() -> None:
    op.drop_column("pipeline_schedules", "version")
