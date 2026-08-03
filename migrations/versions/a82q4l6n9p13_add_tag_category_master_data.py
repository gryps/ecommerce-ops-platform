"""add editable tag category master data

Revision ID: a82q4l6n9p13
Revises: z71p3k5l8m02
Create Date: 2026-08-01
"""

import sqlalchemy as sa
from alembic import op


revision = "a82q4l6n9p13"
down_revision = "z71p3k5l8m02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "wb_tag_categories",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("normalized_name", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("normalized_name", name="uq_wb_tag_categories_normalized_name"),
    )
    op.execute(
        """
        INSERT INTO wb_tag_categories (id, name, normalized_name, created_at, updated_at)
        SELECT md5(category), category, lower(regexp_replace(category, '\\s+', '', 'g')), now(), now()
        FROM (SELECT DISTINCT category FROM wb_shot_tags WHERE category <> '') categories
        ON CONFLICT (normalized_name) DO NOTHING
        """
    )
    op.drop_constraint("uq_wb_shot_tags_normalized_name", "wb_shot_tags", type_="unique")
    op.create_unique_constraint(
        "uq_wb_shot_tags_category_name", "wb_shot_tags", ["category", "normalized_name"]
    )


def downgrade() -> None:
    # Keep the first tag if legacy-incompatible same-name tags exist in multiple categories.
    op.execute(
        """
        DELETE FROM wb_shot_tags a USING wb_shot_tags b
        WHERE a.normalized_name = b.normalized_name AND a.id > b.id
        """
    )
    op.drop_constraint("uq_wb_shot_tags_category_name", "wb_shot_tags", type_="unique")
    op.create_unique_constraint(
        "uq_wb_shot_tags_normalized_name", "wb_shot_tags", ["normalized_name"]
    )
    op.drop_table("wb_tag_categories")
