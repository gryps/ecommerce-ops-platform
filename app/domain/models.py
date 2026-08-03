from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.security import utc_now


def uuid_hex() -> str:
    return uuid.uuid4().hex


class AdminUser(Base):
    __tablename__ = "wb_users"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uuid_hex)
    username: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    sessions: Mapped[list["AuthSession"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class AuthSession(Base):
    __tablename__ = "wb_auth_sessions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uuid_hex)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("wb_users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    user: Mapped[AdminUser] = relationship(back_populates="sessions")


class AuditEvent(Base):
    __tablename__ = "wb_audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    actor_id: Mapped[str | None] = mapped_column(
        ForeignKey("wb_users.id", ondelete="SET NULL")
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    object_type: Mapped[str] = mapped_column(String(80), nullable=False)
    object_id: Mapped[str] = mapped_column(String(80), nullable=False)
    before: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    after: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    reason: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, index=True
    )


class WorkbenchSetting(Base):
    __tablename__ = "wb_settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class ModelCallLog(Base):
    __tablename__ = "wb_model_call_logs"
    __table_args__ = (
        Index("ix_wb_model_call_logs_stage_created", "stage", "created_at"),
        Index("ix_wb_model_call_logs_call_id", "call_id"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uuid_hex)
    call_id: Mapped[str] = mapped_column(String(32), nullable=False, default=uuid_hex)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    stage: Mapped[str] = mapped_column(String(80), nullable=False)
    label: Mapped[str] = mapped_column(String(160), nullable=False, default="")
    provider: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    model: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    business_step: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    business_objects: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, nullable=False, default=list
    )
    input_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    output_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    total_tokens: Mapped[int | None] = mapped_column(Integer)
    token_usage_reported: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ModelCallDailySummary(Base):
    __tablename__ = "wb_model_call_daily_summaries"
    __table_args__ = (
        UniqueConstraint("stat_date", "stage", name="uq_wb_model_call_daily_stage"),
        Index("ix_wb_model_call_daily_stage_date", "stage", "stat_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stat_date: Mapped[date] = mapped_column(Date, nullable=False)
    stage: Mapped[str] = mapped_column(String(80), nullable=False)
    successful_calls: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_calls: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    input_tokens: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    total_tokens: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    token_reported_calls: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_duration_ms: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class Product(Base):
    __tablename__ = "wb_products"
    __table_args__ = (Index("ix_wb_products_status_name", "status", "name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class TagCategory(Base):
    __tablename__ = "wb_tag_categories"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uuid_hex)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class ShotTag(Base):
    __tablename__ = "wb_shot_tags"
    __table_args__ = (
        UniqueConstraint(
            "category_id", "normalized_name", name="uq_wb_shot_tags_category_name"
        ),
        Index("ix_wb_shot_tags_category_name", "category_id", "name"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uuid_hex)
    category_id: Mapped[str] = mapped_column(
        ForeignKey("wb_tag_categories.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(80), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class MediaAsset(Base):
    __tablename__ = "wb_media_assets"
    __table_args__ = (
        Index("ix_wb_media_assets_product_created", "product_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uuid_hex)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("wb_products.id", ondelete="CASCADE"), nullable=False
    )
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    source_path: Mapped[str] = mapped_column(Text, nullable=False)
    original_source_path: Mapped[str] = mapped_column(Text, nullable=False)
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    width: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    height: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="classified")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class MediaAssetTag(Base):
    __tablename__ = "wb_media_asset_tags"
    __table_args__ = (
        UniqueConstraint("asset_id", "tag_id", name="uq_wb_media_asset_tag"),
        Index("ix_wb_media_asset_tags_asset", "asset_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asset_id: Mapped[str] = mapped_column(
        ForeignKey("wb_media_assets.id", ondelete="CASCADE"), nullable=False
    )
    tag_id: Mapped[str] = mapped_column(
        ForeignKey("wb_shot_tags.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class CopyAnalysisRecord(Base):
    __tablename__ = "wb_copy_analysis_records"
    __table_args__ = (Index("ix_wb_copy_analysis_created", "created_at"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uuid_hex)
    source_mode: Mapped[str] = mapped_column(String(20), nullable=False)
    source_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    language_analysis: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    audience_analysis: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    expert_role: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class CopyIterationBatch(Base):
    __tablename__ = "wb_copy_iteration_batches"
    __table_args__ = (
        UniqueConstraint(
            "analysis_record_id", "sequence_number", name="uq_wb_copy_batch_sequence"
        ),
        Index("ix_wb_copy_batch_record_sequence", "analysis_record_id", "sequence_number"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uuid_hex)
    analysis_record_id: Mapped[str] = mapped_column(
        ForeignKey("wb_copy_analysis_records.id", ondelete="CASCADE"), nullable=False
    )
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class CopyCandidate(Base):
    __tablename__ = "wb_copy_candidates"
    __table_args__ = (Index("ix_wb_copy_candidate_batch_created", "iteration_batch_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uuid_hex)
    iteration_batch_id: Mapped[str] = mapped_column(
        ForeignKey("wb_copy_iteration_batches.id", ondelete="CASCADE"), nullable=False
    )
    library_content_id: Mapped[str | None] = mapped_column(
        ForeignKey("wb_copy_contents.id", ondelete="SET NULL"), nullable=True
    )
    content_text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending")
    rejection_reason: Mapped[str] = mapped_column(Text, nullable=False, default="")
    reviewed_by: Mapped[str | None] = mapped_column(
        ForeignKey("wb_users.id", ondelete="SET NULL")
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class CopyContent(Base):
    __tablename__ = "wb_copy_contents"
    __table_args__ = (
        Index("ix_wb_copy_contents_product_created", "product_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uuid_hex)
    product_id: Mapped[int | None] = mapped_column(
        ForeignKey("wb_products.id", ondelete="CASCADE")
    )
    content_text: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_content: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(30), nullable=False, default="manual")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class MusicResource(Base):
    __tablename__ = "wb_music_resources"
    __table_args__ = (Index("ix_wb_music_resources_status_created", "status", "created_at"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uuid_hex)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    source_type: Mapped[str] = mapped_column(String(30), nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False, default="")
    file_path: Mapped[str] = mapped_column(Text, nullable=False, default="")
    rights_confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="processing")
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    custom_tags: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    error: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class NarrationAsset(Base):
    __tablename__ = "wb_narration_assets"
    __table_args__ = (Index("ix_wb_narration_asset_status_created", "status", "created_at"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uuid_hex)
    text_source: Mapped[str] = mapped_column(String(20), nullable=False, default="human")
    voice_source: Mapped[str] = mapped_column(String(20), nullable=False, default="human")
    approved_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    recognized_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    subtitle_cues: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, nullable=False, default=list
    )
    audio_path: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending_review")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class VoicePreviewAsset(Base):
    __tablename__ = "wb_voice_preview_assets"

    sequence: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    voice: Mapped[str] = mapped_column(String(240), nullable=False, unique=True)
    model: Mapped[str] = mapped_column(String(200), nullable=False)
    audio_path: Mapped[str] = mapped_column(Text, nullable=False)
    audio_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class JianyingDraft(Base):
    __tablename__ = "wb_jianying_drafts"
    __table_args__ = (Index("ix_wb_jianying_drafts_status_created", "status", "created_at"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uuid_hex)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    copy_content_id: Mapped[str | None] = mapped_column(
        ForeignKey("wb_copy_contents.id", ondelete="SET NULL")
    )
    narration_asset_id: Mapped[str | None] = mapped_column(
        ForeignKey("wb_narration_assets.id", ondelete="SET NULL")
    )
    music_resource_id: Mapped[str | None] = mapped_column(
        ForeignKey("wb_music_resources.id", ondelete="SET NULL")
    )
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="ready")
    draft_path: Mapped[str] = mapped_column(Text, nullable=False, default="")
    error: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_by: Mapped[str | None] = mapped_column(
        ForeignKey("wb_users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
