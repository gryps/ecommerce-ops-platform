"""add uploaded image source assets

Revision ID: i61b3j9p2s04
Revises: j62c3k6l0p15
Create Date: 2026-08-08
"""

import sqlalchemy as sa
from alembic import op


revision = "i61b3j9p2s04"
down_revision = "j62c3k6l0p15"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "wb_image_source_assets",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("file_name", sa.String(length=240), nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_path", name="uq_wb_image_source_assets_storage_path"),
    )
    op.create_index(
        "ix_wb_image_source_assets_status_created",
        "wb_image_source_assets",
        ["status", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_wb_image_source_assets_status_created", table_name="wb_image_source_assets")
    op.drop_table("wb_image_source_assets")
