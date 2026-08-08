"""add production plan deduplication rule

Revision ID: y15j7e9f2g46
Revises: x04i6d8e1f35
Create Date: 2026-07-29
"""

from alembic import op
import sqlalchemy as sa


revision = "y15j7e9f2g46"
down_revision = "x04i6d8e1f35"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "wb_production_mixes",
        sa.Column(
            "deduplication_window_days",
            sa.Integer(),
            nullable=False,
            server_default="90",
        ),
    )
    op.add_column(
        "wb_production_mixes",
        sa.Column(
            "max_history_reuse_ratio",
            sa.Float(),
            nullable=False,
            server_default="0.3",
        ),
    )
    op.alter_column(
        "wb_production_mixes",
        "deduplication_window_days",
        server_default=None,
    )
    op.alter_column(
        "wb_production_mixes",
        "max_history_reuse_ratio",
        server_default=None,
    )


def downgrade() -> None:
    op.drop_column("wb_production_mixes", "max_history_reuse_ratio")
    op.drop_column("wb_production_mixes", "deduplication_window_days")
