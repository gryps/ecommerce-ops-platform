"""add product-scoped shot tag assignments

Revision ID: z60o2j4k7l91
Revises: z59n1i3j6k80
Create Date: 2026-07-31
"""

import sqlalchemy as sa
from alembic import op


revision = "z60o2j4k7l91"
down_revision = "z59n1i3j6k80"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "wb_product_shot_tags",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("tag_id", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["product_id"], ["wb_products.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["tag_id"], ["wb_shot_tags.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "product_id", "tag_id", name="uq_wb_product_shot_tag"
        ),
    )
    op.create_index(
        "ix_wb_product_shot_tags_product",
        "wb_product_shot_tags",
        ["product_id"],
        unique=False,
    )
    # Preserve the currently available preset tags for every existing product.
    op.execute(
        """
        INSERT INTO wb_product_shot_tags (id, product_id, tag_id, created_at)
        SELECT md5(random()::text || clock_timestamp()::text || p.id::text || t.id),
               p.id, t.id, CURRENT_TIMESTAMP
        FROM wb_products p
        CROSS JOIN wb_shot_tags t
        WHERE p.status = 'active' AND t.is_active = TRUE
        """
    )


def downgrade() -> None:
    op.drop_index(
        "ix_wb_product_shot_tags_product",
        table_name="wb_product_shot_tags",
    )
    op.drop_table("wb_product_shot_tags")
