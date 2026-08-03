"""add mix framework library

Revision ID: p26a8b0c3d57
Revises: o15f7a9b2c46
Create Date: 2026-07-28
"""

from alembic import op
import sqlalchemy as sa


revision = "p26a8b0c3d57"
down_revision = "o15f7a9b2c46"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The project had not entered production when the framework model was
    # redesigned. Remove only the obsolete production/copy chain; product,
    # material and reusable resource records are deliberately preserved.
    connection = op.get_bind()
    for table_name in (
        "wb_copy_hot_events",
        "wb_copy_usage_events",
        "wb_copy_usage_reservations",
        "wb_production_mix_clips",
        "wb_production_mixes",
        "wb_copy_generation_batches",
        "wb_copy_inventory_policies",
        "wb_copy_contents",
        "wb_copy_prompt_versions",
        "wb_copy_semantic_types",
        "wb_production_templates",
        "wb_model_call_logs",
        "wb_model_call_daily_summaries",
    ):
        connection.execute(sa.text(f"DELETE FROM {table_name}"))
    connection.execute(
        sa.text(
            "DELETE FROM wb_jobs "
            "WHERE job_type IN ('copywriting.generate_contents', 'production_mix.render')"
        )
    )
    op.add_column(
        "wb_music_resources",
        sa.Column("analysis", sa.JSON(), nullable=False, server_default="{}"),
    )
    op.add_column(
        "wb_music_resources",
        sa.Column("rights_metadata", sa.JSON(), nullable=False, server_default="{}"),
    )
    op.create_table(
        "wb_font_resources",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("family", sa.String(length=160), nullable=False),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=30), nullable=False),
        sa.Column("rights_confirmed", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_wb_font_resources_status_name",
        "wb_font_resources", ["status", "name"],
    )
    op.create_table(
        "wb_voice_resources",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("provider", sa.String(length=80), nullable=False),
        sa.Column("model", sa.String(length=160), nullable=False),
        sa.Column("voice_key", sa.String(length=200), nullable=False),
        sa.Column("languages", sa.JSON(), nullable=False),
        sa.Column("preview_path", sa.Text(), nullable=False),
        sa.Column("rights_confirmed", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "voice_key", name="uq_wb_voice_provider_key"),
    )
    op.create_index(
        "ix_wb_voice_resources_status_name",
        "wb_voice_resources", ["status", "name"],
    )
    op.create_table(
        "wb_framework_copy_combinations",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("framework_id", sa.String(length=32), nullable=False),
        sa.Column("title_content_id", sa.String(length=32), nullable=True),
        sa.Column("narration_content_id", sa.String(length=32), nullable=True),
        sa.Column("product_id", sa.Integer(), nullable=True),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("validation", sa.JSON(), nullable=False),
        sa.Column("approved_artifact", sa.JSON(), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("usage_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["framework_id"], ["wb_production_templates.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["title_content_id"], ["wb_copy_contents.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["narration_content_id"], ["wb_copy_contents.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["product_id"], ["wb_products.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("framework_id", "sequence_number", name="uq_wb_framework_copy_sequence"),
    )
    op.create_index(
        "ix_wb_framework_copy_status_sequence",
        "wb_framework_copy_combinations",
        ["framework_id", "status", "sequence_number"],
    )
    op.create_table(
        "wb_framework_music_links",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("framework_id", sa.String(length=32), nullable=False),
        sa.Column("music_resource_id", sa.String(length=32), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("compatibility_score", sa.Float(), nullable=False),
        sa.Column("mismatch_reasons", sa.JSON(), nullable=False),
        sa.Column("segment_start_seconds", sa.Float(), nullable=False),
        sa.Column("segment_end_seconds", sa.Float(), nullable=False),
        sa.Column("framework_override", sa.JSON(), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["framework_id"], ["wb_production_templates.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["music_resource_id"], ["wb_music_resources.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("framework_id", "music_resource_id", name="uq_wb_framework_music_resource"),
        sa.UniqueConstraint("framework_id", "sequence_number", name="uq_wb_framework_music_sequence"),
    )
    op.create_index(
        "ix_wb_framework_music_status_sequence",
        "wb_framework_music_links",
        ["framework_id", "status", "sequence_number"],
    )


def downgrade() -> None:
    op.drop_index("ix_wb_framework_music_status_sequence", table_name="wb_framework_music_links")
    op.drop_table("wb_framework_music_links")
    op.drop_index("ix_wb_framework_copy_status_sequence", table_name="wb_framework_copy_combinations")
    op.drop_table("wb_framework_copy_combinations")
    op.drop_index("ix_wb_voice_resources_status_name", table_name="wb_voice_resources")
    op.drop_table("wb_voice_resources")
    op.drop_index("ix_wb_font_resources_status_name", table_name="wb_font_resources")
    op.drop_table("wb_font_resources")
    op.drop_column("wb_music_resources", "rights_metadata")
    op.drop_column("wb_music_resources", "analysis")
