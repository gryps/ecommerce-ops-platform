"""add production mix lifecycle timestamps

Revision ID: e15b7c9a4d21
Revises: d04a6e8f1b32
Create Date: 2026-07-26 05:10:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e15b7c9a4d21"
down_revision: Union[str, Sequence[str], None] = "d04a6e8f1b32"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "wb_production_mixes",
        sa.Column("selected_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "wb_production_mixes",
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("wb_production_mixes", "completed_at")
    op.drop_column("wb_production_mixes", "selected_at")
