from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.api.v1.image.schemas import (
    PlatformProfileBatchUpdatePayload,
    PlatformProfilePayload,
    PlatformTemplatePayload,
)
from app.api.v1.image.serializers import profile_dict, template_dict
from app.core.database import session_scope
from app.core.security import utc_now
from app.domain.models import (
    AdminUser,
    CommerceImageProduct,
    CommercePlatformTemplate,
    CommerceProductPlatformProfile,
)
from app.services.auth import require_admin


router = APIRouter()


def normalize_template_payload(payload: PlatformTemplatePayload) -> tuple[str, str, str, list[dict[str, Any]], list[dict[str, Any]]]:
    name = " ".join(payload.name.strip().split())
    fields: list[dict[str, Any]] = []
    seen: set[str] = set()
    allowed_types = {"text", "number", "select", "textarea", "rich_text", "sku_matrix"}
    for raw in payload.fields:
        key = str(raw.get("key") or "").strip()
        label = str(raw.get("label") or "").strip()
        kind = str(raw.get("type") or "text").strip()
        if not key or not label or kind not in allowed_types or key in seen:
            raise HTTPException(status_code=422, detail="模板字段需有唯一键、名称和有效类型")
        seen.add(key)
        fields.append(
            {
                "key": key[:80],
                "label": label[:120],
                "type": kind,
                "required": bool(raw.get("required")),
                "default": raw.get("default", ""),
                "options": list(raw.get("options") or [])[:100],
                "selector": str(raw.get("selector") or "")[:500],
            }
        )
    slots: list[dict[str, Any]] = []
    slot_seen: set[str] = set()
    for raw in payload.image_slots:
        key = str(raw.get("key") or "").strip()
        label = str(raw.get("label") or "").strip()
        if not key or not label or key in slot_seen:
            raise HTTPException(status_code=422, detail="图片槽位需有唯一键和名称")
        slot_seen.add(key)
        slots.append(
            {
                "key": key[:80],
                "label": label[:120],
                "required": bool(raw.get("required")),
                "max_count": max(1, min(int(raw.get("max_count") or 1), 50)),
                "selector": str(raw.get("selector") or "")[:500],
            }
        )
    return name, payload.platform.strip()[:80], payload.entry_url.strip(), fields, slots


@router.get("/platform-templates")
def list_platform_templates(_admin: AdminUser = Depends(require_admin)) -> dict[str, Any]:
    with session_scope() as session:
        rows = session.scalars(
            select(CommercePlatformTemplate)
            .where(CommercePlatformTemplate.status != "deleted")
            .order_by(CommercePlatformTemplate.name)
        ).all()
        return {"items": [template_dict(item) for item in rows]}


@router.post("/platform-templates", status_code=status.HTTP_201_CREATED)
def create_platform_template(payload: PlatformTemplatePayload, _admin: AdminUser = Depends(require_admin)) -> dict[str, Any]:
    name, platform, entry_url, fields, slots = normalize_template_payload(payload)
    with session_scope() as session:
        if session.scalar(select(CommercePlatformTemplate).where(CommercePlatformTemplate.name == name)):
            raise HTTPException(status_code=409, detail="平台模板名称已存在")
        item = CommercePlatformTemplate(name=name, platform=platform, entry_url=entry_url, fields=fields, image_slots=slots)
        session.add(item)
        session.flush()
        return template_dict(item)


@router.patch("/platform-templates/{template_id}")
def update_platform_template(template_id: str, payload: PlatformTemplatePayload, _admin: AdminUser = Depends(require_admin)) -> dict[str, Any]:
    name, platform, entry_url, fields, slots = normalize_template_payload(payload)
    with session_scope() as session:
        item = session.get(CommercePlatformTemplate, template_id)
        if item is None or item.status == "deleted":
            raise HTTPException(status_code=404, detail="平台模板不存在")
        duplicate = session.scalar(
            select(CommercePlatformTemplate).where(
                CommercePlatformTemplate.name == name,
                CommercePlatformTemplate.id != item.id,
            )
        )
        if duplicate:
            raise HTTPException(status_code=409, detail="平台模板名称已存在")
        item.name, item.platform, item.entry_url, item.fields, item.image_slots = name, platform, entry_url, fields, slots
        item.updated_at = utc_now()
        session.flush()
        return template_dict(item)


@router.delete("/platform-templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_platform_template(template_id: str, _admin: AdminUser = Depends(require_admin)) -> None:
    with session_scope() as session:
        item = session.get(CommercePlatformTemplate, template_id)
        if item is None or item.status == "deleted":
            raise HTTPException(status_code=404, detail="平台模板不存在")
        session.delete(item)


@router.get("/platform-profiles")
def list_platform_profiles(product_id: str = "", _admin: AdminUser = Depends(require_admin)) -> dict[str, Any]:
    with session_scope() as session:
        statement = select(CommerceProductPlatformProfile).order_by(CommerceProductPlatformProfile.updated_at.desc())
        if product_id:
            statement = statement.where(CommerceProductPlatformProfile.product_id == product_id)
        return {"items": [profile_dict(item) for item in session.scalars(statement.limit(1000)).all()]}


@router.post("/products/{product_id}/platform-profiles/{template_id}", status_code=status.HTTP_201_CREATED)
def create_platform_profile(product_id: str, template_id: str, _admin: AdminUser = Depends(require_admin)) -> dict[str, Any]:
    with session_scope() as session:
        product = session.get(CommerceImageProduct, product_id)
        template = session.get(CommercePlatformTemplate, template_id)
        if product is None or product.status in {"deleted", "needs_reshoot"}:
            raise HTTPException(status_code=409, detail="产品不存在或原始照片缺失，不能创建平台档案")
        if template is None or template.status != "active":
            raise HTTPException(status_code=404, detail="平台模板不存在")
        existing = session.scalar(
            select(CommerceProductPlatformProfile).where(
                CommerceProductPlatformProfile.product_id == product_id,
                CommerceProductPlatformProfile.template_id == template_id,
            )
        )
        if existing:
            return profile_dict(existing)
        defaults = {str(field["key"]): field.get("default", "") for field in template.fields or []}
        profile = CommerceProductPlatformProfile(product_id=product_id, template_id=template_id, values=defaults)
        session.add(profile)
        session.flush()
        return profile_dict(profile)


@router.patch("/platform-profiles/{profile_id}")
def update_platform_profile(profile_id: str, payload: PlatformProfilePayload, _admin: AdminUser = Depends(require_admin)) -> dict[str, Any]:
    with session_scope() as session:
        profile = session.get(CommerceProductPlatformProfile, profile_id)
        if profile is None:
            raise HTTPException(status_code=404, detail="平台档案不存在")
        template = session.get(CommercePlatformTemplate, profile.template_id)
        if template is None or template.status != "active":
            raise HTTPException(status_code=409, detail="平台模板已删除或停用")
        keys = {str(field["key"]) for field in template.fields or []}
        slots = {str(slot["key"]): slot for slot in template.image_slots or []}
        if any(key not in keys for key in payload.values):
            raise HTTPException(status_code=422, detail="存在已从模板删除的字段")
        if any(key not in slots for key in payload.image_selections):
            raise HTTPException(status_code=422, detail="存在无效图片槽位")
        for key, rows in payload.image_selections.items():
            if len(rows) > int(slots[key].get("max_count") or 1):
                raise HTTPException(status_code=422, detail=f"图片槽位“{slots[key]['label']}”超过允许数量")
        profile.values = dict(payload.values)
        profile.image_selections = dict(payload.image_selections)
        missing_fields = [field["label"] for field in template.fields or [] if field.get("required") and not profile.values.get(field["key"])]
        missing_slots = [slot["label"] for slot in template.image_slots or [] if slot.get("required") and not profile.image_selections.get(slot["key"])]
        profile.status = "waiting_fields" if missing_fields or missing_slots else "waiting_auto_fill"
        profile.updated_at = utc_now()
        session.flush()
        return profile_dict(profile)


@router.patch("/platform-profile-batch-fields")
def batch_update_platform_profiles(payload: PlatformProfileBatchUpdatePayload, _admin: AdminUser = Depends(require_admin)) -> dict[str, Any]:
    """按模板批量写入产品档案值；字段定义始终只来自模板。"""
    with session_scope() as session:
        template = session.get(CommercePlatformTemplate, payload.template_id)
        if template is None or template.status != "active":
            raise HTTPException(status_code=404, detail="平台模板不存在")
        fields = list(template.fields or [])
        keys = {str(field["key"]) for field in fields}
        if any(key not in keys for key in payload.values):
            raise HTTPException(status_code=422, detail="存在不属于该模板的字段")
        products = list(
            session.scalars(
                select(CommerceImageProduct).where(
                    CommerceImageProduct.id.in_(list(dict.fromkeys(payload.product_ids))),
                    CommerceImageProduct.status.not_in(["deleted", "needs_reshoot"]),
                )
            ).all()
        )
        if not products:
            raise HTTPException(status_code=404, detail="没有可更新的产品")
        slots = {str(slot["key"]): slot for slot in template.image_slots or []}
        for product in products:
            profile = session.scalar(
                select(CommerceProductPlatformProfile).where(
                    CommerceProductPlatformProfile.product_id == product.id,
                    CommerceProductPlatformProfile.template_id == template.id,
                )
            )
            if profile is None:
                profile = CommerceProductPlatformProfile(
                    product_id=product.id,
                    template_id=template.id,
                    values={str(field["key"]): field.get("default", "") for field in fields},
                )
                session.add(profile)
            values = dict(profile.values or {})
            values.update(payload.values)
            profile.values = values
            missing_fields = [field["label"] for field in fields if field.get("required") and not values.get(field["key"])]
            selections = dict(profile.image_selections or {})
            missing_slots = [slot["label"] for slot in slots.values() if slot.get("required") and not selections.get(slot["key"])]
            profile.status = "waiting_fields" if missing_fields or missing_slots else "waiting_auto_fill"
            profile.updated_at = utc_now()
        session.flush()
        rows = session.scalars(
            select(CommerceProductPlatformProfile).where(
                CommerceProductPlatformProfile.template_id == template.id,
                CommerceProductPlatformProfile.product_id.in_([product.id for product in products]),
            )
        ).all()
        return {"updated": len(products), "items": [profile_dict(item) for item in rows]}
