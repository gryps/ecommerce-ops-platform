"""remove derived fields from stored model profiles

Revision ID: c04s6n8p1q35
Revises: b93r5m7n0p24
Create Date: 2026-08-02
"""

from alembic import op


revision = "c04s6n8p1q35"
down_revision = "b93r5m7n0p24"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE wb_settings
        SET value = jsonb_set(
            value::jsonb,
            '{profiles}',
            COALESCE(
                (
                    SELECT jsonb_agg(
                        profile - 'label' - 'has_api_key' - 'api_key_mask'
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
    pass
