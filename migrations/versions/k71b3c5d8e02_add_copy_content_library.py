"""add independent copy content library

Revision ID: k71b3c5d8e02
Revises: j60a2b4c7d91
Create Date: 2026-07-27
"""

from alembic import op
import sqlalchemy as sa
import unicodedata
import uuid


revision = "k71b3c5d8e02"
down_revision = "j60a2b4c7d91"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "wb_copy_semantic_types",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("content_type", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("content_type", "name", name="uq_wb_copy_semantic_type_name"),
    )
    op.create_index(
        "ix_wb_copy_semantic_type_status", "wb_copy_semantic_types",
        ["content_type", "status"],
    )
    op.create_table(
        "wb_copy_prompt_versions",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("semantic_type_id", sa.String(length=32), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["semantic_type_id"], ["wb_copy_semantic_types.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "semantic_type_id", "version", name="uq_wb_copy_prompt_semantic_version"
        ),
    )
    op.create_table(
        "wb_copy_inventory_policies",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("scope", sa.String(length=20), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=True),
        sa.Column("unit_type", sa.String(length=20), nullable=False),
        sa.Column("semantic_type_id", sa.String(length=32), nullable=True),
        sa.Column("rhythm_key", sa.String(length=160), nullable=False),
        sa.Column("minimum_available", sa.Integer(), nullable=False),
        sa.Column("generation_batch_size", sa.Integer(), nullable=False),
        sa.Column("auto_replenish", sa.Boolean(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["wb_products.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["semantic_type_id"], ["wb_copy_semantic_types.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "scope", "product_id", "unit_type", "semantic_type_id", "rhythm_key",
            name="uq_wb_copy_inventory_policy_bucket",
        ),
    )
    op.create_table(
        "wb_copy_contents",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("lineage_id", sa.String(length=32), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("unit_type", sa.String(length=20), nullable=False),
        sa.Column("scope", sa.String(length=20), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=True),
        sa.Column("title_semantic_type_id", sa.String(length=32), nullable=True),
        sa.Column("subtitle_semantic_type_id", sa.String(length=32), nullable=True),
        sa.Column("title_text", sa.Text(), nullable=False),
        sa.Column("subtitle_segments", sa.JSON(), nullable=False),
        sa.Column("rhythm_spec", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("source", sa.String(length=30), nullable=False),
        sa.Column("generation_batch_id", sa.String(length=32), nullable=True),
        sa.Column("prompt_version_id", sa.String(length=32), nullable=True),
        sa.Column("normalized_title", sa.Text(), nullable=False),
        sa.Column("normalized_subtitle", sa.Text(), nullable=False),
        sa.Column("duplicate_of_id", sa.String(length=32), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=False),
        sa.Column("adoption_note", sa.Text(), nullable=False),
        sa.Column("reviewed_by", sa.String(length=32), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("usage_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["wb_products.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["title_semantic_type_id"], ["wb_copy_semantic_types.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["subtitle_semantic_type_id"], ["wb_copy_semantic_types.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["prompt_version_id"], ["wb_copy_prompt_versions.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["duplicate_of_id"], ["wb_copy_contents.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["reviewed_by"], ["wb_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_wb_copy_contents_inventory", "wb_copy_contents",
        ["status", "scope", "product_id", "unit_type"],
    )
    op.create_index(
        "ix_wb_copy_contents_created", "wb_copy_contents", ["created_at"]
    )
    _migrate_legacy_title_and_subtitle_contents()


def _normalized(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return "".join(
        char for char in normalized
        if not char.isspace() and not unicodedata.category(char).startswith(("P", "S"))
    )


def _migrate_legacy_title_and_subtitle_contents() -> None:
    connection = op.get_bind()
    templates = sa.table(
        "wb_production_templates",
        sa.column("id", sa.String()),
        sa.column("template_kind", sa.String()),
        sa.column("product_id", sa.Integer()),
        sa.column("config", sa.JSON()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    contents = sa.table(
        "wb_copy_contents",
        sa.column("id", sa.String()),
        sa.column("lineage_id", sa.String()),
        sa.column("version", sa.Integer()),
        sa.column("unit_type", sa.String()),
        sa.column("scope", sa.String()),
        sa.column("product_id", sa.Integer()),
        sa.column("title_semantic_type_id", sa.String()),
        sa.column("subtitle_semantic_type_id", sa.String()),
        sa.column("title_text", sa.Text()),
        sa.column("subtitle_segments", sa.JSON()),
        sa.column("rhythm_spec", sa.JSON()),
        sa.column("status", sa.String()),
        sa.column("source", sa.String()),
        sa.column("generation_batch_id", sa.String()),
        sa.column("prompt_version_id", sa.String()),
        sa.column("normalized_title", sa.Text()),
        sa.column("normalized_subtitle", sa.Text()),
        sa.column("duplicate_of_id", sa.String()),
        sa.column("rejection_reason", sa.Text()),
        sa.column("adoption_note", sa.Text()),
        sa.column("reviewed_by", sa.String()),
        sa.column("reviewed_at", sa.DateTime(timezone=True)),
        sa.column("last_used_at", sa.DateTime(timezone=True)),
        sa.column("usage_count", sa.Integer()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    rows = connection.execute(
        sa.select(templates).where(
            templates.c.template_kind.in_(["title", "subtitle"])
        )
    ).mappings()
    seen: set[tuple[str, int | None, str]] = set()
    inserts = []
    for row in rows:
        config = row["config"] or {}
        candidates = [config.get("original_text"), *(config.get("variants") or [])]
        for raw_text in candidates:
            text = str(raw_text or "").strip()
            normalized = _normalized(text)
            dedupe_key = (row["template_kind"], row["product_id"], normalized)
            if not text or not normalized or dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            is_title = row["template_kind"] == "title"
            content_id = uuid.uuid4().hex
            inserts.append({
                "id": content_id,
                "lineage_id": content_id,
                "version": 1,
                "unit_type": row["template_kind"],
                "scope": "product" if row["product_id"] else "global",
                "product_id": row["product_id"],
                "title_semantic_type_id": None,
                "subtitle_semantic_type_id": None,
                "title_text": text if is_title else "",
                "subtitle_segments": [] if is_title else [
                    {"text": text, "duration_ratio": 1.0}
                ],
                "rhythm_spec": {} if is_title else {"source": "legacy", "unclassified": True},
                "status": "adopted",
                "source": "legacy",
                "generation_batch_id": None,
                "prompt_version_id": None,
                "normalized_title": normalized if is_title else "",
                "normalized_subtitle": "" if is_title else normalized,
                "duplicate_of_id": None,
                "rejection_reason": "",
                "adoption_note": "由旧标题/字幕模板自动迁移",
                "reviewed_by": None,
                "reviewed_at": None,
                "last_used_at": None,
                "usage_count": 0,
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            })
    if inserts:
        connection.execute(sa.insert(contents), inserts)


def downgrade() -> None:
    op.drop_table("wb_copy_contents")
    op.drop_table("wb_copy_inventory_policies")
    op.drop_table("wb_copy_prompt_versions")
    op.drop_index(
        "ix_wb_copy_semantic_type_status", table_name="wb_copy_semantic_types"
    )
    op.drop_table("wb_copy_semantic_types")
