"""add copy semantic direction ordering

Revision ID: u71f3a5b8c02
Revises: t60e2f4a7b91
Create Date: 2026-07-29
"""

from alembic import op
import sqlalchemy as sa


revision = "u71f3a5b8c02"
down_revision = "t60e2f4a7b91"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "wb_copy_semantic_types",
        sa.Column(
            "sort_order",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            "SELECT id, content_type FROM wb_copy_semantic_types "
            "ORDER BY content_type, created_at, name"
        )
    ).mappings()
    next_order: dict[str, int] = {}
    for row in rows:
        content_type = row["content_type"]
        next_order[content_type] = next_order.get(content_type, 0) + 1
        bind.execute(
            sa.text(
                "UPDATE wb_copy_semantic_types "
                "SET sort_order = :sort_order WHERE id = :semantic_id"
            ),
            {
                "sort_order": next_order[content_type],
                "semantic_id": row["id"],
            },
        )
    op.alter_column(
        "wb_copy_semantic_types",
        "sort_order",
        server_default=None,
    )


def downgrade() -> None:
    op.drop_column("wb_copy_semantic_types", "sort_order")
