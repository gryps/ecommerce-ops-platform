"""separate iteration candidates from the copy library

Revision ID: d26u8p0r3s57
Revises: d15t7o9q2r46
Create Date: 2026-08-02

Candidates are iteration history; library rows are adopted resources. Keeping
them separate lets either side be deleted without damaging the other and
removes review-only fields from the library table.
"""

import sqlalchemy as sa
from alembic import op


revision = "d26u8p0r3s57"
down_revision = "d15t7o9q2r46"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DELETE FROM wb_copy_contents")
    op.drop_index("ix_wb_copy_contents_status_created", table_name="wb_copy_contents")
    op.drop_constraint(
        "wb_copy_contents_iteration_batch_id_fkey",
        "wb_copy_contents",
        type_="foreignkey",
    )
    op.drop_constraint(
        "wb_copy_contents_reviewed_by_fkey",
        "wb_copy_contents",
        type_="foreignkey",
    )
    for column in (
        "iteration_batch_id",
        "status",
        "rejection_reason",
        "reviewed_by",
        "reviewed_at",
    ):
        op.drop_column("wb_copy_contents", column)

    op.create_table(
        "wb_copy_candidates",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("iteration_batch_id", sa.String(length=32), nullable=False),
        sa.Column("library_content_id", sa.String(length=32), nullable=True),
        sa.Column("content_text", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("rejection_reason", sa.Text(), nullable=False),
        sa.Column("reviewed_by", sa.String(length=32), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["iteration_batch_id"], ["wb_copy_iteration_batches.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["library_content_id"], ["wb_copy_contents.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["reviewed_by"], ["wb_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_wb_copy_candidate_batch_created",
        "wb_copy_candidates",
        ["iteration_batch_id", "created_at"],
    )


def downgrade() -> None:
    raise RuntimeError("文案候选分离迁移不支持降级")
