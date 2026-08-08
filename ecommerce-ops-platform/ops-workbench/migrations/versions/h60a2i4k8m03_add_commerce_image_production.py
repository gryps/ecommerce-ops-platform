"""add commerce image production tables

Revision ID: h60a2i4k8m03
Revises: g59x1q3r8s02
Create Date: 2026-08-07
"""

import sqlalchemy as sa
from alembic import op


revision = "h60a2i4k8m03"
down_revision = "g59x1q3r8s02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "wb_image_products",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("product_code", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("category", sa.String(length=80), nullable=False),
        sa.Column("materials", sa.JSON(), nullable=False),
        sa.Column("primary_color", sa.String(length=80), nullable=False),
        sa.Column("secondary_color", sa.String(length=80), nullable=False),
        sa.Column("style_tags", sa.JSON(), nullable=False),
        sa.Column("structure_description", sa.Text(), nullable=False),
        sa.Column("selling_points", sa.JSON(), nullable=False),
        sa.Column("preserve_rules", sa.JSON(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("product_code", name="uq_wb_image_products_code"),
    )
    op.create_index(
        "ix_wb_image_products_status_code",
        "wb_image_products",
        ["status", "product_code"],
    )
    op.create_table(
        "wb_image_references",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("product_id", sa.String(length=32), nullable=False),
        sa.Column("image_type", sa.String(length=40), nullable=False),
        sa.Column("file_name", sa.String(length=240), nullable=False),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["wb_image_products.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("product_id", "image_type", name="uq_wb_image_reference_type"),
    )
    op.create_index("ix_wb_image_references_product", "wb_image_references", ["product_id"])
    op.create_table(
        "wb_image_generation_tasks",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("product_id", sa.String(length=32), nullable=False),
        sa.Column("template_id", sa.String(length=80), nullable=False),
        sa.Column("template_name", sa.String(length=120), nullable=False),
        sa.Column("model", sa.String(length=120), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("negative_prompt", sa.Text(), nullable=False),
        sa.Column("input_image_types", sa.JSON(), nullable=False),
        sa.Column("output_images", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("review_status", sa.String(length=30), nullable=False),
        sa.Column("review_issues", sa.JSON(), nullable=False),
        sa.Column("review_comment", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["wb_image_products.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_wb_image_tasks_product_created",
        "wb_image_generation_tasks",
        ["product_id", "created_at"],
    )
    op.create_index(
        "ix_wb_image_tasks_status_created",
        "wb_image_generation_tasks",
        ["status", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_wb_image_tasks_status_created", table_name="wb_image_generation_tasks")
    op.drop_index("ix_wb_image_tasks_product_created", table_name="wb_image_generation_tasks")
    op.drop_table("wb_image_generation_tasks")
    op.drop_index("ix_wb_image_references_product", table_name="wb_image_references")
    op.drop_table("wb_image_references")
    op.drop_index("ix_wb_image_products_status_code", table_name="wb_image_products")
    op.drop_table("wb_image_products")
