from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.models import Product


def product_code(product_id: int) -> str:
    return f"PRD-{product_id:06d}"


def normalize_product_name(value: str) -> str:
    return re.sub(r"\s+", "", value).casefold()


def duplicate_product_name(
    session: Session,
    name: str,
    *,
    exclude_product_id: int | None = None,
) -> Product | None:
    normalized = normalize_product_name(name)
    if not normalized:
        return None
    products = session.scalars(
        select(Product).where(Product.status != "deleted")
    ).all()
    return next(
        (
            product
            for product in products
            if product.id != exclude_product_id
            and normalize_product_name(product.name) == normalized
        ),
        None,
    )


def create_product(
    session: Session,
    *,
    name: str = "",
) -> Product:
    product = Product(name=name.strip())
    session.add(product)
    session.flush()
    return product
