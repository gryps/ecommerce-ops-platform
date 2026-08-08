from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select

from app.api.v1.image.schemas import SourceAssetProductCreateRequest
from app.api.v1.image.serializers import source_asset_dict
from app.config import settings
from app.core.database import session_scope
from app.core.security import utc_now
from app.domain.models import (
    AdminUser,
    CommerceImageGroup,
    CommerceImageProduct,
    CommerceImageSourceArchive,
    CommerceImageSourceAsset,
)
from app.services.auth import require_admin
from app.services.image import create_product, product_dict


router = APIRouter()


@router.get("/source-assets")
def list_source_assets(status_value: str = "", _admin: AdminUser = Depends(require_admin)) -> dict[str, Any]:
    with session_scope() as session:
        statement = select(CommerceImageSourceAsset).order_by(CommerceImageSourceAsset.created_at.desc())
        if status_value.strip():
            statement = statement.where(CommerceImageSourceAsset.status == status_value.strip())
        rows = session.scalars(statement.limit(2000)).all()
        return {"items": [source_asset_dict(item) for item in rows]}


@router.post("/source-assets", status_code=status.HTTP_201_CREATED)
def upload_source_assets(
    images: list[UploadFile] = File(...),
    _admin: AdminUser = Depends(require_admin),
) -> dict[str, Any]:
    allowed = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
    destination_root = settings.workspace_dir / "image-commerce" / "source-assets"
    destination_root.mkdir(parents=True, exist_ok=True)
    created: list[CommerceImageSourceAsset] = []
    with session_scope() as session:
        for image in images:
            original_name = Path(image.filename or "").name
            suffix = Path(original_name).suffix.lower()
            if not original_name or suffix not in allowed:
                raise HTTPException(status_code=422, detail="仅支持 jpg、png、webp、bmp、tif 图片")
            stored_name = f"{utc_now().strftime('%Y%m%d%H%M%S%f')}_{Path(original_name).stem[:120]}{suffix}"
            destination = destination_root / stored_name
            with destination.open("wb") as target:
                shutil.copyfileobj(image.file, target)
            item = CommerceImageSourceAsset(file_name=original_name, storage_path=str(destination.resolve()))
            session.add(item)
            created.append(item)
        session.flush()
        return {"items": [source_asset_dict(item) for item in created]}


@router.get("/source-assets/{asset_id}/file", response_class=FileResponse)
def get_source_asset_file(asset_id: str, _admin: AdminUser = Depends(require_admin)) -> FileResponse:
    with session_scope() as session:
        item = session.get(CommerceImageSourceAsset, asset_id)
        if item is None:
            raise HTTPException(status_code=404, detail="原始照片不存在")
        path = Path(item.storage_path)
        if not path.is_file():
            raise HTTPException(status_code=404, detail="原始照片文件不存在")
        return FileResponse(path, filename=item.file_name)


def _create_product_from_source_assets(
    session,
    payload: SourceAssetProductCreateRequest,
) -> CommerceImageProduct:
    ids = list(dict.fromkeys(payload.source_asset_ids))
    assets = list(
        session.scalars(
            select(CommerceImageSourceAsset).where(CommerceImageSourceAsset.id.in_(ids))
        ).all()
    )
    by_id = {item.id: item for item in assets}
    ordered_assets = [by_id.get(asset_id) for asset_id in ids]
    if len(assets) != len(ids) or any(item is None or item.status != "unassigned" for item in ordered_assets):
        raise HTTPException(status_code=409, detail="所选原始照片已分配或不存在")
    name = " ".join(payload.name.strip().split())
    if not name:
        raise HTTPException(status_code=422, detail="产品名称必填")
    items = [
        {
            "asset_id": item.id,
            "name": item.file_name,
            "path": item.storage_path,
            "relative_path": item.file_name,
        }
        for item in ordered_assets
        if item is not None
    ]
    source_archive = CommerceImageSourceArchive(
        name="素材库归档",
        source_directory="摄影素材库",
        source_images=items,
        status="archived",
    )
    session.add(source_archive)
    session.flush()
    code = f"IMG{source_archive.id[:10].upper()}"
    try:
        product = create_product(session, {"product_code": code, "name": name})
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    group = CommerceImageGroup(
        batch_id=source_archive.id,
        product_id=product.id,
        name=name,
        basis=f"人工从素材库选择 {len(items)} 张原始照片创建产品档案。",
        image_items=items,
        status="assigned",
        sort_order=1,
    )
    session.add(group)
    for item in ordered_assets:
        if item is not None:
            item.status = "assigned"
            item.updated_at = utc_now()
    session.flush()
    return product


@router.delete("/source-assets/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_source_asset(asset_id: str, _admin: AdminUser = Depends(require_admin)) -> None:
    with session_scope() as session:
        item = session.get(CommerceImageSourceAsset, asset_id)
        if item is None:
            raise HTTPException(status_code=404, detail="原始照片不存在")
        groups = list(session.scalars(select(CommerceImageGroup)).all())
        for group in groups:
            images = list(group.image_items or [])
            if not any(str(image.get("asset_id") or "") == item.id for image in images):
                continue
            group.image_items = [image for image in images if str(image.get("asset_id") or "") != item.id]
            group.updated_at = utc_now()
            if group.product_id:
                product = session.get(CommerceImageProduct, group.product_id)
                if product is not None and product.status != "deleted":
                    product.status = "needs_reshoot"
                    product.updated_at = utc_now()
        path = Path(item.storage_path)
        if path.is_file():
            path.unlink()
        session.delete(item)


@router.post("/source-assets/create-product", status_code=status.HTTP_201_CREATED)
def create_product_from_source_assets(payload: SourceAssetProductCreateRequest, _admin: AdminUser = Depends(require_admin)) -> dict[str, Any]:
    with session_scope() as session:
        product = _create_product_from_source_assets(session, payload)
        return {"product": product_dict(session, product)}
