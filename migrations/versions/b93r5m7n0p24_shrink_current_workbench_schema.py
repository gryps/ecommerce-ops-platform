"""shrink the workbench schema to the current human-first workflow

Revision ID: b93r5m7n0p24
Revises: a82q4l6n9p13
Create Date: 2026-08-02
"""

from alembic import op


revision = "b93r5m7n0p24"
down_revision = "a82q4l6n9p13"
branch_labels = None
depends_on = None


RETIRED_TABLES = (
    "wb_copy_hot_events",
    "wb_framework_copy_combinations",
    "wb_framework_music_links",
    "wb_production_mix_clips",
    "wb_similarity_checks",
    "wb_production_mixes",
    "wb_production_plans",
    "wb_music_beat_schemes",
    "wb_voice_presets",
    "wb_product_shot_tags",
    "wb_media_asset_backgrounds",
    "wb_product_background_groups",
    "wb_candidate_segment_tags",
    "wb_candidate_segments",
    "wb_media_quality_issues",
    "wb_background_tone_groups",
    "wb_production_templates",
    "wb_copy_generation_batches",
    "wb_copy_inventory_policies",
    "wb_copy_prompt_versions",
    "wb_copy_semantic_types",
    "wb_media_asset_products",
    "wb_material_batches",
    "wb_jobs",
    "wb_storage_volumes",
)


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        raise RuntimeError("当前精简迁移仅支持正式部署使用的 PostgreSQL")

    # Preserve only classified assets that have a current confirmed product.
    op.execute("ALTER TABLE wb_media_assets ADD COLUMN IF NOT EXISTS product_id INTEGER")
    op.execute("ALTER TABLE wb_media_assets ADD COLUMN IF NOT EXISTS original_source_path TEXT")
    op.execute(
        "ALTER TABLE wb_media_assets ADD COLUMN IF NOT EXISTS duration_seconds DOUBLE PRECISION DEFAULT 0 NOT NULL"
    )
    op.execute("ALTER TABLE wb_media_assets ADD COLUMN IF NOT EXISTS width INTEGER DEFAULT 0 NOT NULL")
    op.execute("ALTER TABLE wb_media_assets ADD COLUMN IF NOT EXISTS height INTEGER DEFAULT 0 NOT NULL")
    op.execute(
        """
        UPDATE wb_media_assets asset
        SET product_id = assignment.product_id
        FROM wb_media_asset_products assignment
        WHERE assignment.asset_id = asset.id
          AND assignment.status = 'confirmed'
        """
    )
    op.execute(
        """
        UPDATE wb_media_assets
        SET original_source_path = COALESCE(
                NULLIF(media_metadata->>'original_source_path', ''), source_path
            ),
            duration_seconds = COALESCE(
                NULLIF(media_metadata->>'duration_seconds', '')::DOUBLE PRECISION, 0
            ),
            width = COALESCE(NULLIF(media_metadata->>'width', '')::INTEGER, 0),
            height = COALESCE(NULLIF(media_metadata->>'height', '')::INTEGER, 0)
        """
    )
    op.execute("DELETE FROM wb_media_assets WHERE product_id IS NULL")

    # Replace title strategy JSON metadata with a real relation and discard archived copies.
    op.execute("ALTER TABLE wb_copy_contents ADD COLUMN IF NOT EXISTS strategy_id VARCHAR(32)")
    op.execute(
        """
        UPDATE wb_copy_contents content
        SET strategy_id = strategy.id
        FROM wb_title_strategies strategy
        WHERE content.rhythm_spec->>'title_strategy_id' = strategy.id
        """
    )

    # Replace duplicated category names with a stable category foreign key.
    op.execute("ALTER TABLE wb_shot_tags ADD COLUMN IF NOT EXISTS category_id VARCHAR(32)")
    op.execute(
        """
        UPDATE wb_shot_tags tag
        SET category_id = category.id
        FROM wb_tag_categories category
        WHERE category.name = tag.category
        """
    )
    op.execute("DELETE FROM wb_shot_tags WHERE category_id IS NULL")

    # Retired records are intentionally removed; historical Alembic files remain intact.
    for table_name in RETIRED_TABLES:
        op.execute(f"DROP TABLE IF EXISTS {table_name} CASCADE")

    op.execute("DELETE FROM wb_copy_contents WHERE unit_type <> 'title' OR status = 'archived'")

    op.execute("ALTER TABLE wb_products DROP COLUMN IF EXISTS brand CASCADE")
    op.execute("ALTER TABLE wb_products DROP COLUMN IF EXISTS model_number CASCADE")
    op.execute("ALTER TABLE wb_products DROP COLUMN IF EXISTS description CASCADE")
    op.execute("ALTER TABLE wb_products DROP COLUMN IF EXISTS selling_points CASCADE")
    op.execute("ALTER TABLE wb_products DROP COLUMN IF EXISTS output_naming_rule CASCADE")
    op.execute("ALTER TABLE wb_products DROP COLUMN IF EXISTS non_hot_after_days CASCADE")
    op.execute("ALTER TABLE wb_products DROP COLUMN IF EXISTS merged_into_id CASCADE")

    op.execute(
        "ALTER TABLE wb_shot_tags DROP CONSTRAINT IF EXISTS uq_wb_shot_tags_category_name"
    )
    op.execute("ALTER TABLE wb_shot_tags DROP COLUMN IF EXISTS category CASCADE")
    op.execute("ALTER TABLE wb_shot_tags DROP COLUMN IF EXISTS sort_order CASCADE")
    op.execute("ALTER TABLE wb_shot_tags DROP COLUMN IF EXISTS is_system CASCADE")
    op.execute("ALTER TABLE wb_shot_tags DROP COLUMN IF EXISTS is_active CASCADE")
    op.execute("ALTER TABLE wb_shot_tags ALTER COLUMN category_id SET NOT NULL")
    op.execute(
        """
        ALTER TABLE wb_shot_tags
        ADD CONSTRAINT fk_wb_shot_tags_category
        FOREIGN KEY (category_id) REFERENCES wb_tag_categories(id) ON DELETE CASCADE
        """
    )
    op.execute(
        """
        ALTER TABLE wb_shot_tags
        ADD CONSTRAINT uq_wb_shot_tags_category_name
        UNIQUE (category_id, normalized_name)
        """
    )
    op.execute(
        "CREATE INDEX ix_wb_shot_tags_category_name ON wb_shot_tags (category_id, name)"
    )

    op.execute("DROP INDEX IF EXISTS ix_wb_media_assets_batch_status")
    op.execute(
        "ALTER TABLE wb_media_assets DROP CONSTRAINT IF EXISTS uq_wb_media_asset_batch_path"
    )
    for column_name in (
        "batch_id",
        "relative_path",
        "extension",
        "file_size",
        "modified_ns",
        "source_signature",
        "media_metadata",
        "quality_review_status",
        "quality_review_note",
        "quality_reviewed_at",
    ):
        op.execute(
            f"ALTER TABLE wb_media_assets DROP COLUMN IF EXISTS {column_name} CASCADE"
        )
    op.execute("ALTER TABLE wb_media_assets ALTER COLUMN product_id SET NOT NULL")
    op.execute("ALTER TABLE wb_media_assets ALTER COLUMN original_source_path SET NOT NULL")
    op.execute(
        """
        ALTER TABLE wb_media_assets
        ADD CONSTRAINT fk_wb_media_assets_product
        FOREIGN KEY (product_id) REFERENCES wb_products(id) ON DELETE CASCADE
        """
    )
    op.execute(
        "CREATE INDEX ix_wb_media_assets_product_created ON wb_media_assets (product_id, created_at)"
    )

    op.execute("DROP INDEX IF EXISTS ix_wb_copy_contents_inventory")
    op.execute("DROP INDEX IF EXISTS ix_wb_copy_contents_created")
    for column_name in (
        "lineage_id",
        "version",
        "unit_type",
        "scope",
        "title_semantic_type_id",
        "subtitle_semantic_type_id",
        "subtitle_segments",
        "rhythm_spec",
        "generation_batch_id",
        "prompt_version_id",
        "normalized_subtitle",
        "duplicate_of_id",
        "adoption_note",
        "last_used_at",
        "usage_count",
    ):
        op.execute(
            f"ALTER TABLE wb_copy_contents DROP COLUMN IF EXISTS {column_name} CASCADE"
        )
    op.execute(
        """
        ALTER TABLE wb_copy_contents
        ADD CONSTRAINT fk_wb_copy_contents_strategy
        FOREIGN KEY (strategy_id) REFERENCES wb_title_strategies(id) ON DELETE SET NULL
        """
    )
    op.execute(
        "CREATE INDEX ix_wb_copy_contents_status_created ON wb_copy_contents (status, created_at)"
    )
    op.execute(
        "CREATE INDEX ix_wb_copy_contents_product_created ON wb_copy_contents (product_id, created_at)"
    )

    for column_name in ("bpm", "beat_times", "waveform_peaks", "analysis", "rights_metadata"):
        op.execute(
            f"ALTER TABLE wb_music_resources DROP COLUMN IF EXISTS {column_name} CASCADE"
        )

    op.execute("ALTER TABLE wb_narration_assets DROP COLUMN IF EXISTS voice_preset_id CASCADE")

    op.execute("DROP INDEX IF EXISTS ix_wb_title_strategy_status_sort")
    op.execute("ALTER TABLE wb_title_strategies DROP COLUMN IF EXISTS description CASCADE")
    op.execute("ALTER TABLE wb_title_strategies DROP COLUMN IF EXISTS sort_order CASCADE")
    op.execute(
        "CREATE INDEX ix_wb_title_strategy_status_name ON wb_title_strategies (status, name)"
    )

    # Remove unused connection fields, including historical secrets, from stored profiles.
    op.execute(
        """
        UPDATE wb_settings
        SET value = jsonb_set(
            value::jsonb,
            '{profiles}',
            COALESCE(
                (
                    SELECT jsonb_agg(
                        profile
                        - 'provider'
                        - 'create_endpoint'
                        - 'query_endpoint'
                        - 'system_prompt'
                        - 'api_secret'
                        - 'has_api_secret'
                        - 'api_secret_mask'
                    )
                    FROM jsonb_array_elements(value::jsonb->'profiles') profile
                ),
                '[]'::jsonb
            )
        )::json,
        updated_at = now()
        WHERE key = 'model_profiles'
          AND jsonb_typeof(value::jsonb->'profiles') = 'array'
        """
    )


def downgrade() -> None:
    # Retired business data and fields are intentionally not reconstructed.
    pass
