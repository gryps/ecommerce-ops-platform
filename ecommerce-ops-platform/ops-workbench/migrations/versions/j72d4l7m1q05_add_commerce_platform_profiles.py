"""add commerce platform templates and product profiles

Revision ID: j72d4l7m1q05
Revises: i61b3j9p2s04
Create Date: 2026-08-08
"""

import sqlalchemy as sa
from alembic import op


revision = "j72d4l7m1q05"
down_revision = "i61b3j9p2s04"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "wb_commerce_platform_templates",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("platform", sa.String(length=80), nullable=False),
        sa.Column("entry_url", sa.Text(), nullable=False),
        sa.Column("fields", sa.JSON(), nullable=False),
        sa.Column("image_slots", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_wb_commerce_platform_template_name"),
    )
    op.create_table(
        "wb_commerce_product_platform_profiles",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("product_id", sa.String(length=32), nullable=False),
        sa.Column("template_id", sa.String(length=32), nullable=False),
        sa.Column("values", sa.JSON(), nullable=False),
        sa.Column("image_selections", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("draft_url", sa.Text(), nullable=False),
        sa.Column("process_log", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["wb_image_products.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["template_id"], ["wb_commerce_platform_templates.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("product_id", "template_id", name="uq_wb_commerce_product_platform_profile"),
    )
    op.create_index("ix_wb_commerce_platform_profiles_status", "wb_commerce_product_platform_profiles", ["status", "updated_at"])


def downgrade() -> None:
    op.drop_index("ix_wb_commerce_platform_profiles_status", table_name="wb_commerce_product_platform_profiles")
    op.drop_table("wb_commerce_product_platform_profiles")
    op.drop_table("wb_commerce_platform_templates")
