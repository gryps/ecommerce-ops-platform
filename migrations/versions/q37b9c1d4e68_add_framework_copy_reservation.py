"""add framework copy reservation

Revision ID: q37b9c1d4e68
Revises: p26a8b0c3d57
Create Date: 2026-07-28
"""

from alembic import op
import sqlalchemy as sa


revision = "q37b9c1d4e68"
down_revision = "p26a8b0c3d57"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "wb_framework_copy_combinations",
        sa.Column("reserved_mix_id", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "wb_framework_copy_combinations",
        sa.Column("reserved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_wb_framework_copy_reserved_mix",
        "wb_framework_copy_combinations", ["reserved_mix_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_wb_framework_copy_reserved_mix",
        table_name="wb_framework_copy_combinations",
    )
    op.drop_column("wb_framework_copy_combinations", "reserved_at")
    op.drop_column("wb_framework_copy_combinations", "reserved_mix_id")
