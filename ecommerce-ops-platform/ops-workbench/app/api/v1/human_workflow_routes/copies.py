from .human_common import *

router = APIRouter()

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

