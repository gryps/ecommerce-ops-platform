"""add music resources

Revision ID: g37d9e1c6f43
Revises: f26c8d0b5e32
Create Date: 2026-07-26 07:10:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "g37d9e1c6f43"
down_revision: Union[str, Sequence[str], None] = "f26c8d0b5e32"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "wb_music_resources",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("source_type", sa.String(length=30), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("rights_confirmed", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("duration_seconds", sa.Float(), nullable=False),
        sa.Column("bpm", sa.Float(), nullable=False),
        sa.Column("beat_times", sa.JSON(), nullable=False),
        sa.Column("error", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_wb_music_resources_status_created",
        "wb_music_resources",
        ["status", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_wb_music_resources_status_created",
        table_name="wb_music_resources",
    )
    op.drop_table("wb_music_resources")
