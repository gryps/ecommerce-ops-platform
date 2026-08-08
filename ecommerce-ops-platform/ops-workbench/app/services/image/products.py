from __future__ import annotations

import re
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.core.security import utc_now
from app.domain.models import CommerceImageGroup, CommerceImageProduct


def normalize_code(value: str) -> str:
    return re.sub(r"\s+", "", value).upper()


def split_terms(value: list[str] | str | None) -> list[str]:
    if isinstance(value, list):
        raw_items = value
    else:
        raw_items = re.split(r"[,，、\n]", str(value or ""))
    cleaned = [" ".join(str(item).strip().split()) for item in raw_items if str(item).strip()]
    return list(dict.fromkeys(cleaned))[:30]


def product_storage_dir(product_code: str) -> Path:
    return settings.workspace_dir / "image-commerce" / "products" / normalize_code(product_code)


def product_dict(session: Session, product: CommerceImageProduct) -> dict:
    source_groups = list(
        session.scalars(
            select(CommerceImageGroup).where(CommerceImageGroup.product_id == product.id)
        ).all()
    )
    source_images = [item for group in source_groups for item in (group.image_items or [])]
    return {
        "id": product.id,
        "product_code": product.product_code,
        "name": product.name,
        "status": product.status,
        "reference_count": len(source_images),
        "reference_total": len(source_images),
        "missing_reference_types": [],
        "references": [],
        "source_images": source_images,
        "created_at": product.created_at,
        "updated_at": product.updated_at,
    }


def create_product(session: Session, payload: dict) -> CommerceImageProduct:
    code = normalize_code(str(payload.get("product_code") or ""))
    if not code:
        raise ValueError("产品编号必填")
    if session.scalar(select(CommerceImageProduct).where(CommerceImageProduct.product_code == code)):
        raise ValueError("产品编号已存在")
    name = " ".join(str(payload.get("name") or "").strip().split())
    if session.scalar(select(CommerceImageProduct).where(CommerceImageProduct.name == name, CommerceImageProduct.status != "deleted")):
        raise ValueError("产品名称已存在")
    product = CommerceImageProduct(product_code=code)
    apply_product_payload(product, payload)
    session.add(product)
    session.flush()
    product_storage_dir(product.product_code).mkdir(parents=True, exist_ok=True)
    return product


def apply_product_payload(product: CommerceImageProduct, payload: dict) -> None:
    product.product_code = normalize_code(str(payload.get("product_code") or product.product_code))
    product.name = " ".join(str(payload.get("name") or "").strip().split())
    if not product.name:
        raise ValueError("产品名称必填")
    product.updated_at = utc_now()
