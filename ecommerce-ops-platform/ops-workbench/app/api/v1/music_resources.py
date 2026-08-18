from __future__ import annotations

from pathlib import Path
import shutil

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select

from app.api.v1.schemas import MusicResourceLinkRequest, MusicResourceResponse, MusicResourceUpdateRequest
from app.core.database import session_scope
from app.core.security import utc_now
from app.domain.models import AdminUser, MusicResource
from app.services.audit import record_audit
from app.services.auth import require_admin
from app.services.music_resources import create_link_music, create_uploaded_music, delete_music_resource

router = APIRouter(prefix="/music-resources", tags=["music-resources"])


def music_resource_response(resource: MusicResource) -> MusicResourceResponse:
    return MusicResourceResponse(
        id=resource.id,
        name=resource.name,
        source_type=resource.source_type,
        source_url=resource.source_url,
        file_path=resource.file_path,
        rights_confirmed=resource.rights_confirmed,
        status=resource.status,
        duration_seconds=resource.duration_seconds,
        custom_tags=list(resource.custom_tags or []),
        error=resource.error,
        created_at=resource.created_at,
        updated_at=resource.updated_at,
    )


@router.get("", response_model=list[MusicResourceResponse])
def list_music_resources(_admin: AdminUser = Depends(require_admin)) -> list[MusicResourceResponse]:
    with session_scope() as session:
        resources = session.scalars(select(MusicResource).order_by(MusicResource.created_at.desc())).all()
        return [music_resource_response(item) for item in resources]


@router.get("/{resource_id}/audio", response_class=FileResponse)
def get_music_resource_audio(resource_id: str, _admin: AdminUser = Depends(require_admin)) -> FileResponse:
    with session_scope() as session:
        resource = session.get(MusicResource, resource_id)
        if resource is None:
            raise HTTPException(status_code=404, detail="音乐资源不存在")
        path = Path(resource.file_path).expanduser()
        if not resource.file_path or not path.is_file():
            raise HTTPException(status_code=404, detail="音乐文件尚未就绪")
        media_type = {
            ".mp3": "audio/mpeg",
            ".wav": "audio/wav",
            ".m4a": "audio/mp4",
            ".aac": "audio/aac",
            ".ogg": "audio/ogg",
            ".flac": "audio/flac",
        }.get(path.suffix.lower(), "application/octet-stream")
        return FileResponse(path, media_type=media_type)


@router.post("/link", response_model=MusicResourceResponse, status_code=status.HTTP_201_CREATED)
def add_link_music_resource(payload: MusicResourceLinkRequest, _admin: AdminUser = Depends(require_admin)) -> MusicResourceResponse:
    with session_scope() as session:
        try:
            resource = create_link_music(session, **payload.model_dump())
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return music_resource_response(resource)


@router.post("/upload", response_model=MusicResourceResponse, status_code=status.HTTP_201_CREATED)
def add_uploaded_music_resource(
    music: UploadFile = File(...),
    name: str = Form(default=""),
    rights_confirmed: bool = Form(default=False),
    _admin: AdminUser = Depends(require_admin),
) -> MusicResourceResponse:
    with session_scope() as session:
        try:
            resource = create_uploaded_music(
                session,
                name=name,
                filename=music.filename or "music",
                stream=music.file,
                rights_confirmed=rights_confirmed,
            )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return music_resource_response(resource)


@router.delete("/{resource_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def remove_music_resource(resource_id: str, admin: AdminUser = Depends(require_admin)) -> Response:
    cleanup_root: Path | None = None
    with session_scope() as session:
        resource = session.get(MusicResource, resource_id)
        before = {"name": resource.name, "source_type": resource.source_type, "status": resource.status, "file_path": resource.file_path} if resource is not None else {}
        try:
            result = delete_music_resource(session, resource_id)
        except LookupError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        record_audit(
            session,
            actor_id=admin.id,
            action="music_resource.delete",
            object_type="music_resource",
            object_id=resource_id,
            before=before,
            after={"deleted": True},
        )
        cleanup_root = Path(str(result["storage_root"]))
    if cleanup_root is not None:
        shutil.rmtree(cleanup_root, ignore_errors=True)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/{resource_id}", response_model=MusicResourceResponse)
def update_music_resource(resource_id: str, payload: MusicResourceUpdateRequest, admin: AdminUser = Depends(require_admin)) -> MusicResourceResponse:
    with session_scope() as session:
        resource = session.get(MusicResource, resource_id)
        if resource is None:
            raise HTTPException(status_code=404, detail="音乐资源不存在")
        before_name = resource.name
        before_tags = list(resource.custom_tags or [])
        resource.name = payload.name.strip()
        if payload.custom_tags is not None:
            normalized_tags = [" ".join(str(value).strip().split())[:40] for value in payload.custom_tags if str(value).strip()]
            resource.custom_tags = list(dict.fromkeys(normalized_tags))
        resource.updated_at = utc_now()
        record_audit(
            session,
            actor_id=admin.id,
            action="music_resource.rename",
            object_type="music_resource",
            object_id=resource.id,
            before={"name": before_name, "custom_tags": before_tags},
            after={"name": resource.name, "custom_tags": list(resource.custom_tags or [])},
        )
        return music_resource_response(resource)
