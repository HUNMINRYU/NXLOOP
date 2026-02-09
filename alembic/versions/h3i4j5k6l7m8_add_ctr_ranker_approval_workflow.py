"""add ctr ranker approval workflow

Revision ID: h3i4j5k6l7m8
Revises: g2g3h4i5j6k7
Create Date: 2026-02-09
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "h3i4j5k6l7m8"
down_revision = "g2g3h4i5j6k7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ctr_ranker_runs",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("product_name", sa.String(length=100), nullable=False),
        sa.Column("report_date", sa.Date(), nullable=False),
        sa.Column("mode", sa.String(length=50), nullable=False, server_default="youtube"),
        sa.Column("raw_dataset_path", sa.String(length=500), nullable=True),
        sa.Column("topk_csv_path", sa.String(length=500), nullable=True),
        sa.Column("report_json_path", sa.String(length=500), nullable=True),
        sa.Column("metrics_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_ctr_ranker_runs_product_name", "ctr_ranker_runs", ["product_name"])
    op.create_index("ix_ctr_ranker_runs_report_date", "ctr_ranker_runs", ["report_date"])

    op.create_table(
        "ctr_ranker_candidates",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("run_id", sa.String(length=36), nullable=False),
        sa.Column("video_id", sa.String(length=200), nullable=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("thumbnail_url", sa.String(length=500), nullable=True),
        sa.Column("baseline_rank", sa.Integer(), nullable=True),
        sa.Column("baseline_score", sa.Float(), nullable=True),
        sa.Column("after_rank", sa.Integer(), nullable=True),
        sa.Column("after_score", sa.Float(), nullable=True),
        sa.Column("proxy_score", sa.Float(), nullable=True),
        sa.Column("meta_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["ctr_ranker_runs.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("run_id", "video_id", name="uq_ctr_ranker_candidates_run_video"),
    )
    op.create_index("ix_ctr_ranker_candidates_run_id", "ctr_ranker_candidates", ["run_id"])
    op.create_index("ix_ctr_ranker_candidates_video_id", "ctr_ranker_candidates", ["video_id"])

    op.create_table(
        "ctr_ranker_approvals",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("run_id", sa.String(length=36), nullable=False),
        sa.Column("candidate_id", sa.Integer(), nullable=False),
        sa.Column("approved_by_user_id", sa.Integer(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["ctr_ranker_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["candidate_id"], ["ctr_ranker_candidates.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["approved_by_user_id"], ["users.id"]),
        sa.UniqueConstraint("run_id", name="uq_ctr_ranker_approvals_run_id"),
        sa.UniqueConstraint("candidate_id", name="uq_ctr_ranker_approvals_candidate_id"),
    )
    op.create_index("ix_ctr_ranker_approvals_run_id", "ctr_ranker_approvals", ["run_id"])
    op.create_index("ix_ctr_ranker_approvals_candidate_id", "ctr_ranker_approvals", ["candidate_id"])
    op.create_index(
        "ix_ctr_ranker_approvals_approved_by_user_id",
        "ctr_ranker_approvals",
        ["approved_by_user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_ctr_ranker_approvals_approved_by_user_id", table_name="ctr_ranker_approvals")
    op.drop_index("ix_ctr_ranker_approvals_candidate_id", table_name="ctr_ranker_approvals")
    op.drop_index("ix_ctr_ranker_approvals_run_id", table_name="ctr_ranker_approvals")
    op.drop_table("ctr_ranker_approvals")

    op.drop_index("ix_ctr_ranker_candidates_video_id", table_name="ctr_ranker_candidates")
    op.drop_index("ix_ctr_ranker_candidates_run_id", table_name="ctr_ranker_candidates")
    op.drop_table("ctr_ranker_candidates")

    op.drop_index("ix_ctr_ranker_runs_report_date", table_name="ctr_ranker_runs")
    op.drop_index("ix_ctr_ranker_runs_product_name", table_name="ctr_ranker_runs")
    op.drop_table("ctr_ranker_runs")
