"""add copy reservations usage history and hot attribution

Revision ID: m93d5e7f0a24
Revises: l82c4d6e9f13
Create Date: 2026-07-27
"""

from alembic import op
import sqlalchemy as sa


revision = "m93d5e7f0a24"
down_revision = "l82c4d6e9f13"
branch_labels = None
depends_on = None


def upgrade() -> None:
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
        sa.ForeignKeyConstraint(["content_id"], ["wb_copy_contents.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["product_id"], ["wb_products.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_wb_copy_reservation_mix_status", "wb_copy_usage_reservations",
        ["production_mix_id", "status"],
    )
    op.create_index(
        "ix_wb_copy_reservation_content_status", "wb_copy_usage_reservations",
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
        sa.ForeignKeyConstraint(["content_id"], ["wb_copy_contents.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["product_id"], ["wb_products.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_wb_copy_usage_shape_time", "wb_copy_usage_events",
        ["usage_shape", "used_at"],
    )
    op.create_index(
        "ix_wb_copy_usage_content_time", "wb_copy_usage_events",
        ["content_id", "used_at"],
    )
    op.create_table(
        "wb_copy_hot_events",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("production_mix_id", sa.String(length=32), nullable=False),
        sa.Column("framework_id", sa.String(length=32), nullable=True),
        sa.Column("content_id", sa.String(length=32), nullable=True),
        sa.Column("usage_shape", sa.String(length=20), nullable=False),
        sa.Column("heat_level", sa.String(length=10), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["production_mix_id"], ["wb_production_mixes.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["framework_id"], ["wb_production_templates.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["content_id"], ["wb_copy_contents.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("production_mix_id", name="uq_wb_copy_hot_mix"),
    )
    op.create_index(
        "ix_wb_copy_hot_level_created", "wb_copy_hot_events",
        ["heat_level", "created_at"],
    )


def downgrade() -> None:
    op.drop_table("wb_copy_hot_events")
    op.drop_table("wb_copy_usage_events")
    op.drop_table("wb_copy_usage_reservations")
