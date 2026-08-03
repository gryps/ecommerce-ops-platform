"""add media quality review

Revision ID: c0f4a8e13b27
Revises: 95f5da9cb7f3
Create Date: 2026-07-25 01:45:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c0f4a8e13b27"
down_revision: Union[str, Sequence[str], None] = "95f5da9cb7f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("wb_media_assets") as batch_op:
        batch_op.add_column(
            sa.Column(
                "quality_review_status",
                sa.String(length=30),
                nullable=False,
                server_default="pending",
            )
        )
        batch_op.add_column(
            sa.Column(
                "quality_review_note",
                sa.Text(),
                nullable=False,
                server_default="",
            )
        )
        batch_op.add_column(
            sa.Column("quality_reviewed_at", sa.DateTime(timezone=True), nullable=True)
        )

    op.create_table(
        "wb_media_quality_issues",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("asset_id", sa.String(length=32), nullable=False),
        sa.Column("issue_type", sa.String(length=40), nullable=False),
        sa.Column("start_seconds", sa.Float(), nullable=False),
        sa.Column("end_seconds", sa.Float(), nullable=False),
        sa.Column("severity", sa.Float(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("detector_version", sa.String(length=40), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("review_status", sa.String(length=30), nullable=False),
        sa.Column("review_note", sa.Text(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["asset_id"], ["wb_media_assets.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("wb_media_quality_issues") as batch_op:
        batch_op.create_index(
            "ix_wb_media_quality_issues_asset_review",
            ["asset_id", "review_status"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("wb_media_quality_issues") as batch_op:
        batch_op.drop_index("ix_wb_media_quality_issues_asset_review")
    op.drop_table("wb_media_quality_issues")
    with op.batch_alter_table("wb_media_assets") as batch_op:
        batch_op.drop_column("quality_reviewed_at")
        batch_op.drop_column("quality_review_note")
        batch_op.drop_column("quality_review_status")
