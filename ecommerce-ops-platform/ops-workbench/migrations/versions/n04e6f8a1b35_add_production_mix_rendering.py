"""add production mix render tracking

Revision ID: n04e6f8a1b35
Revises: m93d5e7f0a24
Create Date: 2026-07-27
"""

from alembic import op
import sqlalchemy as sa


revision = "n04e6f8a1b35"
down_revision = "m93d5e7f0a24"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "wb_production_mixes",
        sa.Column("render_job_id", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "wb_production_mixes",
        sa.Column("output_path", sa.Text(), nullable=False, server_default=""),
    )
    op.add_column(
        "wb_production_mixes",
        sa.Column("render_error", sa.Text(), nullable=False, server_default=""),
    )
    op.add_column(
        "wb_production_mixes",
        sa.Column("render_started_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("wb_production_mixes", "render_started_at")
    op.drop_column("wb_production_mixes", "render_error")
    op.drop_column("wb_production_mixes", "output_path")
    op.drop_column("wb_production_mixes", "render_job_id")
