from .human_common import *

router = APIRouter()

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

