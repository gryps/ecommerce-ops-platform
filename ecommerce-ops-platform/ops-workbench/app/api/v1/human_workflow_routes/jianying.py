from .human_common import *

router = APIRouter()

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

