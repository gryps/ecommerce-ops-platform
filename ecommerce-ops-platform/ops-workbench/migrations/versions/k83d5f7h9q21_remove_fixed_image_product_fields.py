"""remove fixed image product archive fields

Revision ID: k83d5f7h9q21
Revises: j72d4l7m1q05
Create Date: 2026-08-08
"""

import sqlalchemy as sa
from alembic import op


revision = "k83d5f7h9q21"
down_revision = "j72d4l7m1q05"
branch_labels = None
depends_on = None


FIXED_COLUMNS = (
    "category",
    "materials",
    "primary_color",
    "secondary_color",
    "style_tags",
    "structure_description",
    "selling_points",
    "preserve_rules",
    "notes",
)


def upgrade() -> None:
    op.drop_index("ix_wb_image_references_product", table_name="wb_image_references")
    op.drop_table("wb_image_references")
    with op.batch_alter_table("wb_image_products") as batch_op:
        for column in FIXED_COLUMNS:
            batch_op.drop_column(column)


def downgrade() -> None:
    with op.batch_alter_table("wb_image_products") as batch_op:
        batch_op.add_column(sa.Column("category", sa.String(length=80), nullable=False, server_default=""))
        batch_op.add_column(sa.Column("materials", sa.JSON(), nullable=False, server_default="[]"))
        batch_op.add_column(sa.Column("primary_color", sa.String(length=80), nullable=False, server_default=""))
        batch_op.add_column(sa.Column("secondary_color", sa.String(length=80), nullable=False, server_default=""))
        batch_op.add_column(sa.Column("style_tags", sa.JSON(), nullable=False, server_default="[]"))
        batch_op.add_column(sa.Column("structure_description", sa.Text(), nullable=False, server_default=""))
        batch_op.add_column(sa.Column("selling_points", sa.JSON(), nullable=False, server_default="[]"))
        batch_op.add_column(sa.Column("preserve_rules", sa.JSON(), nullable=False, server_default="[]"))
        batch_op.add_column(sa.Column("notes", sa.Text(), nullable=False, server_default=""))
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
