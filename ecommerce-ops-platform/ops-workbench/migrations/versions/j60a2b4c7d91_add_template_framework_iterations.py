"""add template framework iterations

Revision ID: j60a2b4c7d91
Revises: i59f1a3e8b65
Create Date: 2026-07-26
"""

from alembic import op
import sqlalchemy as sa


revision = "j60a2b4c7d91"
down_revision = "i59f1a3e8b65"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("wb_production_templates", sa.Column("heat_level", sa.String(length=10), nullable=True))
    op.add_column("wb_production_templates", sa.Column("parent_framework_id", sa.String(length=32), nullable=True))
    op.add_column("wb_production_templates", sa.Column("iteration_root_id", sa.String(length=32), nullable=True))
    op.add_column("wb_production_templates", sa.Column("iteration_generation", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("wb_production_templates", sa.Column("iteration_package_id", sa.String(length=32), nullable=True))
    op.add_column("wb_production_templates", sa.Column("source_template_id", sa.String(length=32), nullable=True))
    op.create_foreign_key(
        "fk_wb_templates_parent_framework",
        "wb_production_templates", "wb_production_templates",
        ["parent_framework_id"], ["id"], ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_wb_templates_source_template",
        "wb_production_templates", "wb_production_templates",
        ["source_template_id"], ["id"], ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_wb_templates_source_template", "wb_production_templates", type_="foreignkey")
    op.drop_constraint("fk_wb_templates_parent_framework", "wb_production_templates", type_="foreignkey")
    op.drop_column("wb_production_templates", "source_template_id")
    op.drop_column("wb_production_templates", "iteration_package_id")
    op.drop_column("wb_production_templates", "iteration_generation")
    op.drop_column("wb_production_templates", "iteration_root_id")
    op.drop_column("wb_production_templates", "parent_framework_id")
    op.drop_column("wb_production_templates", "heat_level")
