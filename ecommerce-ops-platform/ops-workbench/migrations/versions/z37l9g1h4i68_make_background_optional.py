"""make production background optional

Revision ID: z37l9g1h4i68
Revises: z26k8f0g3h57
Create Date: 2026-07-31
"""

from alembic import op
import sqlalchemy as sa


revision = "z37l9g1h4i68"
down_revision = "z26k8f0g3h57"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "wb_production_mixes",
        "background_group_id",
        existing_type=sa.Integer(),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "wb_production_mixes",
        "background_group_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
