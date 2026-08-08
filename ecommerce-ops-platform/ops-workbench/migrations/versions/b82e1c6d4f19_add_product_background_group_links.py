"""add product background group links

Revision ID: b82e1c6d4f19
Revises: a71d9f4c2e08
Create Date: 2026-07-26 09:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b82e1c6d4f19"
down_revision: Union[str, Sequence[str], None] = "a71d9f4c2e08"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "wb_product_background_groups",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("background_group_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["wb_products.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["background_group_id"],
            ["wb_background_tone_groups.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "product_id",
            "background_group_id",
            name="uq_wb_product_background_group",
        ),
    )
    op.create_index(
        "ix_wb_product_background_groups_product",
        "wb_product_background_groups",
        ["product_id"],
    )
    op.create_index(
        "ix_wb_product_background_groups_group",
        "wb_product_background_groups",
        ["background_group_id"],
    )
    op.execute(
        """
        INSERT INTO wb_product_background_groups
            (product_id, background_group_id, created_at)
        SELECT product_id, id, created_at
        FROM wb_background_tone_groups
        """
    )


def downgrade() -> None:
    op.drop_index(
        "ix_wb_product_background_groups_group",
        table_name="wb_product_background_groups",
    )
    op.drop_index(
        "ix_wb_product_background_groups_product",
        table_name="wb_product_background_groups",
    )
    op.drop_table("wb_product_background_groups")
