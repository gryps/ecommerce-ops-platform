"""add admin user profile fields

Revision ID: l94e6f8g1h25
Revises: k83d5f7h9q21
Create Date: 2026-08-09
"""

import sqlalchemy as sa
from alembic import op


revision = "l94e6f8g1h25"
down_revision = "k83d5f7h9q21"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("wb_users", sa.Column("display_name", sa.String(length=80), nullable=False, server_default=""))
    op.add_column("wb_users", sa.Column("phone", sa.String(length=40), nullable=False, server_default=""))


def downgrade() -> None:
    op.drop_column("wb_users", "phone")
    op.drop_column("wb_users", "display_name")
