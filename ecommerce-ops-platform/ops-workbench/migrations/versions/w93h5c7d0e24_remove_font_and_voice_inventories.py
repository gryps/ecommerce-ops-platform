"""remove font and voice inventories

Revision ID: w93h5c7d0e24
Revises: v82g4b6c9d13
Create Date: 2026-07-29
"""

from __future__ import annotations

import json

from alembic import op
import sqlalchemy as sa


revision = "w93h5c7d0e24"
down_revision = "v82g4b6c9d13"
branch_labels = None
depends_on = None


def _as_dict(value) -> dict:
    if isinstance(value, str):
        value = json.loads(value)
    return dict(value) if isinstance(value, dict) else {}


def upgrade() -> None:
    bind = op.get_bind()
    fonts = {
        row["id"]: row
        for row in bind.execute(
            sa.text("SELECT id, family, file_path FROM wb_font_resources")
        ).mappings()
    }
    templates = bind.execute(
        sa.text("SELECT id, config FROM wb_production_templates")
    ).mappings()
    for row in templates:
        config = _as_dict(row["config"])
        config.pop("voice_resource_id", None)
        text_styles = _as_dict(config.get("text_styles"))
        for kind in ("title", "subtitle"):
            style = _as_dict(text_styles.get(kind))
            font = fonts.get(str(style.pop("font_resource_id", "") or ""))
            if font:
                style.setdefault("font_family", font["family"] or "")
                style.setdefault("font_file_path", font["file_path"] or "")
            if not style.get("font_family") and not style.get("font_file_path"):
                style["font_family"] = "Noto Sans CJK SC"
                style["font_file_path"] = ""
            text_styles[kind] = style
        config["text_styles"] = text_styles
        bind.execute(
            sa.text(
                "UPDATE wb_production_templates SET config = :config WHERE id = :id"
            ).bindparams(sa.bindparam("config", type_=sa.JSON())),
            {"config": config, "id": row["id"]},
        )

    op.drop_index("ix_wb_voice_resources_status_name", table_name="wb_voice_resources")
    op.drop_table("wb_voice_resources")
    op.drop_index("ix_wb_font_resources_status_name", table_name="wb_font_resources")
    op.drop_table("wb_font_resources")


def downgrade() -> None:
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
        "wb_font_resources",
        ["status", "name"],
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
        sa.UniqueConstraint(
            "provider",
            "voice_key",
            name="uq_wb_voice_provider_key",
        ),
    )
    op.create_index(
        "ix_wb_voice_resources_status_name",
        "wb_voice_resources",
        ["status", "name"],
    )
