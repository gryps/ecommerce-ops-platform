from __future__ import annotations
import re
import shutil
import uuid
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Literal
from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session
from app.config import settings
from app.ai import load_model_profiles
from app.core.database import session_scope
from app.core.security import utc_now
from app.domain.models import AdminUser, CopyAnalysisRecord, CopyCandidate, CopyContent, CopyIterationBatch, JianyingDraft, MediaAsset, MediaAssetTag, NarrationAsset, Product, ShotTag, TagCategory, VoicePreviewAsset
from app.services.auth import require_admin
from app.services.audit import record_audit
from app.text_normalization import normalize_copy_text, normalize_tag_name
from app.services.jianying_drafts import create_jianying_draft, detect_jianying_draft_directory, duplicate_jianying_draft_usage_count, reset_jianying_draft_duplicate_counter, save_jianying_draft_directory
from app.services.material_classification_move import ClassificationItem, classify_and_move_originals
from app.services.operation_state import begin_operation, finish_operation, get_operation
from app.services.copywriting import analyze_and_generate_copies, continue_copy_iteration
from app.services.speech_recognition import recognize_narration_audio
from app.services.speech_synthesis import generate_narration_audio, generated_subtitle_cues
from app.services.music_resources import prepare_shared_audio, prepare_uploaded_audio
from app.services.source_directory_preview import resolve_source_image, select_native_image_files, select_native_source_files
from app.services.voice_catalog import CATALOG_MODEL, voice_catalog_item, voice_catalog_page

def _start_tracked_operation(operation_id: object, kind: str) -> str:
    value = operation_id.strip() if isinstance(operation_id, str) else ''
    if not value:
        value = uuid.uuid4().hex
    if len(value) > 80 or not re.fullmatch(r'[A-Za-z0-9_-]+', value):
        raise HTTPException(status_code=400, detail='操作编号无效')
    try:
        begin_operation(value, kind)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return value

class MaterialClassificationItemPayload(BaseModel):
    source_path: str = Field(min_length=1, max_length=4000)
    tag_ids: list[str] = Field(min_length=1, max_length=30)

class MaterialClassificationPayload(BaseModel):
    product_id: int
    source_dir: str = Field(min_length=1, max_length=4000)
    items: list[MaterialClassificationItemPayload] = Field(min_length=1, max_length=5000)

class SourceDirectorySelectPayload(BaseModel):
    initial_path: str = Field(default='', max_length=2000)

class SourceImagePreviewPayload(BaseModel):
    path: str = Field(min_length=1, max_length=4000)

class ProductTagPayload(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    category_id: str = Field(min_length=1, max_length=32)

class MasterNamePayload(BaseModel):
    name: str = Field(min_length=1, max_length=160)

class CopyIterationPayload(BaseModel):
    reference_text: str = Field(default='', max_length=20000)

class CopyReviewPayload(BaseModel):
    status: Literal['adopted', 'not_adopted']
    reason: str = Field(default='', max_length=2000)

class CopyLibraryPayload(BaseModel):
    content: str = Field(min_length=1, max_length=20000)
    product_id: int | None = None

class ModelNarrationPayload(BaseModel):
    approved_text: str = Field(min_length=1, max_length=20000)
    text_source: Literal['human', 'model'] = 'human'
    voice_sequence: int = Field(ge=1, le=597)

class VoicePreviewPayload(BaseModel):
    voice_sequence: int = Field(ge=1, le=597)

class NarrationConfirmPayload(BaseModel):
    approved_text: str = Field(min_length=1, max_length=20000)
    subtitle_cues: list[dict[str, Any]] = Field(default_factory=list, max_length=1000)

class JianyingDraftCreatePayload(BaseModel):
    name: str = Field(default='', max_length=200)
    destination_dir: str = Field(min_length=1, max_length=4000)
    copy_content_id: str | None = None
    narration_asset_id: str | None = None
    music_resource_id: str | None = None

class JianyingDraftDuplicatePayload(BaseModel):
    copy_content_id: str | None = None
    narration_asset_id: str | None = None
    music_resource_id: str | None = None

class JianyingDraftDirectoryPayload(BaseModel):
    path: str = Field(min_length=1, max_length=4000)

def _narration_dict(item: NarrationAsset) -> dict:
    return {'id': item.id, 'text_source': item.text_source, 'voice_source': item.voice_source, 'approved_text': item.approved_text, 'recognized_text': item.recognized_text, 'subtitle_cues': list(item.subtitle_cues or []), 'status': item.status, 'metadata': dict(item.metadata_json or {}), 'created_at': item.created_at, 'updated_at': item.updated_at}

def _validated_cues(cues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    previous_end = 0.0
    for raw in cues:
        text = str(raw.get('text') or '').strip()
        start = round(float(raw.get('start_seconds') or 0), 3)
        end = round(float(raw.get('end_seconds') or 0), 3)
        if not text or start < 0 or end <= start:
            raise ValueError('字幕时间轴包含无效片段')
        if start < previous_end - 0.001:
            raise ValueError('字幕时间轴不能重叠或逆序')
        result.append({'text': text, 'start_seconds': start, 'end_seconds': end})
        previous_end = end
    return result

def _tag_dict(tag: ShotTag, category_name: str = '') -> dict[str, Any]:
    return {'id': tag.id, 'name': tag.name, 'category': category_name, 'category_id': tag.category_id}

def _similarity(query: str, value: str) -> float:
    query_key = normalize_tag_name(query)
    value_key = normalize_tag_name(value)
    if not query_key:
        return 1.0
    if query_key in value_key:
        return 2.0 + len(query_key) / max(1, len(value_key))
    return SequenceMatcher(None, query_key, value_key).ratio()

def _category_dict(category: TagCategory) -> dict[str, Any]:
    return {'id': category.id, 'name': category.name, 'created_at': category.created_at}

def _classified_asset_dict(session: Session, asset: MediaAsset) -> dict[str, Any]:
    product = session.get(Product, asset.product_id)
    rows = session.execute(select(ShotTag, TagCategory.name).join(MediaAssetTag, MediaAssetTag.tag_id == ShotTag.id).join(TagCategory, TagCategory.id == ShotTag.category_id).where(MediaAssetTag.asset_id == asset.id).order_by(TagCategory.name, ShotTag.name)).all()
    return {'id': asset.id, 'product_id': product.id if product else None, 'product_name': product.name if product else '', 'filename': asset.filename, 'source_path': asset.source_path, 'original_source_path': asset.original_source_path, 'status': asset.status, 'duration_seconds': asset.duration_seconds, 'width': asset.width, 'height': asset.height, 'tags': [_tag_dict(tag, category_name) for tag, category_name in rows], 'created_at': asset.created_at}

def _library_copy_item(session: Session, item: CopyContent) -> dict[str, Any]:
    product = session.get(Product, item.product_id) if item.product_id else None
    return {'id': item.id, 'content': item.content_text, 'product_id': item.product_id, 'product_name': product.name if product else '', 'source': item.source, 'created_at': item.created_at, 'updated_at': item.updated_at}

def _candidate_item(item: CopyCandidate) -> dict[str, Any]:
    return {'id': item.id, 'content': item.content_text, 'status': item.status, 'rejection_reason': item.rejection_reason, 'library_content_id': item.library_content_id, 'created_at': item.created_at}

def _iteration_record(session: Session, record: CopyAnalysisRecord) -> dict[str, Any]:
    batches = session.scalars(select(CopyIterationBatch).where(CopyIterationBatch.analysis_record_id == record.id).order_by(CopyIterationBatch.sequence_number)).all()
    return {'id': record.id, 'source_mode': record.source_mode, 'source_text': record.source_text, 'language_analysis': dict(record.language_analysis or {}), 'audience_analysis': dict(record.audience_analysis or {}), 'expert_role': record.expert_role, 'created_at': record.created_at, 'batches': [{'id': batch.id, 'sequence_number': batch.sequence_number, 'created_at': batch.created_at, 'copies': [_candidate_item(item) for item in session.scalars(select(CopyCandidate).where(CopyCandidate.iteration_batch_id == batch.id).order_by(CopyCandidate.created_at)).all()]} for batch in batches]}

def _create_iteration_batch(session: Session, record: CopyAnalysisRecord, sequence: int, copies: list[str]) -> CopyIterationBatch:
    batch = CopyIterationBatch(analysis_record_id=record.id, sequence_number=sequence)
    session.add(batch)
    session.flush()
    for content in copies:
        session.add(CopyCandidate(iteration_batch_id=batch.id, content_text=content, status='pending'))
    session.flush()
    return batch


def _resolve_model_voice(voice_sequence: int, admin: AdminUser) -> tuple[str, dict[str, Any]]:
    item = get_voice_catalog_item(voice_sequence, _admin=admin)
    profile = next((row for row in load_model_profiles() if row.stage == 'speech_synthesis'), None)
    if profile is None or profile.model.casefold() != CATALOG_MODEL:
        raise HTTPException(status_code=409, detail=f'音色库适用于 {CATALOG_MODEL}，当前字幕配音模型不匹配')
    return str(item['voice']), item

def _jianying_draft_dict(session: Session, item: JianyingDraft) -> dict[str, Any]:
    return {'id': item.id, 'name': item.name, 'draft_path': item.draft_path, 'copy_content_id': item.copy_content_id, 'narration_asset_id': item.narration_asset_id, 'music_resource_id': item.music_resource_id, 'snapshot': dict(item.snapshot or {}), 'status': item.status, 'error': item.error, 'created_at': item.created_at, 'updated_at': item.updated_at}


__all__ = [name for name in globals() if not name.startswith('__')]
