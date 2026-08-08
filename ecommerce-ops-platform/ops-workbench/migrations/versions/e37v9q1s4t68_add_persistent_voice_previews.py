"""add persistent voice preview assets

Revision ID: e37v9q1s4t68
Revises: d26u8p0r3s57
Create Date: 2026-08-03
"""

import sqlalchemy as sa
from alembic import op


revision = "e37v9q1s4t68"
down_revision = "d26u8p0r3s57"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "wb_voice_preview_assets",
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("voice", sa.String(length=240), nullable=False),
        sa.Column("model", sa.String(length=200), nullable=False),
        sa.Column("audio_path", sa.Text(), nullable=False),
        sa.Column("audio_bytes", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("sequence"),
        sa.UniqueConstraint("voice"),
    )


def downgrade() -> None:
    op.drop_table("wb_voice_preview_assets")
