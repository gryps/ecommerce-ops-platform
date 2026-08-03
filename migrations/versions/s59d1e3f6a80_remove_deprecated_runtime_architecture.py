"""remove deprecated runtime architecture

Revision ID: s59d1e3f6a80
Revises: r48c0d2e5f79
Create Date: 2026-07-28
"""

from alembic import op
import sqlalchemy as sa


revision = "s59d1e3f6a80"
down_revision = "r48c0d2e5f79"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_table("wb_copy_usage_events")
    op.drop_table("wb_copy_usage_reservations")
    op.drop_table("wb_production_calendar_days")
    op.drop_constraint(
        "fk_wb_templates_source_template",
        "wb_production_templates",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_wb_production_templates_scope",
        table_name="wb_production_templates",
    )
    op.drop_column("wb_production_templates", "source_template_id")
    op.drop_column("wb_production_templates", "template_kind")
    op.create_index(
        "ix_wb_production_templates_scope",
        "wb_production_templates",
        ["product_id", "status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_wb_production_templates_scope",
        table_name="wb_production_templates",
    )
    op.add_column(
        "wb_production_templates",
        sa.Column(
            "template_kind",
            sa.String(length=30),
            nullable=False,
            server_default="complete",
        ),
    )
    op.add_column(
        "wb_production_templates",
        sa.Column("source_template_id", sa.String(length=32), nullable=True),
    )
    op.create_foreign_key(
        "fk_wb_templates_source_template",
        "wb_production_templates",
        "wb_production_templates",
        ["source_template_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_wb_production_templates_scope",
        "wb_production_templates",
        ["template_kind", "product_id", "status"],
    )
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
            ["selected_product_id"], ["wb_products.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["selected_background_group_id"],
            ["wb_background_tone_groups.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "plan_date", name="uq_wb_production_calendar_plan_date"
        ),
    )
    op.create_index(
        "ix_wb_production_calendar_plan_date",
        "wb_production_calendar_days",
        ["plan_date"],
    )
    op.create_table(
        "wb_copy_usage_reservations",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("production_mix_id", sa.String(length=32), nullable=True),
        sa.Column("content_id", sa.String(length=32), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("usage_shape", sa.String(length=20), nullable=False),
        sa.Column("normalized_title", sa.Text(), nullable=False),
        sa.Column("normalized_subtitle", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("reserved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["production_mix_id"], ["wb_production_mixes.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["content_id"], ["wb_copy_contents.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["product_id"], ["wb_products.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_wb_copy_reservation_mix_status",
        "wb_copy_usage_reservations",
        ["production_mix_id", "status"],
    )
    op.create_index(
        "ix_wb_copy_reservation_content_status",
        "wb_copy_usage_reservations",
        ["content_id", "status"],
    )
    op.create_table(
        "wb_copy_usage_events",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("production_mix_id", sa.String(length=32), nullable=False),
        sa.Column("content_id", sa.String(length=32), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("usage_shape", sa.String(length=20), nullable=False),
        sa.Column("content_scope", sa.String(length=20), nullable=False),
        sa.Column("normalized_title", sa.Text(), nullable=False),
        sa.Column("normalized_subtitle", sa.Text(), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["production_mix_id"], ["wb_production_mixes.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["content_id"], ["wb_copy_contents.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["product_id"], ["wb_products.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_wb_copy_usage_shape_time",
        "wb_copy_usage_events",
        ["usage_shape", "used_at"],
    )
    op.create_index(
        "ix_wb_copy_usage_content_time",
        "wb_copy_usage_events",
        ["content_id", "used_at"],
    )
