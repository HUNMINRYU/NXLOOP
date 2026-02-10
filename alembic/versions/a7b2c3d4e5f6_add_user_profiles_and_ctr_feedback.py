"""Add user_profiles and ctr_feedback tables

Revision ID: a7b2c3d4e5f6
Revises: c121533f78bf
Create Date: 2026-02-04 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a7b2c3d4e5f6"
down_revision: Union[str, None] = "c121533f78bf"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_profiles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("product_id", sa.String(100), nullable=False),
        sa.Column("preferences_json", sa.Text(), server_default="{}", nullable=False),
        sa.Column(
            "topic_affinities_json", sa.Text(), server_default="{}", nullable=False
        ),
        sa.Column(
            "interaction_count", sa.Integer(), server_default="0", nullable=False
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("product_id"),
    )

    op.create_table(
        "ctr_feedback",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("video_id", sa.String(200), nullable=False),
        sa.Column("predicted_ctr", sa.String(20), nullable=False),
        sa.Column("actual_ctr", sa.String(20), nullable=True),
        sa.Column("error", sa.String(20), nullable=True),
        sa.Column(
            "model_version",
            sa.String(50),
            server_default="v1",
            nullable=False,
        ),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ctr_feedback_video_id", "ctr_feedback", ["video_id"])


def downgrade() -> None:
    op.drop_index("ix_ctr_feedback_video_id", table_name="ctr_feedback")
    op.drop_table("ctr_feedback")
    op.drop_table("user_profiles")
