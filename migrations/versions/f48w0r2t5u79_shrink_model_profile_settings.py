"""remove retired model profile switches and voice IDs

Revision ID: f48w0r2t5u79
Revises: e37v9q1s4t68
Create Date: 2026-08-03
"""

from alembic import op


revision = "f48w0r2t5u79"
down_revision = "e37v9q1s4t68"
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
                    SELECT jsonb_agg(profile - 'enabled' - 'voice')
                    FROM jsonb_array_elements(value::jsonb -> 'profiles') AS profile
                ),
                '[]'::jsonb
            )
        )::json
        WHERE key = 'model_profiles'
          AND jsonb_typeof(value::jsonb -> 'profiles') = 'array'
        """
    )


def downgrade() -> None:
    raise RuntimeError("模型配置精简迁移不支持降级")
