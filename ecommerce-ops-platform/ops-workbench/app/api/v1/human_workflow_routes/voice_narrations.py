from .human_common import *

router = APIRouter()

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

