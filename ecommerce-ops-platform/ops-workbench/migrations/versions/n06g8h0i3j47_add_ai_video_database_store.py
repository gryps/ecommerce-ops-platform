"""add ai video database store

Revision ID: n06g8h0i3j47
Revises: m05f7g9h2i36
Create Date: 2026-08-17
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "n06g8h0i3j47"
down_revision = "m05f7g9h2i36"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "wb_ai_video_projects",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("product_name", sa.String(length=200), nullable=False),
        sa.Column("selling_points", sa.Text(), nullable=False),
        sa.Column("audience", sa.Text(), nullable=False),
        sa.Column("tone", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_wb_ai_video_projects_status_created",
        "wb_ai_video_projects",
        ["status", "created_at"],
    )
    op.create_table(
        "wb_ai_video_assets",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("project_id", sa.String(length=32), nullable=False),
        sa.Column("kind", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("preview_url", sa.Text(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["wb_ai_video_projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_wb_ai_video_assets_created", "wb_ai_video_assets", ["created_at"])
    op.create_index(
        "ix_wb_ai_video_assets_project_kind",
        "wb_ai_video_assets",
        ["project_id", "kind"],
    )
    op.create_table(
        "wb_ai_video_shots",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("project_id", sa.String(length=32), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("duration_seconds", sa.Float(), nullable=False),
        sa.Column("visual_goal", sa.Text(), nullable=False),
        sa.Column("camera", sa.Text(), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("negative_prompt", sa.Text(), nullable=False),
        sa.Column("required_asset_kinds", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["wb_ai_video_projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_wb_ai_video_shots_project_order",
        "wb_ai_video_shots",
        ["project_id", "order_index"],
    )
    op.create_table(
        "wb_ai_video_generation_tasks",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("project_id", sa.String(length=32), nullable=False),
        sa.Column("engine", sa.String(length=40), nullable=False),
        sa.Column("workflow_name", sa.String(length=120), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("input_asset_ids", sa.JSON(), nullable=False),
        sa.Column("provider_task_id", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("output_paths", sa.JSON(), nullable=False),
        sa.Column("error", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["wb_ai_video_projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_wb_ai_video_tasks_created", "wb_ai_video_generation_tasks", ["created_at"])
    op.create_index(
        "ix_wb_ai_video_tasks_project_status",
        "wb_ai_video_generation_tasks",
        ["project_id", "status"],
    )
    op.create_table(
        "wb_ai_video_task_events",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("task_id", sa.String(length=32), nullable=False),
        sa.Column("event_type", sa.String(length=60), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["wb_ai_video_generation_tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_wb_ai_video_task_events_task_created",
        "wb_ai_video_task_events",
        ["task_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_wb_ai_video_task_events_task_created", table_name="wb_ai_video_task_events")
    op.drop_table("wb_ai_video_task_events")
    op.drop_index("ix_wb_ai_video_tasks_project_status", table_name="wb_ai_video_generation_tasks")
    op.drop_index("ix_wb_ai_video_tasks_created", table_name="wb_ai_video_generation_tasks")
    op.drop_table("wb_ai_video_generation_tasks")
    op.drop_index("ix_wb_ai_video_shots_project_order", table_name="wb_ai_video_shots")
    op.drop_table("wb_ai_video_shots")
    op.drop_index("ix_wb_ai_video_assets_project_kind", table_name="wb_ai_video_assets")
    op.drop_index("ix_wb_ai_video_assets_created", table_name="wb_ai_video_assets")
    op.drop_table("wb_ai_video_assets")
    op.drop_index("ix_wb_ai_video_projects_status_created", table_name="wb_ai_video_projects")
    op.drop_table("wb_ai_video_projects")
