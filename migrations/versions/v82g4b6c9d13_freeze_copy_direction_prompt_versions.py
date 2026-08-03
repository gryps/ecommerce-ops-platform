"""freeze copy direction prompt versions on generation batches

Revision ID: v82g4b6c9d13
Revises: u71f3a5b8c02
Create Date: 2026-07-29
"""

from datetime import datetime, timezone
import uuid

from alembic import op
import sqlalchemy as sa


revision = "v82g4b6c9d13"
down_revision = "u71f3a5b8c02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "wb_copy_generation_batches",
        sa.Column("prompt_version_id", sa.String(length=32), nullable=True),
    )
    op.create_foreign_key(
        "fk_wb_copy_generation_batch_prompt_version",
        "wb_copy_generation_batches",
        "wb_copy_prompt_versions",
        ["prompt_version_id"],
        ["id"],
        ondelete="SET NULL",
    )

    bind = op.get_bind()
    semantics = bind.execute(
        sa.text(
            "SELECT semantic.id, semantic.description "
            "FROM wb_copy_semantic_types AS semantic "
            "WHERE NOT EXISTS ("
            "SELECT 1 FROM wb_copy_prompt_versions AS prompt "
            "WHERE prompt.semantic_type_id = semantic.id"
            ")"
        )
    ).mappings()
    now = datetime.now(timezone.utc)
    for semantic in semantics:
        bind.execute(
            sa.text(
                "INSERT INTO wb_copy_prompt_versions "
                "(id, semantic_type_id, version, prompt, status, created_at) "
                "VALUES (:id, :semantic_type_id, 1, :prompt, 'active', :created_at)"
            ),
            {
                "id": uuid.uuid4().hex,
                "semantic_type_id": semantic["id"],
                "prompt": semantic["description"] or "",
                "created_at": now,
            },
        )


def downgrade() -> None:
    op.drop_constraint(
        "fk_wb_copy_generation_batch_prompt_version",
        "wb_copy_generation_batches",
        type_="foreignkey",
    )
    op.drop_column("wb_copy_generation_batches", "prompt_version_id")
