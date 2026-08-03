"""add production mixes

Revision ID: d04a6e8f1b32
Revises: c93f2d7e5a20
Create Date: 2026-07-26 03:10:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d04a6e8f1b32"
down_revision: Union[str, Sequence[str], None] = "c93f2d7e5a20"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "wb_production_mixes",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("background_group_id", sa.Integer(), nullable=False),
        sa.Column("preset", sa.String(length=30), nullable=False),
        sa.Column("target_duration_seconds", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("timeline", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["background_group_id"], ["wb_background_tone_groups.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["product_id"], ["wb_products.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_wb_production_mixes_created_status", "wb_production_mixes", ["created_at", "status"])
    op.create_index("ix_wb_production_mixes_product_background", "wb_production_mixes", ["product_id", "background_group_id"])
    op.create_table(
        "wb_production_mix_clips",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("mix_id", sa.String(length=32), nullable=False),
        sa.Column("segment_id", sa.String(length=32), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("similarity_signature", sa.String(length=500), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["mix_id"], ["wb_production_mixes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["segment_id"], ["wb_candidate_segments.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("mix_id", "order_index", name="uq_wb_production_mix_clip_order"),
    )
    op.create_index("ix_wb_production_mix_clips_segment", "wb_production_mix_clips", ["segment_id"])
    op.create_index("ix_wb_production_mix_clips_signature", "wb_production_mix_clips", ["similarity_signature"])


def downgrade() -> None:
    op.drop_index("ix_wb_production_mix_clips_signature", table_name="wb_production_mix_clips")
    op.drop_index("ix_wb_production_mix_clips_segment", table_name="wb_production_mix_clips")
    op.drop_table("wb_production_mix_clips")
    op.drop_index("ix_wb_production_mixes_product_background", table_name="wb_production_mixes")
    op.drop_index("ix_wb_production_mixes_created_status", table_name="wb_production_mixes")
    op.drop_table("wb_production_mixes")
