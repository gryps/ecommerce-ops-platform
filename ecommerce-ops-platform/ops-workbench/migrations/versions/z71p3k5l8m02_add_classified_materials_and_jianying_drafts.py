"""add classified material tags and Jianying drafts

Revision ID: z71p3k5l8m02
Revises: z60o2j4k7l91
Create Date: 2026-08-01
"""

import sqlalchemy as sa
from alembic import op


revision = "z71p3k5l8m02"
down_revision = "z60o2j4k7l91"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "wb_music_resources",
        sa.Column("custom_tags", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.create_table(
        "wb_media_asset_tags",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("asset_id", sa.String(length=32), nullable=False),
        sa.Column("tag_id", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["wb_media_assets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tag_id"], ["wb_shot_tags.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("asset_id", "tag_id", name="uq_wb_media_asset_tag"),
    )
    op.create_index(
        "ix_wb_media_asset_tags_asset", "wb_media_asset_tags", ["asset_id"]
    )
    op.create_table(
        "wb_jianying_drafts",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("video_asset_ids", sa.JSON(), nullable=False),
        sa.Column("title_content_id", sa.String(length=32), nullable=True),
        sa.Column("narration_asset_id", sa.String(length=32), nullable=True),
        sa.Column("music_resource_id", sa.String(length=32), nullable=True),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("draft_path", sa.Text(), nullable=False),
        sa.Column("package_path", sa.Text(), nullable=False),
        sa.Column("error", sa.Text(), nullable=False),
        sa.Column("created_by", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["wb_products.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["title_content_id"], ["wb_copy_contents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["narration_asset_id"], ["wb_narration_assets.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["music_resource_id"], ["wb_music_resources.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by"], ["wb_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_wb_jianying_drafts_status_created",
        "wb_jianying_drafts",
        ["status", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_wb_jianying_drafts_status_created", table_name="wb_jianying_drafts"
    )
    op.drop_table("wb_jianying_drafts")
    op.drop_index("ix_wb_media_asset_tags_asset", table_name="wb_media_asset_tags")
    op.drop_table("wb_media_asset_tags")
    op.drop_column("wb_music_resources", "custom_tags")
