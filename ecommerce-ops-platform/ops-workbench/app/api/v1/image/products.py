from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.api.v1.image.schemas import ImageProductPayload
from app.core.database import session_scope
from app.core.security import utc_now
from app.domain.models import (
    AdminUser,
    CommerceImageGroup,
    CommerceImageProduct,
    CommerceImageSourceAsset,
    CommerceImageTask,
    CommerceProductPlatformProfile,
)
from app.services.auth import require_admin
from app.services.image import apply_product_payload, create_product, product_dict


router = APIRouter()


@router.get("/products")
def list_image_products(q: str = "", _admin: AdminUser = Depends(require_admin)) -> dict[str, Any]:
    query = q.strip().casefold()
    with session_scope() as session:
        products = list(
            session.scalars(
                select(CommerceImageProduct)
                .where(CommerceImageProduct.status != "deleted")
                .order_by(CommerceImageProduct.product_code)
            ).all()
        )
        if query:
            products = [
                item
                for item in products
                if query in item.product_code.casefold() or query in item.name.casefold()
            ]
        return {"items": [product_dict(session, item) for item in products], "total": len(products)}


@router.post("/products", status_code=status.HTTP_201_CREATED)
def add_image_product(payload: ImageProductPayload, _admin: AdminUser = Depends(require_admin)) -> dict[str, Any]:
    with session_scope() as session:
        try:
            product = create_product(session, payload.model_dump())
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return product_dict(session, product)


@router.get("/products/{product_id}")
def get_image_product(product_id: str, _admin: AdminUser = Depends(require_admin)) -> dict[str, Any]:
    with session_scope() as session:
        product = session.get(CommerceImageProduct, product_id)
        if product is None or product.status == "deleted":
            raise HTTPException(status_code=404, detail="图片产品不存在")
        return product_dict(session, product)


@router.patch("/products/{product_id}")
def update_image_product(product_id: str, payload: ImageProductPayload, _admin: AdminUser = Depends(require_admin)) -> dict[str, Any]:
    with session_scope() as session:
        product = session.get(CommerceImageProduct, product_id)
        if product is None or product.status == "deleted":
            raise HTTPException(status_code=404, detail="图片产品不存在")
        duplicate_name = session.scalar(
            select(CommerceImageProduct).where(
                CommerceImageProduct.name == " ".join(payload.name.strip().split()),
                CommerceImageProduct.id != product.id,
                CommerceImageProduct.status != "deleted",
            )
        )
        if duplicate_name is not None:
            raise HTTPException(status_code=409, detail="产品名称已存在")
        try:
            values = payload.model_dump()
            values["product_code"] = product.product_code
            apply_product_payload(product, values)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        session.flush()
        return product_dict(session, product)


@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_image_product(
    product_id: str,
    delete_source_assets: bool = False,
    _admin: AdminUser = Depends(require_admin),
) -> None:
    with session_scope() as session:
        product = session.get(CommerceImageProduct, product_id)
        if product is None or product.status == "deleted":
            raise HTTPException(status_code=404, detail="图片产品不存在")
        groups = list(session.scalars(select(CommerceImageGroup).where(CommerceImageGroup.product_id == product.id)).all())
        source_ids: list[str] = []
        for group in groups:
            source_ids.extend(str(image.get("asset_id") or "") for image in (group.image_items or []))
            if delete_source_assets:
                session.delete(group)
            else:
                group.product_id = None
                group.status = "unassigned"
                group.updated_at = utc_now()
        if source_ids:
            source_assets = session.scalars(
                select(CommerceImageSourceAsset).where(
                    CommerceImageSourceAsset.id.in_([item for item in source_ids if item])
                )
            ).all()
            for item in source_assets:
                if delete_source_assets:
                    path = Path(item.storage_path)
                    if path.is_file():
                        path.unlink()
                    session.delete(item)
                else:
                    item.status = "unassigned"
                    item.updated_at = utc_now()
        for task in session.scalars(select(CommerceImageTask).where(CommerceImageTask.product_id == product.id)).all():
            session.delete(task)
        for profile in session.scalars(select(CommerceProductPlatformProfile).where(CommerceProductPlatformProfile.product_id == product.id)).all():
            session.delete(profile)
        product.status = "deleted"
        product.updated_at = utc_now()
