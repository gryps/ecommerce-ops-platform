"""add narration assets

Revision ID: z48m0h2i5j79
Revises: z37l9g1h4i68
Create Date: 2026-07-31
"""

from alembic import op
import sqlalchemy as sa


revision = "z48m0h2i5j79"
down_revision = "z37l9g1h4i68"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "wb_narration_assets",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("text_source", sa.String(length=20), nullable=False),
        sa.Column("voice_source", sa.String(length=20), nullable=False),
        sa.Column("approved_text", sa.Text(), nullable=False),
        sa.Column("recognized_text", sa.Text(), nullable=False),
        sa.Column("subtitle_cues", sa.JSON(), nullable=False),
        sa.Column("audio_path", sa.Text(), nullable=False),
        sa.Column("voice_preset_id", sa.String(length=32), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["voice_preset_id"], ["wb_voice_presets.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_wb_narration_asset_status_created",
        "wb_narration_assets",
        ["status", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_wb_narration_asset_status_created",
        table_name="wb_narration_assets",
    )
    op.drop_table("wb_narration_assets")
