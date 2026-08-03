"""add production calendar

Revision ID: f3a9c7d21b46
Revises: e8f1a7c32d90
Create Date: 2026-07-25 12:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f3a9c7d21b46"
down_revision: Union[str, Sequence[str], None] = "e8f1a7c32d90"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "wb_production_calendar_days",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("plan_date", sa.Date(), nullable=False),
        sa.Column("daily_target", sa.Integer(), nullable=False),
        sa.Column("target_duration_seconds", sa.Float(), nullable=False),
        sa.Column("preset_style", sa.String(length=30), nullable=False),
        sa.Column("selected_product_id", sa.Integer(), nullable=True),
        sa.Column("selected_background_group_id", sa.Integer(), nullable=True),
        sa.Column("stop_day", sa.Boolean(), nullable=False),
        sa.Column("is_confirmed", sa.Boolean(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["selected_background_group_id"],
            ["wb_background_tone_groups.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["selected_product_id"],
            ["wb_products.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "plan_date",
            name="uq_wb_production_calendar_plan_date",
        ),
    )
    op.create_index(
        "ix_wb_production_calendar_plan_date",
        "wb_production_calendar_days",
        ["plan_date"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_wb_production_calendar_plan_date",
        table_name="wb_production_calendar_days",
    )
    op.drop_table("wb_production_calendar_days")
