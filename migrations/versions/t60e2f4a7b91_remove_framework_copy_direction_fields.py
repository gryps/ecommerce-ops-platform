"""remove redundant framework copy direction fields

Revision ID: t60e2f4a7b91
Revises: s59d1e3f6a80
Create Date: 2026-07-29
"""

from __future__ import annotations

import json

from alembic import op
import sqlalchemy as sa


revision = "t60e2f4a7b91"
down_revision = "s59d1e3f6a80"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    rows = bind.execute(
        sa.text("SELECT id, config FROM wb_production_templates")
    ).mappings()
    for row in rows:
        config = row["config"]
        if isinstance(config, str):
            config = json.loads(config)
        if not isinstance(config, dict):
            continue
        copywriting = config.get("copywriting")
        if not isinstance(copywriting, dict):
            continue
        changed = False
        for key in ("title_semantic_type_id", "subtitle_semantic_type_id"):
            if key in copywriting:
                copywriting.pop(key)
                changed = True
        if not changed:
            continue
        config["copywriting"] = copywriting
        bind.execute(
            sa.text(
                "UPDATE wb_production_templates "
                "SET config = :config WHERE id = :template_id"
            ).bindparams(
                sa.bindparam("config", type_=sa.JSON()),
            ),
            {"config": config, "template_id": row["id"]},
        )


def downgrade() -> None:
    # Removed direction values duplicated content metadata and cannot be
    # reconstructed reliably. Content records remain unchanged.
    pass
