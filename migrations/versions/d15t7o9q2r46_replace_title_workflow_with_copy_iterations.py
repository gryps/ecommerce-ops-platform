"""replace title workflow with copy analysis and iterations

Revision ID: d15t7o9q2r46
Revises: c04s6n8p1q35
Create Date: 2026-08-02

The product owner explicitly chose a clean start for copy data. Existing title
strategies, title candidates and title-library rows are intentionally removed.
"""

import sqlalchemy as sa
from alembic import op


revision = "d15t7o9q2r46"
down_revision = "c04s6n8p1q35"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(
        "wb_jianying_drafts_title_content_id_fkey",
        "wb_jianying_drafts",
        type_="foreignkey",
    )
    op.drop_table("wb_copy_contents")
    op.drop_table("wb_title_strategies")
    op.alter_column(
        "wb_jianying_drafts", "title_content_id", new_column_name="copy_content_id"
    )
    op.execute("UPDATE wb_jianying_drafts SET copy_content_id = NULL")

    op.create_table(
        "wb_copy_analysis_records",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("source_mode", sa.String(length=20), nullable=False),
        sa.Column("source_text", sa.Text(), nullable=False),
        sa.Column("language_analysis", sa.JSON(), nullable=False),
        sa.Column("audience_analysis", sa.JSON(), nullable=False),
        sa.Column("expert_role", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_wb_copy_analysis_created", "wb_copy_analysis_records", ["created_at"]
    )
    op.create_table(
        "wb_copy_iteration_batches",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("analysis_record_id", sa.String(length=32), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["analysis_record_id"], ["wb_copy_analysis_records.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "analysis_record_id", "sequence_number", name="uq_wb_copy_batch_sequence"
        ),
    )
    op.create_index(
        "ix_wb_copy_batch_record_sequence",
        "wb_copy_iteration_batches",
        ["analysis_record_id", "sequence_number"],
    )
    op.create_table(
        "wb_copy_contents",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=True),
        sa.Column("iteration_batch_id", sa.String(length=32), nullable=True),
        sa.Column("content_text", sa.Text(), nullable=False),
        sa.Column("normalized_content", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("source", sa.String(length=30), nullable=False),
        sa.Column("rejection_reason", sa.Text(), nullable=False),
        sa.Column("reviewed_by", sa.String(length=32), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["wb_products.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["iteration_batch_id"], ["wb_copy_iteration_batches.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["reviewed_by"], ["wb_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_wb_copy_contents_status_created", "wb_copy_contents", ["status", "created_at"]
    )
    op.create_index(
        "ix_wb_copy_contents_product_created", "wb_copy_contents", ["product_id", "created_at"]
    )
    op.create_foreign_key(
        "fk_wb_jianying_drafts_copy_content",
        "wb_jianying_drafts",
        "wb_copy_contents",
        ["copy_content_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    raise RuntimeError("文案流程清空迁移不支持降级")
