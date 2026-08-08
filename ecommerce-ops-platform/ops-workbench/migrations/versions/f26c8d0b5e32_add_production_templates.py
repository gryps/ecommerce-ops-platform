"""add production templates

Revision ID: f26c8d0b5e32
Revises: e15b7c9a4d21
Create Date: 2026-07-26 06:10:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f26c8d0b5e32"
down_revision: Union[str, Sequence[str], None] = "e15b7c9a4d21"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "wb_production_templates",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("lineage_id", sa.String(length=32), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("template_kind", sa.String(length=30), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column("production_ready", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["wb_products.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "lineage_id",
            "version",
            name="uq_wb_production_template_lineage_version",
        ),
    )
    op.create_index(
        "ix_wb_production_templates_scope",
        "wb_production_templates",
        ["template_kind", "product_id", "status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_wb_production_templates_scope",
        table_name="wb_production_templates",
    )
    op.drop_table("wb_production_templates")
