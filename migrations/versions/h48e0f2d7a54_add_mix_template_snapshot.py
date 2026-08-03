"""add mix template snapshot

Revision ID: h48e0f2d7a54
Revises: g37d9e1c6f43
Create Date: 2026-07-26 08:10:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "h48e0f2d7a54"
down_revision: Union[str, Sequence[str], None] = "g37d9e1c6f43"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "wb_production_mixes",
        sa.Column("template_id", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "wb_production_mixes",
        sa.Column("template_snapshot", sa.JSON(), nullable=False, server_default="{}"),
    )
    op.create_foreign_key(
        "fk_wb_production_mixes_template",
        "wb_production_mixes",
        "wb_production_templates",
        ["template_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_wb_production_mixes_template",
        "wb_production_mixes",
        ["template_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_wb_production_mixes_template",
        table_name="wb_production_mixes",
    )
    op.drop_constraint(
        "fk_wb_production_mixes_template",
        "wb_production_mixes",
        type_="foreignkey",
    )
    op.drop_column("wb_production_mixes", "template_snapshot")
    op.drop_column("wb_production_mixes", "template_id")
