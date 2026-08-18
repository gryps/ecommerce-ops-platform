"""add operations center

Revision ID: m05f7g9h2i36
Revises: l94e6f8g1h25
Create Date: 2026-08-11
"""

import sqlalchemy as sa
from alembic import op


revision = "m05f7g9h2i36"
down_revision = "l94e6f8g1h25"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "wb_ops_products",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("product_code", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("category", sa.String(length=80), nullable=False),
        sa.Column("style_tags", sa.JSON(), nullable=False),
        sa.Column("supplier_name", sa.String(length=160), nullable=False),
        sa.Column("supplier_link", sa.Text(), nullable=False),
        sa.Column("purchase_cost_yuan", sa.Float(), nullable=False),
        sa.Column("target_sale_price_yuan", sa.Float(), nullable=False),
        sa.Column("actual_sale_price_yuan", sa.Float(), nullable=False),
        sa.Column("stock_qty", sa.Integer(), nullable=False),
        sa.Column("inbound_qty", sa.Integer(), nullable=False),
        sa.Column("procurement_cycle_days", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("selection_grade", sa.String(length=20), nullable=False),
        sa.Column("owner", sa.String(length=80), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("product_code", name="uq_wb_ops_products_code"),
    )
    op.create_index("ix_wb_ops_products_status_name", "wb_ops_products", ["status", "name"])
    op.create_table(
        "wb_ops_live_sessions",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("live_date", sa.Date(), nullable=False),
        sa.Column("anchor", sa.String(length=80), nullable=False),
        sa.Column("start_time", sa.String(length=20), nullable=False),
        sa.Column("end_time", sa.String(length=20), nullable=False),
        sa.Column("target_orders", sa.Integer(), nullable=False),
        sa.Column("target_gmv_yuan", sa.Float(), nullable=False),
        sa.Column("actual_orders", sa.Integer(), nullable=False),
        sa.Column("actual_gmv_yuan", sa.Float(), nullable=False),
        sa.Column("ad_spend_yuan", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("review_summary", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_wb_ops_live_sessions_date_status", "wb_ops_live_sessions", ["live_date", "status"])
    op.create_table(
        "wb_ops_live_products",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("session_id", sa.String(length=32), nullable=False),
        sa.Column("product_id", sa.String(length=32), nullable=False),
        sa.Column("product_role", sa.String(length=40), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("planned_minutes", sa.Integer(), nullable=False),
        sa.Column("actual_orders", sa.Integer(), nullable=False),
        sa.Column("actual_gmv_yuan", sa.Float(), nullable=False),
        sa.Column("refund_orders", sa.Integer(), nullable=False),
        sa.Column("refund_amount_yuan", sa.Float(), nullable=False),
        sa.Column("estimated_profit_yuan", sa.Float(), nullable=False),
        sa.Column("action_suggestion", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["wb_ops_products.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["wb_ops_live_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_wb_ops_live_products_product", "wb_ops_live_products", ["product_id"])
    op.create_index("ix_wb_ops_live_products_session_order", "wb_ops_live_products", ["session_id", "order_index"])
    op.create_table(
        "wb_ops_ad_plans",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("ad_date", sa.Date(), nullable=False),
        sa.Column("platform", sa.String(length=80), nullable=False),
        sa.Column("plan_name", sa.String(length=160), nullable=False),
        sa.Column("promotion_type", sa.String(length=40), nullable=False),
        sa.Column("traffic_stage", sa.String(length=40), nullable=False),
        sa.Column("objective", sa.String(length=80), nullable=False),
        sa.Column("budget_type", sa.String(length=40), nullable=False),
        sa.Column("planned_budget_yuan", sa.Float(), nullable=False),
        sa.Column("actual_spend_yuan", sa.Float(), nullable=False),
        sa.Column("paid_gmv_yuan", sa.Float(), nullable=False),
        sa.Column("net_gmv_yuan", sa.Float(), nullable=False),
        sa.Column("paid_orders", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.String(length=32), nullable=True),
        sa.Column("live_session_id", sa.String(length=32), nullable=True),
        sa.Column("material_ref", sa.String(length=160), nullable=False),
        sa.Column("anchor", sa.String(length=80), nullable=False),
        sa.Column("operator_decision", sa.String(length=80), nullable=False),
        sa.Column("decision_reason", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["live_session_id"], ["wb_ops_live_sessions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["product_id"], ["wb_ops_products.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_wb_ops_ad_plans_date_stage", "wb_ops_ad_plans", ["ad_date", "traffic_stage"])
    op.create_index("ix_wb_ops_ad_plans_product", "wb_ops_ad_plans", ["product_id"])
    op.create_table(
        "wb_ops_daily_metrics",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("metric_date", sa.Date(), nullable=False),
        sa.Column("product_id", sa.String(length=32), nullable=True),
        sa.Column("paid_orders", sa.Integer(), nullable=False),
        sa.Column("paid_gmv_yuan", sa.Float(), nullable=False),
        sa.Column("refund_orders", sa.Integer(), nullable=False),
        sa.Column("refund_amount_yuan", sa.Float(), nullable=False),
        sa.Column("ad_spend_yuan", sa.Float(), nullable=False),
        sa.Column("logistics_cost_yuan", sa.Float(), nullable=False),
        sa.Column("freight_insurance_cost_yuan", sa.Float(), nullable=False),
        sa.Column("packaging_cost_yuan", sa.Float(), nullable=False),
        sa.Column("estimated_profit_yuan", sa.Float(), nullable=False),
        sa.Column("review_note", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["wb_ops_products.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("metric_date", "product_id", name="uq_wb_ops_daily_metrics_product_date"),
    )
    op.create_index("ix_wb_ops_daily_metrics_date", "wb_ops_daily_metrics", ["metric_date"])


def downgrade() -> None:
    op.drop_index("ix_wb_ops_daily_metrics_date", table_name="wb_ops_daily_metrics")
    op.drop_table("wb_ops_daily_metrics")
    op.drop_index("ix_wb_ops_ad_plans_product", table_name="wb_ops_ad_plans")
    op.drop_index("ix_wb_ops_ad_plans_date_stage", table_name="wb_ops_ad_plans")
    op.drop_table("wb_ops_ad_plans")
    op.drop_index("ix_wb_ops_live_products_session_order", table_name="wb_ops_live_products")
    op.drop_index("ix_wb_ops_live_products_product", table_name="wb_ops_live_products")
    op.drop_table("wb_ops_live_products")
    op.drop_index("ix_wb_ops_live_sessions_date_status", table_name="wb_ops_live_sessions")
    op.drop_table("wb_ops_live_sessions")
    op.drop_index("ix_wb_ops_products_status_name", table_name="wb_ops_products")
    op.drop_table("wb_ops_products")
