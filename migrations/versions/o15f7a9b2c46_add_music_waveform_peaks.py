"""add music waveform peaks

Revision ID: o15f7a9b2c46
Revises: n04e6f8a1b35
Create Date: 2026-07-27
"""

from alembic import op
import sqlalchemy as sa


revision = "o15f7a9b2c46"
down_revision = "n04e6f8a1b35"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "wb_music_resources",
        sa.Column("waveform_peaks", sa.JSON(), nullable=False, server_default="[]"),
    )


def downgrade() -> None:
    op.drop_column("wb_music_resources", "waveform_peaks")
