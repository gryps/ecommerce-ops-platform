from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select

from app.api.v1.schemas import ProductCreateRequest, ProductResponse, ProductUpdateRequest
from app.core.database import session_scope
from app.core.security import utc_now
from app.domain.models import AdminUser, MediaAsset, Product
from app.services.audit import record_audit
from app.services.auth import require_admin
from app.services.product_library import create_product, duplicate_product_name, product_code

router = APIRouter(prefix="/products", tags=["products"])


def product_response(session, product: Product) -> ProductResponse:
    asset_count = session.scalar(select(func.count(MediaAsset.id)).where(MediaAsset.product_id == product.id)) or 0
    code = product_code(product.id)
    return ProductResponse(
        id=product.id,
        system_code=code,
        name=product.name,
        status=product.status,
        asset_count=asset_count,
        created_at=product.created_at,
        updated_at=product.updated_at,
    )


@router.get("", response_model=list[ProductResponse])
def list_products(include_inactive: bool = True, _admin: AdminUser = Depends(require_admin)) -> list[ProductResponse]:
    with session_scope() as session:
        statement = select(Product).where(Product.status != "deleted").order_by(Product.id)
        if not include_inactive:
            statement = statement.where(Product.status == "active")
        products = session.scalars(statement).all()
        return [product_response(session, product) for product in products]


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def add_product(payload: ProductCreateRequest, admin: AdminUser = Depends(require_admin)) -> ProductResponse:
    with session_scope() as session:
        duplicate = duplicate_product_name(session, payload.name)
        if duplicate is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"产品名称“{duplicate.name}”已存在，请直接选择已有产品")
        product = create_product(session, name=payload.name)
        record_audit(
            session,
            actor_id=admin.id,
            action="product.create",
            object_type="product",
            object_id=str(product.id),
            after={"system_code": product_code(product.id), "name": product.name},
        )
        return product_response(session, product)


@router.patch("/{product_id}", response_model=ProductResponse)
def update_product(product_id: int, payload: ProductUpdateRequest, admin: AdminUser = Depends(require_admin)) -> ProductResponse:
    with session_scope() as session:
        product = session.get(Product, product_id)
        if product is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="产品不存在")
        if product.status == "merged":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="已合并产品不能修改")
        name = payload.name.strip()
        duplicate = duplicate_product_name(session, name, exclude_product_id=product.id)
        if duplicate is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"产品名称“{duplicate.name}”已存在")
        before = {"name": product.name}
        product.name = name
        product.updated_at = utc_now()
        record_audit(
            session,
            actor_id=admin.id,
            action="product.update",
            object_type="product",
            object_id=str(product.id),
            before=before,
            after={"name": name},
        )
        session.flush()
        return product_response(session, product)
