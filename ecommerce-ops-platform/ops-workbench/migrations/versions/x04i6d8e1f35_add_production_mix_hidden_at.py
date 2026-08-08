"""add production mix list hiding

Revision ID: x04i6d8e1f35
Revises: w93h5c7d0e24
Create Date: 2026-07-29
"""

from alembic import op
import sqlalchemy as sa


revision = "x04i6d8e1f35"
down_revision = "w93h5c7d0e24"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "wb_production_mixes",
        sa.Column("hidden_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("wb_production_mixes", "hidden_at")
