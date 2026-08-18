from __future__ import annotations

from collections import Counter
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import utc_now
from app.domain.models import OpsProduct


OPS_PRODUCT_STATUSES = {
    "candidate",
    "needs_sample",
    "ready_listing",
    "testing",
    "main",
    "clearance",
    "retired",
}


def normalize_tags(values: list[str]) -> list[str]:
    cleaned = [" ".join(value.strip().split())[:40] for value in values if value.strip()]
    return list(dict.fromkeys(cleaned))


def product_financials(product: OpsProduct) -> dict[str, float]:
    profit = max(0.0, product.actual_sale_price_yuan - product.purchase_cost_yuan)
    margin = profit / product.actual_sale_price_yuan if product.actual_sale_price_yuan else 0.0
    return {
        "estimated_gross_profit_yuan": round(profit, 2),
        "estimated_gross_margin": round(margin, 4),
    }


def stock_warning(product: OpsProduct) -> str:
    available = product.stock_qty + product.inbound_qty
    if product.status in {"retired", "clearance"}:
        return "manual_review"
    if available <= 0:
        return "out_of_stock"
    if available < 20:
        return "low_stock"
    return "ok"


def serialize_product(product: OpsProduct) -> dict[str, Any]:
    return {
        "id": product.id,
        "product_code": product.product_code,
        "name": product.name,
        "category": product.category,
        "style_tags": list(product.style_tags or []),
        "supplier_name": product.supplier_name,
        "supplier_link": product.supplier_link,
        "purchase_cost_yuan": product.purchase_cost_yuan,
        "target_sale_price_yuan": product.target_sale_price_yuan,
        "actual_sale_price_yuan": product.actual_sale_price_yuan,
        "stock_qty": product.stock_qty,
        "inbound_qty": product.inbound_qty,
        "procurement_cycle_days": product.procurement_cycle_days,
        "status": product.status,
        "selection_grade": product.selection_grade,
        "owner": product.owner,
        "notes": product.notes,
        "stock_warning": stock_warning(product),
        "created_at": product.created_at,
        "updated_at": product.updated_at,
        **product_financials(product),
    }


def list_ops_products(session: Session) -> list[OpsProduct]:
    return list(session.scalars(select(OpsProduct).order_by(OpsProduct.created_at.desc(), OpsProduct.product_code)).all())


def _apply_product_payload(product: OpsProduct, payload: Any) -> None:
    status = payload.status.strip() or "candidate"
    if status not in OPS_PRODUCT_STATUSES:
        raise ValueError("商品状态无效")
    product.product_code = payload.product_code.strip()
    product.name = payload.name.strip()
    product.category = payload.category.strip()
    product.style_tags = normalize_tags(payload.style_tags)
    product.supplier_name = payload.supplier_name.strip()
    product.supplier_link = payload.supplier_link.strip()
    product.purchase_cost_yuan = round(float(payload.purchase_cost_yuan), 2)
    product.target_sale_price_yuan = round(float(payload.target_sale_price_yuan), 2)
    product.actual_sale_price_yuan = round(float(payload.actual_sale_price_yuan), 2)
    product.stock_qty = int(payload.stock_qty)
    product.inbound_qty = int(payload.inbound_qty)
    product.procurement_cycle_days = int(payload.procurement_cycle_days)
    product.status = status
    product.selection_grade = payload.selection_grade.strip().upper()[:20]
    product.owner = payload.owner.strip()
    product.notes = payload.notes.strip()
    product.updated_at = utc_now()


def create_ops_product(session: Session, payload: Any) -> OpsProduct:
    code = payload.product_code.strip()
    if session.scalar(select(OpsProduct).where(OpsProduct.product_code == code)) is not None:
        raise ValueError("商品编号已存在")
    product = OpsProduct(product_code=code, name=payload.name.strip())
    _apply_product_payload(product, payload)
    session.add(product)
    session.flush()
    return product


def update_ops_product(session: Session, product_id: str, payload: Any) -> OpsProduct:
    product = session.get(OpsProduct, product_id)
    if product is None:
        raise LookupError("商品不存在")
    duplicate = session.scalar(
        select(OpsProduct).where(OpsProduct.product_code == payload.product_code.strip(), OpsProduct.id != product_id)
    )
    if duplicate is not None:
        raise ValueError("商品编号已存在")
    _apply_product_payload(product, payload)
    session.flush()
    return product


def operations_overview(session: Session) -> dict[str, Any]:
    products = list_ops_products(session)
    status_counts = dict(Counter(product.status for product in products))
    total_stock = sum(product.stock_qty for product in products)
    average_margin = 0.0
    if products:
        average_margin = sum(product_financials(product)["estimated_gross_margin"] for product in products) / len(products)
    risks = []
    for product in products:
        warning = stock_warning(product)
        if warning == "ok":
            continue
        detail = "可用库存不足" if warning in {"out_of_stock", "low_stock"} else "清仓或淘汰商品需人工复核"
        risks.append({
            "product_id": product.id,
            "product_code": product.product_code,
            "name": product.name,
            "risk": warning,
            "detail": detail,
        })
    return {
        "metrics": [
            {"key": "products", "label": "运营商品", "value": len(products), "unit": "个"},
            {"key": "main_products", "label": "主推商品", "value": status_counts.get("main", 0), "unit": "个"},
            {"key": "stock", "label": "当前库存", "value": total_stock, "unit": "件"},
            {"key": "gross_margin", "label": "平均毛利率", "value": round(average_margin * 100, 1), "unit": "%"},
        ],
        "risks": risks[:20],
        "product_status_counts": status_counts,
        "next_actions": [
            "补齐候选商品的供应商、采购价、建议售价和库存",
            "把可直播商品标记为测试中或主推，并生成直播排品",
            "导入下播后的订单、退款和投流数据，再做每日复盘",
        ],
    }
