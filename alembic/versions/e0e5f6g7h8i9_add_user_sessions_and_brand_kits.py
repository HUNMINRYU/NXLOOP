"""Add user_sessions and brand_kits tables

Revision ID: e0e5f6g7h8i9
Revises: d9d4e5f6g7h8
Create Date: 2026-02-08 21:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e0e5f6g7h8i9"
down_revision: Union[str, None] = "d9d4e5f6g7h8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    tables = insp.get_table_names()

    if "user_sessions" not in tables:
        op.create_table(
            "user_sessions",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column(
                "user_id",
                sa.Integer(),
                sa.ForeignKey("users.id"),
                nullable=False,
                index=True,
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index(
            "ix_user_sessions_expires_at",
            "user_sessions",
            ["expires_at"],
            unique=False,
        )

    if "brand_kits" not in tables:
        op.create_table(
            "brand_kits",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("name", sa.String(100), nullable=False),
            sa.Column("primary_color", sa.String(50), nullable=True),
            sa.Column("secondary_color", sa.String(50), nullable=True),
            sa.Column("font_style", sa.String(100), nullable=True),
            sa.Column("tone_and_voice", sa.String(255), nullable=True),
            sa.Column(
                "visual_vibes_json",
                sa.Text(),
                server_default="[]",
                nullable=False,
            ),
            sa.Column("logo_description", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("name"),
        )


def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    tables = insp.get_table_names()
    if "user_sessions" in tables:
        op.drop_index(
            "ix_user_sessions_expires_at",
            table_name="user_sessions",
        )
        op.drop_table("user_sessions")
    if "brand_kits" in tables:
        op.drop_table("brand_kits")
