"""add candidate segments and shot tags

Revision ID: 4d8c2f019a64
Revises: c0f4a8e13b27
Create Date: 2026-07-25 03:10:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "4d8c2f019a64"
down_revision: Union[str, Sequence[str], None] = "c0f4a8e13b27"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "wb_shot_tags",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("normalized_name", sa.String(length=80), nullable=False),
        sa.Column("is_system", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "normalized_name", name="uq_wb_shot_tags_normalized_name"
        ),
    )
    op.create_table(
        "wb_candidate_segments",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("asset_id", sa.String(length=32), nullable=False),
        sa.Column("start_seconds", sa.Float(), nullable=False),
        sa.Column("end_seconds", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("origin", sa.String(length=30), nullable=False),
        sa.Column("detector_version", sa.String(length=40), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["asset_id"], ["wb_media_assets.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("wb_candidate_segments") as batch_op:
        batch_op.create_index(
            "ix_wb_candidate_segments_asset_status",
            ["asset_id", "status"],
            unique=False,
        )
    op.create_table(
        "wb_candidate_segment_tags",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("segment_id", sa.String(length=32), nullable=False),
        sa.Column("tag_id", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["segment_id"], ["wb_candidate_segments.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["tag_id"], ["wb_shot_tags.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "segment_id", "tag_id", name="uq_wb_candidate_segment_tag"
        ),
    )


def downgrade() -> None:
    op.drop_table("wb_candidate_segment_tags")
    with op.batch_alter_table("wb_candidate_segments") as batch_op:
        batch_op.drop_index("ix_wb_candidate_segments_asset_status")
    op.drop_table("wb_candidate_segments")
    op.drop_table("wb_shot_tags")
