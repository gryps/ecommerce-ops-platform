from .human_common import *

router = APIRouter()

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

