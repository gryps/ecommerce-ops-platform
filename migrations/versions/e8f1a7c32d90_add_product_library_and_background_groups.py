"""add product library and background tone groups

Revision ID: e8f1a7c32d90
Revises: 4d8c2f019a64
Create Date: 2026-07-25 04:20:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e8f1a7c32d90"
down_revision: Union[str, Sequence[str], None] = "4d8c2f019a64"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "wb_products",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("brand", sa.String(length=120), nullable=False),
        sa.Column("model_number", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("selling_points", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("merged_into_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["merged_into_id"], ["wb_products.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_wb_products_status_name", "wb_products", ["status", "name"])
    op.create_table(
        "wb_media_asset_products",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("asset_id", sa.String(length=32), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("origin", sa.String(length=30), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["wb_media_assets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["wb_products.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_wb_media_asset_products_asset_status",
        "wb_media_asset_products",
        ["asset_id", "status"],
    )
    op.create_index(
        "ix_wb_media_asset_products_product_status",
        "wb_media_asset_products",
        ["product_id", "status"],
    )
    op.create_table(
        "wb_background_tone_groups",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("primary_color", sa.String(length=80), nullable=False),
        sa.Column("color_temperature", sa.String(length=40), nullable=False),
        sa.Column("brightness", sa.String(length=40), nullable=False),
        sa.Column("scene", sa.String(length=160), nullable=False),
        sa.Column("lighting_style", sa.String(length=160), nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["wb_products.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_wb_background_groups_product_status",
        "wb_background_tone_groups",
        ["product_id", "status"],
    )
    op.create_table(
        "wb_media_asset_backgrounds",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("asset_id", sa.String(length=32), nullable=False),
        sa.Column("background_group_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("cross_batch_confirmed", sa.Boolean(), nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["wb_media_assets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["background_group_id"],
            ["wb_background_tone_groups.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_wb_media_asset_backgrounds_asset_status",
        "wb_media_asset_backgrounds",
        ["asset_id", "status"],
    )
    op.create_index(
        "ix_wb_media_asset_backgrounds_group_status",
        "wb_media_asset_backgrounds",
        ["background_group_id", "status"],
    )


def downgrade() -> None:
    op.drop_table("wb_media_asset_backgrounds")
    op.drop_table("wb_background_tone_groups")
    op.drop_table("wb_media_asset_products")
    op.drop_table("wb_products")
