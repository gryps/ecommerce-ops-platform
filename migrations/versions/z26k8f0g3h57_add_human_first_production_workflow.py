"""add human-first production workflow

Revision ID: z26k8f0g3h57
Revises: y15j7e9f2g46
Create Date: 2026-07-31
"""

from alembic import op
import sqlalchemy as sa


revision = "z26k8f0g3h57"
down_revision = "y15j7e9f2g46"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "wb_shot_tags",
        sa.Column("category", sa.String(length=40), nullable=False, server_default="other"),
    )
    op.add_column(
        "wb_shot_tags",
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "wb_products",
        sa.Column(
            "output_naming_rule",
            sa.String(length=500),
            nullable=False,
            server_default="{product}-{title}-{date}-{sequence}",
        ),
    )
    op.add_column(
        "wb_products",
        sa.Column(
            "non_hot_after_days",
            sa.Integer(),
            nullable=False,
            server_default="7",
        ),
    )

    op.create_table(
        "wb_title_strategies",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("emotion", sa.Text(), nullable=False),
        sa.Column("tension", sa.Text(), nullable=False),
        sa.Column("controversy", sa.Text(), nullable=False),
        sa.Column("de_ai_requirements", sa.Text(), nullable=False),
        sa.Column("generation_prompt", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_wb_title_strategy_name"),
    )
    op.create_index(
        "ix_wb_title_strategy_status_sort",
        "wb_title_strategies",
        ["status", "sort_order"],
    )
    op.create_table(
        "wb_music_beat_schemes",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("music_resource_id", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("source_start_seconds", sa.Float(), nullable=False),
        sa.Column("source_end_seconds", sa.Float(), nullable=False),
        sa.Column("slots", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["music_resource_id"], ["wb_music_resources.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "music_resource_id", "name", name="uq_wb_music_beat_scheme_name"
        ),
    )
    op.create_index(
        "ix_wb_music_beat_scheme_status",
        "wb_music_beat_schemes",
        ["music_resource_id", "status"],
    )
    op.create_table(
        "wb_voice_presets",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("provider", sa.String(length=80), nullable=False),
        sa.Column("model", sa.String(length=160), nullable=False),
        sa.Column("voice_key", sa.String(length=200), nullable=False),
        sa.Column("speed", sa.Float(), nullable=False),
        sa.Column("emotion", sa.String(length=80), nullable=False),
        sa.Column("intensity", sa.Float(), nullable=False),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_wb_voice_preset_name"),
    )
    op.create_index(
        "ix_wb_voice_preset_status", "wb_voice_presets", ["status", "name"]
    )
    op.create_table(
        "wb_production_plans",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("framework_id", sa.String(length=32), nullable=False),
        sa.Column("framework_version", sa.Integer(), nullable=False),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_by", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["product_id"], ["wb_products.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["framework_id"], ["wb_production_templates.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["wb_users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_wb_production_plan_status_created",
        "wb_production_plans",
        ["status", "created_at"],
    )

    op.add_column(
        "wb_production_mixes",
        sa.Column("plan_id", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "wb_production_mixes",
        sa.Column("final_title", sa.Text(), nullable=False, server_default=""),
    )
    op.add_column(
        "wb_production_mixes",
        sa.Column("normalized_title", sa.Text(), nullable=False, server_default=""),
    )
    op.add_column(
        "wb_production_mixes",
        sa.Column(
            "performance_status",
            sa.String(length=20),
            nullable=False,
            server_default="observing",
        ),
    )
    op.add_column(
        "wb_production_mixes",
        sa.Column("performance_marked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "wb_production_mixes",
        sa.Column("hot_share_url", sa.Text(), nullable=False, server_default=""),
    )
    op.add_column(
        "wb_production_mixes",
        sa.Column(
            "similarity_status",
            sa.String(length=20),
            nullable=False,
            server_default="pending",
        ),
    )
    op.add_column(
        "wb_production_mixes",
        sa.Column(
            "similarity_max_ratio",
            sa.Float(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "wb_production_mixes",
        sa.Column(
            "similarity_ignored",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.create_foreign_key(
        "fk_wb_production_mixes_plan",
        "wb_production_mixes",
        "wb_production_plans",
        ["plan_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_wb_production_mix_normalized_title",
        "wb_production_mixes",
        ["normalized_title"],
    )
    op.create_table(
        "wb_similarity_checks",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("mix_id", sa.String(length=32), nullable=False),
        sa.Column("compared_mix_id", sa.String(length=32), nullable=False),
        sa.Column("reused_duration_seconds", sa.Float(), nullable=False),
        sa.Column("reuse_ratio", sa.Float(), nullable=False),
        sa.Column("threshold", sa.Float(), nullable=False),
        sa.Column("visual_threshold", sa.Float(), nullable=False),
        sa.Column("matches", sa.JSON(), nullable=False),
        sa.Column("is_warning", sa.Boolean(), nullable=False),
        sa.Column("dismissed", sa.Boolean(), nullable=False),
        sa.Column("dismissal_reason", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["mix_id"], ["wb_production_mixes.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["compared_mix_id"], ["wb_production_mixes.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_wb_similarity_check_mix_created",
        "wb_similarity_checks",
        ["mix_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_wb_similarity_check_mix_created", table_name="wb_similarity_checks"
    )
    op.drop_table("wb_similarity_checks")
    op.drop_index(
        "ix_wb_production_mix_normalized_title", table_name="wb_production_mixes"
    )
    op.drop_constraint(
        "fk_wb_production_mixes_plan", "wb_production_mixes", type_="foreignkey"
    )
    for column in (
        "similarity_ignored",
        "similarity_max_ratio",
        "similarity_status",
        "hot_share_url",
        "performance_marked_at",
        "performance_status",
        "normalized_title",
        "final_title",
        "plan_id",
    ):
        op.drop_column("wb_production_mixes", column)
    op.drop_index(
        "ix_wb_production_plan_status_created", table_name="wb_production_plans"
    )
    op.drop_table("wb_production_plans")
    op.drop_index("ix_wb_voice_preset_status", table_name="wb_voice_presets")
    op.drop_table("wb_voice_presets")
    op.drop_index(
        "ix_wb_music_beat_scheme_status", table_name="wb_music_beat_schemes"
    )
    op.drop_table("wb_music_beat_schemes")
    op.drop_index(
        "ix_wb_title_strategy_status_sort", table_name="wb_title_strategies"
    )
    op.drop_table("wb_title_strategies")
    op.drop_column("wb_products", "non_hot_after_days")
    op.drop_column("wb_products", "output_naming_rule")
    op.drop_column("wb_shot_tags", "sort_order")
    op.drop_column("wb_shot_tags", "category")
