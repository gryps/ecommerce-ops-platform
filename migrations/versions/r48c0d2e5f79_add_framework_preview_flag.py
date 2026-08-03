"""add framework preview flag

Revision ID: r48c0d2e5f79
Revises: q37b9c1d4e68
Create Date: 2026-07-28
"""

from alembic import op
import sqlalchemy as sa


revision = "r48c0d2e5f79"
down_revision = "q37b9c1d4e68"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "wb_production_mixes",
        sa.Column("is_preview", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("wb_production_mixes", "is_preview")
