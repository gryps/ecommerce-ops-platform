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
router = APIRouter(prefix='/human', tags=['human-first-workflow'])

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


@router.get('/operation-status/{operation_id}')
def operation_status(operation_id: str, _admin: AdminUser=Depends(require_admin)) -> dict[str, Any]:
    state = get_operation(operation_id)
    if state is None:
        return {'operation_id': operation_id, 'kind': '', 'status': 'unknown', 'detail': ''}
    return {'operation_id': state.operation_id, 'kind': state.kind, 'status': state.status, 'detail': state.detail, 'updated_at': state.updated_at}

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

@router.delete('/products/{product_id}', status_code=status.HTTP_204_NO_CONTENT)
def delete_human_product(product_id: int, admin: AdminUser=Depends(require_admin)) -> None:
    """Remove a product from current classification data without touching files."""
    with session_scope() as session:
        product = session.get(Product, product_id)
        if product is None or product.status == 'deleted':
            raise HTTPException(status_code=404, detail='产品不存在')
        before_status = product.status
        session.execute(delete(MediaAsset).where(MediaAsset.product_id == product.id))
        session.execute(delete(CopyContent).where(CopyContent.product_id == product.id))
        product.status = 'deleted'
        product.updated_at = utc_now()
        record_audit(session, actor_id=admin.id, action='human_product.delete', object_type='product', object_id=str(product.id), before={'status': before_status, 'name': product.name}, after={'status': 'deleted', 'current_materials_and_titles_removed': True})

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

@router.get('/tag-categories')
def list_tag_categories(q: str='', limit: int=20, offset: int=0, _admin: AdminUser=Depends(require_admin)) -> dict[str, Any]:
    with session_scope() as session:
        categories = list(session.scalars(select(TagCategory).order_by(TagCategory.name)).all())
        if q.strip():
            categories = [item for item in categories if _similarity(q, item.name) >= 0.35]
            categories.sort(key=lambda item: (-_similarity(q, item.name), item.name))
        total = len(categories)
        rows = categories[max(0, offset):max(0, offset) + max(1, min(limit, 5000))]
        return {'items': [_category_dict(item) for item in rows], 'total': total}

@router.post('/tag-categories', status_code=status.HTTP_201_CREATED)
def create_tag_category(payload: MasterNamePayload, _admin: AdminUser=Depends(require_admin)) -> dict[str, Any]:
    name = ' '.join(payload.name.strip().split())
    normalized = normalize_tag_name(name)
    with session_scope() as session:
        if session.scalar(select(TagCategory).where(TagCategory.normalized_name == normalized)):
            raise HTTPException(status_code=409, detail='标签分类已存在')
        item = TagCategory(name=name, normalized_name=normalized)
        session.add(item)
        session.flush()
        return _category_dict(item)

@router.patch('/tag-categories/{category_id}')
def update_tag_category(category_id: str, payload: MasterNamePayload, _admin: AdminUser=Depends(require_admin)) -> dict[str, Any]:
    name = ' '.join(payload.name.strip().split())
    normalized = normalize_tag_name(name)
    with session_scope() as session:
        item = session.get(TagCategory, category_id)
        if item is None:
            raise HTTPException(status_code=404, detail='标签分类不存在')
        duplicate = session.scalar(select(TagCategory).where(TagCategory.normalized_name == normalized, TagCategory.id != item.id))
        if duplicate:
            raise HTTPException(status_code=409, detail='标签分类已存在')
        item.name = name
        item.normalized_name = normalized
        item.updated_at = utc_now()
        session.flush()
        return _category_dict(item)

@router.delete('/tag-categories/{category_id}', status_code=status.HTTP_204_NO_CONTENT)
def delete_tag_category(category_id: str, _admin: AdminUser=Depends(require_admin)) -> None:
    with session_scope() as session:
        item = session.get(TagCategory, category_id)
        if item is None:
            raise HTTPException(status_code=404, detail='标签分类不存在')
        session.delete(item)

@router.get('/tags')
def list_global_tags(category_id: str | None=None, q: str='', limit: int=20, offset: int=0, _admin: AdminUser=Depends(require_admin)) -> dict[str, Any]:
    with session_scope() as session:
        category = session.get(TagCategory, category_id) if category_id else None
        statement = select(ShotTag)
        if category_id and category is None:
            raise HTTPException(status_code=404, detail='标签分类不存在')
        if category:
            statement = statement.where(ShotTag.category_id == category.id)
        tags = list(session.scalars(statement.order_by(ShotTag.name)).all())
        if q.strip():
            tags = [item for item in tags if _similarity(q, item.name) >= 0.35]
            tags.sort(key=lambda item: (-_similarity(q, item.name), item.name))
        categories = {item.id: item.name for item in session.scalars(select(TagCategory)).all()}
        total = len(tags)
        rows = tags[max(0, offset):max(0, offset) + max(1, min(limit, 5000))]
        return {'items': [_tag_dict(item, categories.get(item.category_id, '')) for item in rows], 'total': total}

@router.patch('/tags/{tag_id}')
def update_global_tag(tag_id: str, payload: MasterNamePayload, _admin: AdminUser=Depends(require_admin)) -> dict[str, Any]:
    name = ' '.join(payload.name.strip().split())
    normalized = normalize_tag_name(name)
    with session_scope() as session:
        tag = session.get(ShotTag, tag_id)
        if tag is None:
            raise HTTPException(status_code=404, detail='标签不存在')
        duplicate = session.scalar(select(ShotTag).where(ShotTag.category_id == tag.category_id, ShotTag.normalized_name == normalized, ShotTag.id != tag.id))
        if duplicate:
            raise HTTPException(status_code=409, detail='当前分类下标签名称已存在')
        tag.name = name
        tag.normalized_name = normalized
        tag.updated_at = utc_now()
        category = session.get(TagCategory, tag.category_id)
        session.flush()
        return _tag_dict(tag, category.name if category else '')

@router.delete('/tags/{tag_id}', status_code=status.HTTP_204_NO_CONTENT)
def delete_global_tag(tag_id: str, _admin: AdminUser=Depends(require_admin)) -> None:
    with session_scope() as session:
        tag = session.get(ShotTag, tag_id)
        if tag is None:
            raise HTTPException(status_code=404, detail='标签不存在')
        session.delete(tag)

@router.post('/source-directory/select')
def select_source_directory(payload: SourceDirectorySelectPayload, _admin: AdminUser=Depends(require_admin)) -> dict[str, Any]:
    try:
        folder, videos = select_native_source_files(payload.initial_path)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {'path': folder, 'cancelled': not bool(videos), 'videos': [{'name': video.name, 'relative_path': video.relative_to(folder).as_posix(), 'path': str(video)} for video in videos]}

@router.post('/image-source-files/select')
def select_image_source_files(payload: SourceDirectorySelectPayload, _admin: AdminUser=Depends(require_admin)) -> dict[str, Any]:
    try:
        folder, images = select_native_image_files(payload.initial_path)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {'path': folder, 'cancelled': not bool(folder), 'images': [{'name': image.name, 'relative_path': image.relative_to(folder).as_posix(), 'path': str(image)} for image in images]}

@router.post('/image-source-files/preview', response_class=FileResponse)
def preview_image_source_file(payload: SourceImagePreviewPayload, _admin: AdminUser=Depends(require_admin)) -> FileResponse:
    try:
        image = resolve_source_image(payload.path)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return FileResponse(image, filename=image.name)

def _classified_asset_dict(session: Session, asset: MediaAsset) -> dict[str, Any]:
    product = session.get(Product, asset.product_id)
    rows = session.execute(select(ShotTag, TagCategory.name).join(MediaAssetTag, MediaAssetTag.tag_id == ShotTag.id).join(TagCategory, TagCategory.id == ShotTag.category_id).where(MediaAssetTag.asset_id == asset.id).order_by(TagCategory.name, ShotTag.name)).all()
    return {'id': asset.id, 'product_id': product.id if product else None, 'product_name': product.name if product else '', 'filename': asset.filename, 'source_path': asset.source_path, 'original_source_path': asset.original_source_path, 'status': asset.status, 'duration_seconds': asset.duration_seconds, 'width': asset.width, 'height': asset.height, 'tags': [_tag_dict(tag, category_name) for tag, category_name in rows], 'created_at': asset.created_at}

@router.post('/material-classifications', status_code=status.HTTP_201_CREATED)
def confirm_material_classification(payload: MaterialClassificationPayload, admin: AdminUser=Depends(require_admin), x_operation_id: str | None=Header(default=None, alias='X-Operation-Id')) -> dict[str, Any]:
    operation_id = _start_tracked_operation(x_operation_id, 'material_classification')
    try:
        with session_scope() as session:
            assets = classify_and_move_originals(session, product_id=payload.product_id, source_dir=payload.source_dir, items=[ClassificationItem(source_path=item.source_path, tag_ids=item.tag_ids) for item in payload.items])
            result = {'status': 'classified', 'assets': [_classified_asset_dict(session, asset) for asset in assets]}
        finish_operation(operation_id, 'completed', f'已移动并重命名 {len(result["assets"])} 个原视频')
        return result
    except (ValueError, RuntimeError, OSError) as exc:
        finish_operation(operation_id, 'failed', str(exc))
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        finish_operation(operation_id, 'failed', str(exc))
        raise

@router.get('/classified-materials')
def list_classified_materials(product_id: int | None=None, _admin: AdminUser=Depends(require_admin)) -> list[dict[str, Any]]:
    with session_scope() as session:
        statement = select(MediaAsset).where(MediaAsset.status == 'classified')
        if product_id is not None:
            statement = statement.where(MediaAsset.product_id == product_id)
        assets = session.scalars(statement.order_by(MediaAsset.created_at.desc())).all()
        return [_classified_asset_dict(session, asset) for asset in assets]

@router.get('/classified-materials/{asset_id}/video')
def get_classified_material_video(asset_id: str, _admin: AdminUser=Depends(require_admin)) -> FileResponse:
    with session_scope() as session:
        asset = session.get(MediaAsset, asset_id)
        if asset is None or asset.status != 'classified':
            raise HTTPException(status_code=404, detail='已归类视频不存在')
        path = Path(asset.source_path)
        if not path.is_file():
            raise HTTPException(status_code=404, detail='原视频文件不可访问')
        return FileResponse(path, media_type='video/mp4', filename=path.name)

@router.post('/tags', status_code=status.HTTP_201_CREATED)
def create_product_tag(payload: ProductTagPayload, _admin: AdminUser=Depends(require_admin)) -> dict[str, Any]:
    name = ' '.join(payload.name.strip().split())
    normalized = normalize_tag_name(name)
    with session_scope() as session:
        category = session.get(TagCategory, payload.category_id)
        if category is None:
            raise HTTPException(status_code=404, detail='标签分类不存在')
        tag = session.scalar(select(ShotTag).where(ShotTag.category_id == category.id, ShotTag.normalized_name == normalized))
        if tag is None:
            tag = ShotTag(name=name, normalized_name=normalized, category_id=category.id)
            session.add(tag)
            session.flush()
        else:
            raise HTTPException(status_code=409, detail='当前分类下标签名称已存在')
        session.flush()
        return _tag_dict(tag, category.name)

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

@router.post('/copies/iterations', status_code=status.HTTP_201_CREATED)
def create_copy_iteration(payload: CopyIterationPayload, _admin: AdminUser=Depends(require_admin), x_operation_id: str | None=Header(default=None, alias='X-Operation-Id')) -> dict[str, Any]:
    operation_id = _start_tracked_operation(x_operation_id, 'copy_generation')
    reference = payload.reference_text.strip()
    try:
        with session_scope() as session:
            source_mode = 'input' if reference else 'adopted_history'
            if not reference:
                adopted = session.scalars(select(CopyContent).order_by(CopyContent.created_at.desc()).limit(100)).all()
                if not adopted:
                    raise HTTPException(status_code=400, detail='还没有已采纳文案，请先输入一条参考文案')
                reference = '\n\n'.join(item.content_text for item in adopted)[:30000]
            try:
                result = analyze_and_generate_copies(reference_text=reference, source_mode=source_mode)
            except (ValueError, RuntimeError) as exc:
                raise HTTPException(status_code=409, detail=str(exc)) from exc
            record = CopyAnalysisRecord(source_mode=source_mode, source_text=reference, language_analysis=result['language_analysis'], audience_analysis=result['audience_analysis'], expert_role=result['expert_role'])
            session.add(record)
            session.flush()
            if source_mode == 'input':
                original = CopyContent(content_text=payload.reference_text.strip(), normalized_content=normalize_copy_text(payload.reference_text), source='original')
                session.add(original)
            _create_iteration_batch(session, record, 1, result['copies'])
            session.flush()
            response = _iteration_record(session, record)
        finish_operation(operation_id, 'completed', '文案分析完成，已生成 5 条候选')
        return response
    except Exception as exc:
        detail = exc.detail if isinstance(exc, HTTPException) else str(exc)
        finish_operation(operation_id, 'failed', str(detail))
        raise

@router.post('/copies/iterations/{record_id}/continue', status_code=status.HTTP_201_CREATED)
def continue_copy_generation(record_id: str, _admin: AdminUser=Depends(require_admin), x_operation_id: str | None=Header(default=None, alias='X-Operation-Id')) -> dict[str, Any]:
    operation_id = _start_tracked_operation(x_operation_id, 'copy_generation')
    try:
        with session_scope() as session:
            record = session.get(CopyAnalysisRecord, record_id)
            if record is None:
                raise HTTPException(status_code=404, detail='分析与迭代记录不存在')
            batches = session.scalars(select(CopyIterationBatch).where(CopyIterationBatch.analysis_record_id == record.id).order_by(CopyIterationBatch.sequence_number)).all()
            batch_ids = [item.id for item in batches]
            rows = session.scalars(select(CopyCandidate).where(CopyCandidate.iteration_batch_id.in_(batch_ids)).order_by(CopyCandidate.created_at)).all() if batch_ids else []
            latest_rows = [item for item in rows if batches and item.iteration_batch_id == batches[-1].id]
            if not latest_rows or any(item.status == 'pending' for item in latest_rows):
                raise HTTPException(status_code=400, detail='请先完成本轮 5 条文案的采纳或不采纳审核')
            feedback = [{'content': item.content_text, 'status': '已采纳' if item.status == 'adopted' else '未采纳', 'reason': item.rejection_reason} for item in rows if item.status in {'adopted', 'not_adopted'}]
            try:
                copies = continue_copy_iteration(reference_text=record.source_text, language_analysis=dict(record.language_analysis), audience_analysis=dict(record.audience_analysis), expert_role=record.expert_role, reviewed_feedback=feedback)
            except (ValueError, RuntimeError) as exc:
                raise HTTPException(status_code=409, detail=str(exc)) from exc
            _create_iteration_batch(session, record, len(batches) + 1, copies)
            response = _iteration_record(session, record)
        finish_operation(operation_id, 'completed', '已继续生成 5 条候选')
        return response
    except Exception as exc:
        detail = exc.detail if isinstance(exc, HTTPException) else str(exc)
        finish_operation(operation_id, 'failed', str(detail))
        raise

@router.get('/copies/iterations')
def list_copy_iterations(page: int=1, page_size: int=10, _admin: AdminUser=Depends(require_admin)) -> dict[str, Any]:
    size = max(1, min(page_size, 10)); current = max(1, page)
    with session_scope() as session:
        total = session.scalar(select(func.count(CopyAnalysisRecord.id))) or 0
        rows = session.scalars(select(CopyAnalysisRecord).order_by(CopyAnalysisRecord.created_at.desc()).offset((current - 1) * size).limit(size)).all()
        return {'total': int(total), 'page': current, 'page_size': size, 'items': [_iteration_record(session, item) for item in rows]}

@router.delete('/copies/iterations/{record_id}')
def delete_copy_iteration(record_id: str, _admin: AdminUser=Depends(require_admin)) -> dict[str, bool]:
    with session_scope() as session:
        record = session.get(CopyAnalysisRecord, record_id)
        if record is None:
            raise HTTPException(status_code=404, detail='分析与迭代记录不存在')
        session.delete(record)
        session.flush()
        return {'deleted': True}

@router.patch('/copies/{content_id}/review')
def review_generated_copy(content_id: str, payload: CopyReviewPayload, admin: AdminUser=Depends(require_admin)) -> dict[str, Any]:
    with session_scope() as session:
        item = session.get(CopyCandidate, content_id)
        if item is None:
            raise HTTPException(status_code=404, detail='文案候选不存在')
        if payload.status == 'not_adopted' and not payload.reason.strip():
            raise HTTPException(status_code=400, detail='不采纳文案必须填写原因')
        item.status = payload.status
        item.rejection_reason = payload.reason.strip() if payload.status == 'not_adopted' else ''
        item.reviewed_by = admin.id
        item.reviewed_at = utc_now()
        if payload.status == 'adopted' and item.library_content_id is None:
            normalized = normalize_copy_text(item.content_text)
            library = session.scalar(select(CopyContent).where(CopyContent.normalized_content == normalized))
            if library is None:
                library = CopyContent(content_text=item.content_text, normalized_content=normalized, source='model')
                session.add(library); session.flush()
            item.library_content_id = library.id
        return _candidate_item(item)

@router.get('/copies/library')
def list_copy_library(search: str='', product_id: int | None=None, limit: int=50, offset: int=0, _admin: AdminUser=Depends(require_admin)) -> dict[str, Any]:
    with session_scope() as session:
        filters = []
        if product_id is not None: filters.append(CopyContent.product_id == product_id)
        if search.strip(): filters.append(CopyContent.content_text.ilike(f'%{search.strip()}%'))
        total = session.scalar(select(func.count(CopyContent.id)).where(*filters)) or 0
        rows = session.scalars(select(CopyContent).where(*filters).order_by(CopyContent.created_at.desc()).offset(max(0, offset)).limit(max(1, min(limit, 200)))).all()
        return {'total': int(total), 'items': [_library_copy_item(session, item) for item in rows]}

@router.post('/copies', status_code=status.HTTP_201_CREATED)
def create_library_copy(payload: CopyLibraryPayload, _admin: AdminUser=Depends(require_admin)) -> dict[str, Any]:
    with session_scope() as session:
        content = payload.content.strip(); normalized = normalize_copy_text(content)
        duplicate = session.scalar(select(CopyContent).where(CopyContent.normalized_content == normalized))
        if duplicate is not None: raise HTTPException(status_code=409, detail='文案库中已存在相同文案')
        if payload.product_id is not None:
            product = session.get(Product, payload.product_id)
            if product is None or product.status != 'active': raise HTTPException(status_code=404, detail='所属产品不存在或已停用')
        item = CopyContent(product_id=payload.product_id, content_text=content, normalized_content=normalized, source='manual')
        session.add(item); session.flush()
        return _library_copy_item(session, item)

@router.put('/copies/{content_id}')
def update_library_copy(content_id: str, payload: CopyLibraryPayload, _admin: AdminUser=Depends(require_admin)) -> dict[str, Any]:
    with session_scope() as session:
        item = session.get(CopyContent, content_id)
        if item is None: raise HTTPException(status_code=404, detail='文案不存在')
        content = payload.content.strip(); normalized = normalize_copy_text(content)
        duplicate = session.scalar(select(CopyContent).where(CopyContent.normalized_content == normalized, CopyContent.id != item.id))
        if duplicate is not None: raise HTTPException(status_code=409, detail='文案库中已存在相同文案')
        if payload.product_id is not None:
            product = session.get(Product, payload.product_id)
            if product is None or product.status != 'active': raise HTTPException(status_code=404, detail='所属产品不存在或已停用')
        item.content_text = content; item.normalized_content = normalized; item.product_id = payload.product_id; item.updated_at = utc_now()
        return _library_copy_item(session, item)

@router.delete('/copies/{content_id}')
def delete_library_copy(content_id: str, _admin: AdminUser=Depends(require_admin)) -> dict[str, bool]:
    with session_scope() as session:
        item = session.get(CopyContent, content_id)
        if item is None: raise HTTPException(status_code=404, detail='文案不存在')
        session.delete(item); session.flush()
        return {'deleted': True}

@router.post('/copies/audio-to-text')
def audio_to_copy(
    share_url: str=Form(default=''),
    media: UploadFile | None=File(default=None),
    _admin: AdminUser=Depends(require_admin),
) -> dict[str, Any]:
    if bool(share_url.strip()) == bool(media and media.filename):
        raise HTTPException(status_code=400, detail='请选择一种来源：抖音视频短链接，或本地视频/音频')
    operation_id = uuid.uuid4().hex
    root = (Path(settings.workspace_dir) / 'copy-transcriptions' / operation_id).resolve()
    try:
        if share_url.strip():
            audio_path = prepare_shared_audio(share_url, root)
            source_type = 'douyin_link'
            source_name = share_url.strip()
        else:
            assert media is not None
            audio_path = prepare_uploaded_audio(filename=media.filename or 'media', stream=media.file, root=root)
            source_type = 'upload'
            source_name = media.filename or ''
        recognition = recognize_narration_audio(audio_path, call_id=operation_id, business_step='音频转文案')
        return {'text': str(recognition.get('text') or ''), 'source_type': source_type, 'source_name': source_name, 'model': recognition.get('model')}
    except (ValueError, RuntimeError, OSError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    finally:
        shutil.rmtree(root, ignore_errors=True)

@router.get('/voice-catalog')
def list_voice_catalog(
    page: int=1,
    page_size: int=20,
    q: str='',
    gender: str='',
    age: str='',
    scenario: str='',
    _admin: AdminUser=Depends(require_admin),
) -> dict[str, Any]:
    result = voice_catalog_page(page=page, page_size=page_size, query=q, gender=gender, age=age, scenario=scenario)
    profile = next((item for item in load_model_profiles() if item.stage == 'speech_synthesis'), None)
    result['current_model'] = profile.model if profile else ''
    result['available_for_current_model'] = bool(profile and profile.model.casefold() == CATALOG_MODEL)
    sequences = [int(item['sequence']) for item in result['items']]
    with session_scope() as session:
        ready = set(session.scalars(select(VoicePreviewAsset.sequence).where(VoicePreviewAsset.sequence.in_(sequences))).all()) if sequences else set()
    for item in result['items']:
        item['preview_ready'] = item['sequence'] in ready
    return result

@router.get('/voice-catalog/{sequence}')
def get_voice_catalog_item(sequence: int, _admin: AdminUser=Depends(require_admin)) -> dict[str, Any]:
    item = voice_catalog_item(sequence)
    if item is None:
        raise HTTPException(status_code=404, detail='音色序号不存在，请输入 1 至 597')
    with session_scope() as session:
        item['preview_ready'] = session.get(VoicePreviewAsset, sequence) is not None
    return item

def _resolve_model_voice(voice_sequence: int, admin: AdminUser) -> tuple[str, dict[str, Any]]:
    item = get_voice_catalog_item(voice_sequence, _admin=admin)
    profile = next((row for row in load_model_profiles() if row.stage == 'speech_synthesis'), None)
    if profile is None or profile.model.casefold() != CATALOG_MODEL:
        raise HTTPException(status_code=409, detail=f'音色库适用于 {CATALOG_MODEL}，当前字幕配音模型不匹配')
    return str(item['voice']), item

@router.post('/voice-preview', response_class=FileResponse)
def preview_model_voice(payload: VoicePreviewPayload, _admin: AdminUser=Depends(require_admin)) -> FileResponse:
    voice, catalog_item = _resolve_model_voice(payload.voice_sequence, _admin)
    with session_scope() as session:
        stored = session.get(VoicePreviewAsset, payload.voice_sequence)
        if stored is not None and Path(stored.audio_path).is_file():
            return FileResponse(Path(stored.audio_path), media_type='audio/wav', filename=f'voice-{payload.voice_sequence}.wav')
    preview_id = uuid.uuid4().hex
    target = (Path(settings.workspace_dir) / 'voice-previews' / f'{payload.voice_sequence}.wav').resolve()
    try:
        generate_narration_audio('你好，我是当前选择的配音音色，这是一段试听。', target, call_id=preview_id, voice=voice, business_step='字幕配音音色试听')
        audio_bytes = target.stat().st_size
    except (ValueError, RuntimeError, OSError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    with session_scope() as session:
        stored = session.get(VoicePreviewAsset, payload.voice_sequence)
        if stored is None:
            stored = VoicePreviewAsset(sequence=payload.voice_sequence, name=str(catalog_item['name']), voice=voice, model=CATALOG_MODEL, audio_path=str(target), audio_bytes=audio_bytes)
            session.add(stored)
        else:
            stored.name = str(catalog_item['name']); stored.voice = voice; stored.model = CATALOG_MODEL; stored.audio_path = str(target); stored.audio_bytes = audio_bytes; stored.updated_at = utc_now()
    return FileResponse(target, media_type='audio/wav', filename=f'voice-{payload.voice_sequence}.wav')

@router.get('/narrations')
def list_narrations(_admin: AdminUser=Depends(require_admin)) -> list[dict]:
    with session_scope() as session:
        items = session.scalars(select(NarrationAsset).order_by(NarrationAsset.created_at.desc())).all()
        return [_narration_dict(item) for item in items]

@router.post('/narrations/model-voice', status_code=status.HTTP_201_CREATED)
def create_model_voice_narration(payload: ModelNarrationPayload, _admin: AdminUser=Depends(require_admin)) -> dict:
    item_id = uuid.uuid4().hex
    target = (Path(settings.workspace_dir) / 'narrations' / item_id / 'generated.wav').resolve()
    chosen_voice, catalog_item = _resolve_model_voice(payload.voice_sequence, _admin)
    try:
        synthesis = generate_narration_audio(payload.approved_text, target, call_id=item_id, voice=chosen_voice)
        cues = _validated_cues(generated_subtitle_cues(payload.approved_text, target))
    except (ValueError, RuntimeError) as exc:
        if target.is_file():
            target.unlink()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    with session_scope() as session:
        item = NarrationAsset(id=item_id, text_source=payload.text_source, voice_source='model', approved_text=payload.approved_text.strip(), recognized_text=payload.approved_text.strip(), subtitle_cues=cues, audio_path=str(target), status='pending_review', metadata_json={'synthesis': synthesis, 'voice_catalog': {'sequence': catalog_item['sequence'], 'name': catalog_item['name']}})
        session.add(item)
        session.flush()
        return _narration_dict(item)

@router.put('/narrations/{narration_id}/confirm')
def confirm_narration(narration_id: str, payload: NarrationConfirmPayload, _admin: AdminUser=Depends(require_admin)) -> dict:
    try:
        cues = _validated_cues(payload.subtitle_cues)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    with session_scope() as session:
        item = session.get(NarrationAsset, narration_id)
        if item is None:
            raise HTTPException(status_code=404, detail='旁白资源不存在')
        item.approved_text = payload.approved_text.strip()
        item.subtitle_cues = cues
        item.status = 'approved'
        item.updated_at = utc_now()
        return _narration_dict(item)

@router.get('/narrations/{narration_id}/audio')
def get_narration_audio(narration_id: str, _admin: AdminUser=Depends(require_admin)) -> FileResponse:
    with session_scope() as session:
        item = session.get(NarrationAsset, narration_id)
        if item is None:
            raise HTTPException(status_code=404, detail='旁白资源不存在')
        path = Path(item.audio_path)
        if not path.is_file():
            raise HTTPException(status_code=404, detail='旁白音频文件不存在')
        return FileResponse(path, filename=path.name)

@router.delete('/narrations/{narration_id}', status_code=status.HTTP_204_NO_CONTENT)
def delete_narration(narration_id: str, _admin: AdminUser=Depends(require_admin)) -> None:
    with session_scope() as session:
        item = session.get(NarrationAsset, narration_id)
        if item is None:
            raise HTTPException(status_code=404, detail='旁白配音不存在')
        audio_path = Path(item.audio_path)
        session.delete(item)
        session.flush()
    narration_root = (Path(settings.workspace_dir) / 'narrations').resolve()
    try:
        resource_root = audio_path.resolve().parent
        resource_root.relative_to(narration_root)
        shutil.rmtree(resource_root, ignore_errors=True)
    except (OSError, ValueError):
        pass

def _jianying_draft_dict(session: Session, item: JianyingDraft) -> dict[str, Any]:
    return {'id': item.id, 'name': item.name, 'draft_path': item.draft_path, 'copy_content_id': item.copy_content_id, 'narration_asset_id': item.narration_asset_id, 'music_resource_id': item.music_resource_id, 'snapshot': dict(item.snapshot or {}), 'status': item.status, 'error': item.error, 'created_at': item.created_at, 'updated_at': item.updated_at}

@router.get('/jianying-drafts/directory')
def get_jianying_draft_directory(_admin: AdminUser=Depends(require_admin)) -> dict[str, Any]:
    with session_scope() as session:
        return detect_jianying_draft_directory(session)

@router.put('/jianying-drafts/directory')
def confirm_jianying_draft_directory(payload: JianyingDraftDirectoryPayload, _admin: AdminUser=Depends(require_admin)) -> dict[str, Any]:
    with session_scope() as session:
        try:
            save_jianying_draft_directory(session, payload.path)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return detect_jianying_draft_directory(session)

@router.get('/jianying-drafts')
def list_jianying_drafts(_admin: AdminUser=Depends(require_admin)) -> list[dict[str, Any]]:
    with session_scope() as session:
        items = session.scalars(select(JianyingDraft).order_by(JianyingDraft.created_at.desc())).all()
        return [_jianying_draft_dict(session, item) for item in items]

@router.post('/jianying-drafts', status_code=status.HTTP_201_CREATED)
def generate_jianying_draft(payload: JianyingDraftCreatePayload, admin: AdminUser=Depends(require_admin)) -> dict[str, Any]:
    with session_scope() as session:
        try:
            item = create_jianying_draft(session, name=payload.name, destination_dir=payload.destination_dir, copy_content_id=payload.copy_content_id, narration_asset_id=payload.narration_asset_id, music_resource_id=payload.music_resource_id, created_by=admin.id)
        except (ValueError, OSError, RuntimeError) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return _jianying_draft_dict(session, item)

@router.post('/jianying-drafts/duplicate-count')
def get_jianying_draft_duplicate_count(payload: JianyingDraftDuplicatePayload, _admin: AdminUser=Depends(require_admin)) -> dict[str, int]:
    with session_scope() as session:
        return {'count': duplicate_jianying_draft_usage_count(session, copy_content_id=payload.copy_content_id, narration_asset_id=payload.narration_asset_id, music_resource_id=payload.music_resource_id)}

@router.post('/jianying-drafts/duplicate-counter/reset')
def reset_jianying_draft_duplicate_count(payload: JianyingDraftDuplicatePayload, _admin: AdminUser=Depends(require_admin)) -> dict[str, int]:
    with session_scope() as session:
        count = reset_jianying_draft_duplicate_counter(session, copy_content_id=payload.copy_content_id, narration_asset_id=payload.narration_asset_id, music_resource_id=payload.music_resource_id)
        return {'count': count}

@router.delete('/jianying-drafts/{draft_id}', status_code=status.HTTP_204_NO_CONTENT)
def delete_jianying_draft(draft_id: str, _admin: AdminUser=Depends(require_admin)) -> None:
    with session_scope() as session:
        item = session.get(JianyingDraft, draft_id)
        if item is None:
            raise HTTPException(status_code=404, detail='剪映草稿记录不存在')
        session.delete(item)
        session.flush()
