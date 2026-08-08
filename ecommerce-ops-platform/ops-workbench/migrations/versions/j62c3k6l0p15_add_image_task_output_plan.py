"""add image task output plan

Revision ID: j62c3k6l0p15
Revises: i61b2j5k9n04
Create Date: 2026-08-07
"""

import sqlalchemy as sa
from alembic import op


revision = "j62c3k6l0p15"
down_revision = "i61b2j5k9n04"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("wb_image_generation_tasks", sa.Column("output_plan", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))


def downgrade() -> None:
    op.drop_column("wb_image_generation_tasks", "output_plan")
