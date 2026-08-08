"""make Jianying drafts video-free

Revision ID: g59x1q3r8s02
Revises: f48w0r2t5u79
Create Date: 2026-08-03
"""

from alembic import op


revision = "g59x1q3r8s02"
down_revision = "f48w0r2t5u79"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE wb_jianying_drafts DROP CONSTRAINT IF EXISTS wb_jianying_drafts_product_id_fkey")
    op.execute("ALTER TABLE wb_jianying_drafts DROP COLUMN IF EXISTS product_id")
    op.execute("ALTER TABLE wb_jianying_drafts DROP COLUMN IF EXISTS video_asset_ids")
    op.execute("ALTER TABLE wb_jianying_drafts DROP COLUMN IF EXISTS package_path")


def downgrade() -> None:
    raise RuntimeError("无视频剪映草稿迁移不支持降级")
