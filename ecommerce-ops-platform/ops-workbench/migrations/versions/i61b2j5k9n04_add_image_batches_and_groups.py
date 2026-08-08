"""add image batches and product groups

Revision ID: i61b2j5k9n04
Revises: h60a2i4k8m03
Create Date: 2026-08-07
"""

import sqlalchemy as sa
from alembic import op


revision = "i61b2j5k9n04"
down_revision = "h60a2i4k8m03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "wb_image_batches",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("source_directory", sa.Text(), nullable=False),
        sa.Column("source_images", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_wb_image_batches_status_created", "wb_image_batches", ["status", "created_at"])
    op.create_table(
        "wb_image_groups",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("batch_id", sa.String(length=32), nullable=False),
        sa.Column("product_id", sa.String(length=32), nullable=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("basis", sa.Text(), nullable=False),
        sa.Column("image_items", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["batch_id"], ["wb_image_batches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["wb_image_products.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_wb_image_groups_batch_sort", "wb_image_groups", ["batch_id", "sort_order"])
    op.create_index("ix_wb_image_groups_product", "wb_image_groups", ["product_id"])


def downgrade() -> None:
    op.drop_index("ix_wb_image_groups_product", table_name="wb_image_groups")
    op.drop_index("ix_wb_image_groups_batch_sort", table_name="wb_image_groups")
    op.drop_table("wb_image_groups")
    op.drop_index("ix_wb_image_batches_status_created", table_name="wb_image_batches")
    op.drop_table("wb_image_batches")
