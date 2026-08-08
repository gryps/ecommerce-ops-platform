"""add model call logs and permanent daily summaries

Revision ID: i59f1a3e8b65
Revises: h48e0f2d7a54
Create Date: 2026-07-26 21:20:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "i59f1a3e8b65"
down_revision: Union[str, Sequence[str], None] = "h48e0f2d7a54"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "wb_model_call_logs",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("call_id", sa.String(length=32), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("stage", sa.String(length=80), nullable=False),
        sa.Column("label", sa.String(length=160), nullable=False),
        sa.Column("provider", sa.String(length=80), nullable=False),
        sa.Column("model", sa.String(length=200), nullable=False),
        sa.Column("business_step", sa.String(length=120), nullable=False),
        sa.Column("business_objects", sa.JSON(), nullable=False),
        sa.Column("input_payload", sa.JSON(), nullable=False),
        sa.Column("output_payload", sa.JSON(), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("token_usage_reported", sa.Boolean(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_wb_model_call_logs_stage_created",
        "wb_model_call_logs",
        ["stage", "created_at"],
    )
    op.create_index(
        "ix_wb_model_call_logs_call_id",
        "wb_model_call_logs",
        ["call_id"],
    )
    op.create_table(
        "wb_model_call_daily_summaries",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("stat_date", sa.Date(), nullable=False),
        sa.Column("stage", sa.String(length=80), nullable=False),
        sa.Column("successful_calls", sa.Integer(), nullable=False),
        sa.Column("failed_calls", sa.Integer(), nullable=False),
        sa.Column("input_tokens", sa.BigInteger(), nullable=False),
        sa.Column("output_tokens", sa.BigInteger(), nullable=False),
        sa.Column("total_tokens", sa.BigInteger(), nullable=False),
        sa.Column("token_reported_calls", sa.Integer(), nullable=False),
        sa.Column("total_duration_ms", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "stat_date",
            "stage",
            name="uq_wb_model_call_daily_stage",
        ),
    )
    op.create_index(
        "ix_wb_model_call_daily_stage_date",
        "wb_model_call_daily_summaries",
        ["stage", "stat_date"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_wb_model_call_daily_stage_date",
        table_name="wb_model_call_daily_summaries",
    )
    op.drop_table("wb_model_call_daily_summaries")
    op.drop_index(
        "ix_wb_model_call_logs_call_id",
        table_name="wb_model_call_logs",
    )
    op.drop_index(
        "ix_wb_model_call_logs_stage_created",
        table_name="wb_model_call_logs",
    )
    op.drop_table("wb_model_call_logs")
