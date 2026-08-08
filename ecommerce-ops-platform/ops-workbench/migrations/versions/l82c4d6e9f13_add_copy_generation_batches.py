"""add copy generation batches and replenishment policy fields

Revision ID: l82c4d6e9f13
Revises: k71b3c5d8e02
Create Date: 2026-07-27
"""

from alembic import op
import sqlalchemy as sa


revision = "l82c4d6e9f13"
down_revision = "k71b3c5d8e02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "wb_copy_inventory_policies",
        sa.Column("rhythm_spec", sa.JSON(), nullable=False, server_default="{}"),
    )
    op.add_column(
        "wb_copy_inventory_policies",
        sa.Column("seed_text", sa.Text(), nullable=False, server_default=""),
    )
    op.create_table(
        "wb_copy_generation_batches",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("unit_type", sa.String(length=20), nullable=False),
        sa.Column("scope", sa.String(length=20), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=True),
        sa.Column("title_semantic_type_id", sa.String(length=32), nullable=True),
        sa.Column("subtitle_semantic_type_id", sa.String(length=32), nullable=True),
        sa.Column("rhythm_spec", sa.JSON(), nullable=False),
        sa.Column("seed_title", sa.Text(), nullable=False),
        sa.Column("seed_subtitle", sa.Text(), nullable=False),
        sa.Column("target_count", sa.Integer(), nullable=False),
        sa.Column("generated_count", sa.Integer(), nullable=False),
        sa.Column("duplicate_count", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("trigger_type", sa.String(length=20), nullable=False),
        sa.Column("policy_id", sa.String(length=32), nullable=True),
        sa.Column("job_id", sa.String(length=32), nullable=True),
        sa.Column("error", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["wb_products.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["title_semantic_type_id"], ["wb_copy_semantic_types.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["subtitle_semantic_type_id"], ["wb_copy_semantic_types.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["policy_id"], ["wb_copy_inventory_policies.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["job_id"], ["wb_jobs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_wb_copy_generation_batch_status",
        "wb_copy_generation_batches", ["status", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_wb_copy_generation_batch_status",
        table_name="wb_copy_generation_batches",
    )
    op.drop_table("wb_copy_generation_batches")
    op.drop_column("wb_copy_inventory_policies", "seed_text")
    op.drop_column("wb_copy_inventory_policies", "rhythm_spec")
