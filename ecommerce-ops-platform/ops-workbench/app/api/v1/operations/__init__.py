from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.v1.operations.schemas import OpsOverviewResponse, OpsProductPayload, OpsProductResponse
from app.core.database import session_scope
from app.domain.models import AdminUser
from app.services.auth import require_admin
from app.services.operations.products import create_ops_product, list_ops_products, operations_overview, serialize_product, update_ops_product


router = APIRouter(prefix="/operations", tags=["operations-center"])


@router.get("/overview", response_model=OpsOverviewResponse)
def get_operations_overview(_admin: AdminUser = Depends(require_admin)) -> dict:
    with session_scope() as session:
        return operations_overview(session)


@router.get("/products", response_model=list[OpsProductResponse])
def get_operations_products(_admin: AdminUser = Depends(require_admin)) -> list[dict]:
    with session_scope() as session:
        return [serialize_product(product) for product in list_ops_products(session)]


@router.post("/products", response_model=OpsProductResponse, status_code=status.HTTP_201_CREATED)
def add_operations_product(payload: OpsProductPayload, _admin: AdminUser = Depends(require_admin)) -> dict:
    with session_scope() as session:
        try:
            product = create_ops_product(session, payload)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        return serialize_product(product)


@router.patch("/products/{product_id}", response_model=OpsProductResponse)
def edit_operations_product(product_id: str, payload: OpsProductPayload, _admin: AdminUser = Depends(require_admin)) -> dict:
    with session_scope() as session:
        try:
            product = update_ops_product(session, product_id, payload)
        except LookupError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        return serialize_product(product)


__all__ = ["router"]
