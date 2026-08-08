from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.config import settings
from app.core.database import session_scope
from app.core.security import utc_now
from app.domain.models import (
    AdminUser,
    CommerceImageGroup,
    CommerceImageProduct,
    CommerceImageSourceArchive,
    CommerceImageSourceAsset,
    CommerceImageTask,
    CommercePlatformTemplate,
    CommerceProductPlatformProfile,
)
from app.services.auth import require_admin
from app.services.image_production import (
    apply_product_payload,
    build_prompt,
    create_product,
    create_task,
    list_templates,
    product_dict,
    task_dict,
    template_by_id,
)
from app.services.platform_browser import get_browser_session, start_browser_session, stop_browser_session


router = APIRouter(prefix="/images", tags=["commerce-image-production"])


class ImageProductPayload(BaseModel):
    product_code: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=160)


class PromptRequest(BaseModel):
    template_id: str = Field(min_length=1, max_length=80)


class TaskCreateRequest(BaseModel):
    template_id: str = Field(min_length=1, max_length=80)
    model: str = Field(default="", max_length=120)
    output_plan: dict[str, int] = Field(default_factory=dict)


class TaskReviewRequest(BaseModel):
    review_status: str = Field(min_length=1, max_length=30)
    issues: list[str] = Field(default_factory=list, max_length=30)
    comment: str = Field(default="", max_length=2000)


class TaskOutputsRequest(BaseModel):
    image_type: str = Field(min_length=1, max_length=40)
    items: list[dict[str, str]] = Field(min_length=1, max_length=500)


class TaskControlRequest(BaseModel):
    action: str = Field(pattern="^(terminate|retry)$")


class SourceAssetProductCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    source_asset_ids: list[str] = Field(min_length=1, max_length=5000)


class BrowserSessionCreateRequest(BaseModel):
    platform_url: str = Field(min_length=8, max_length=2000)


class PlatformTemplatePayload(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    platform: str = Field(default="", max_length=80)
    entry_url: str = Field(default="", max_length=2000)
    fields: list[dict[str, Any]] = Field(default_factory=list, max_length=200)
    image_slots: list[dict[str, Any]] = Field(default_factory=list, max_length=50)


class PlatformProfilePayload(BaseModel):
    values: dict[str, Any] = Field(default_factory=dict)
    image_selections: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)


class PlatformProfileBatchUpdatePayload(BaseModel):
    product_ids: list[str] = Field(min_length=1, max_length=500)
    template_id: str = Field(min_length=1, max_length=32)
    values: dict[str, Any] = Field(min_length=1)


def _template_dict(item: CommercePlatformTemplate) -> dict[str, Any]:
    return {"id": item.id, "name": item.name, "platform": item.platform, "entry_url": item.entry_url,
            "fields": list(item.fields or []), "image_slots": list(item.image_slots or []), "status": item.status,
            "created_at": item.created_at, "updated_at": item.updated_at}


def _profile_dict(profile: CommerceProductPlatformProfile) -> dict[str, Any]:
    return {"id": profile.id, "product_id": profile.product_id, "template_id": profile.template_id,
            "values": dict(profile.values or {}), "image_selections": dict(profile.image_selections or {}),
            "status": profile.status, "draft_url": profile.draft_url, "process_log": list(profile.process_log or []),
            "created_at": profile.created_at, "updated_at": profile.updated_at}


def _normalize_template_payload(payload: PlatformTemplatePayload) -> tuple[str, str, str, list[dict[str, Any]], list[dict[str, Any]]]:
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
        fields.append({"key": key[:80], "label": label[:120], "type": kind,
                       "required": bool(raw.get("required")), "default": raw.get("default", ""),
                       "options": list(raw.get("options") or [])[:100], "selector": str(raw.get("selector") or "")[:500]})
    slots: list[dict[str, Any]] = []
    slot_seen: set[str] = set()
    for raw in payload.image_slots:
        key = str(raw.get("key") or "").strip()
        label = str(raw.get("label") or "").strip()
        if not key or not label or key in slot_seen:
            raise HTTPException(status_code=422, detail="图片槽位需有唯一键和名称")
        slot_seen.add(key)
        slots.append({"key": key[:80], "label": label[:120], "required": bool(raw.get("required")),
                      "max_count": max(1, min(int(raw.get("max_count") or 1), 50)), "selector": str(raw.get("selector") or "")[:500]})
    return name, payload.platform.strip()[:80], payload.entry_url.strip(), fields, slots


@router.get("/templates")
def get_image_templates(_admin: AdminUser = Depends(require_admin)) -> dict[str, Any]:
    return {"items": list_templates()}


@router.get("/platform-templates")
def list_platform_templates(_admin: AdminUser = Depends(require_admin)) -> dict[str, Any]:
    with session_scope() as session:
        rows = session.scalars(select(CommercePlatformTemplate).where(CommercePlatformTemplate.status != "deleted").order_by(CommercePlatformTemplate.name)).all()
        return {"items": [_template_dict(item) for item in rows]}


@router.post("/platform-templates", status_code=status.HTTP_201_CREATED)
def create_platform_template(payload: PlatformTemplatePayload, _admin: AdminUser = Depends(require_admin)) -> dict[str, Any]:
    name, platform, entry_url, fields, slots = _normalize_template_payload(payload)
    with session_scope() as session:
        if session.scalar(select(CommercePlatformTemplate).where(CommercePlatformTemplate.name == name)):
            raise HTTPException(status_code=409, detail="平台模板名称已存在")
        item = CommercePlatformTemplate(name=name, platform=platform, entry_url=entry_url, fields=fields, image_slots=slots)
        session.add(item); session.flush()
        return _template_dict(item)


@router.patch("/platform-templates/{template_id}")
def update_platform_template(template_id: str, payload: PlatformTemplatePayload, _admin: AdminUser = Depends(require_admin)) -> dict[str, Any]:
    name, platform, entry_url, fields, slots = _normalize_template_payload(payload)
    with session_scope() as session:
        item = session.get(CommercePlatformTemplate, template_id)
        if item is None or item.status == "deleted":
            raise HTTPException(status_code=404, detail="平台模板不存在")
        duplicate = session.scalar(select(CommercePlatformTemplate).where(CommercePlatformTemplate.name == name, CommercePlatformTemplate.id != item.id))
        if duplicate:
            raise HTTPException(status_code=409, detail="平台模板名称已存在")
        item.name, item.platform, item.entry_url, item.fields, item.image_slots = name, platform, entry_url, fields, slots
        item.updated_at = utc_now(); session.flush()
        return _template_dict(item)


@router.delete("/platform-templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_platform_template(template_id: str, _admin: AdminUser = Depends(require_admin)) -> None:
    with session_scope() as session:
        item = session.get(CommercePlatformTemplate, template_id)
        if item is None or item.status == "deleted":
            raise HTTPException(status_code=404, detail="平台模板不存在")
        # 模板删除已在界面二次确认；数据库外键级联清理该模板下的档案值与选图映射。
        session.delete(item)


@router.get("/platform-profiles")
def list_platform_profiles(product_id: str = "", _admin: AdminUser = Depends(require_admin)) -> dict[str, Any]:
    with session_scope() as session:
        statement = select(CommerceProductPlatformProfile).order_by(CommerceProductPlatformProfile.updated_at.desc())
        if product_id:
            statement = statement.where(CommerceProductPlatformProfile.product_id == product_id)
        return {"items": [_profile_dict(item) for item in session.scalars(statement.limit(1000)).all()]}


@router.post("/products/{product_id}/platform-profiles/{template_id}", status_code=status.HTTP_201_CREATED)
def create_platform_profile(product_id: str, template_id: str, _admin: AdminUser = Depends(require_admin)) -> dict[str, Any]:
    with session_scope() as session:
        product = session.get(CommerceImageProduct, product_id)
        template = session.get(CommercePlatformTemplate, template_id)
        if product is None or product.status in {"deleted", "needs_reshoot"}:
            raise HTTPException(status_code=409, detail="产品不存在或原始照片缺失，不能创建平台档案")
        if template is None or template.status != "active":
            raise HTTPException(status_code=404, detail="平台模板不存在")
        existing = session.scalar(select(CommerceProductPlatformProfile).where(CommerceProductPlatformProfile.product_id == product_id, CommerceProductPlatformProfile.template_id == template_id))
        if existing:
            return _profile_dict(existing)
        defaults = {str(field["key"]): field.get("default", "") for field in template.fields or []}
        profile = CommerceProductPlatformProfile(product_id=product_id, template_id=template_id, values=defaults)
        session.add(profile); session.flush()
        return _profile_dict(profile)


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
        profile.values = dict(payload.values); profile.image_selections = dict(payload.image_selections)
        missing_fields = [field["label"] for field in template.fields or [] if field.get("required") and not profile.values.get(field["key"])]
        missing_slots = [slot["label"] for slot in template.image_slots or [] if slot.get("required") and not profile.image_selections.get(slot["key"])]
        profile.status = "waiting_fields" if missing_fields or missing_slots else "waiting_auto_fill"
        profile.updated_at = utc_now(); session.flush()
        return _profile_dict(profile)


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
        products = list(session.scalars(select(CommerceImageProduct).where(
            CommerceImageProduct.id.in_(list(dict.fromkeys(payload.product_ids))),
            CommerceImageProduct.status.not_in(["deleted", "needs_reshoot"]),
        )).all())
        if not products:
            raise HTTPException(status_code=404, detail="没有可更新的产品")
        slots = {str(slot["key"]): slot for slot in template.image_slots or []}
        for product in products:
            profile = session.scalar(select(CommerceProductPlatformProfile).where(
                CommerceProductPlatformProfile.product_id == product.id,
                CommerceProductPlatformProfile.template_id == template.id,
            ))
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
        return {"updated": len(products), "items": [_profile_dict(item) for item in session.scalars(select(CommerceProductPlatformProfile).where(
            CommerceProductPlatformProfile.template_id == template.id,
            CommerceProductPlatformProfile.product_id.in_([product.id for product in products]),
        )).all()]}


@router.post("/browser-sessions", status_code=status.HTTP_201_CREATED)
def start_platform_browser(payload: BrowserSessionCreateRequest, _admin: AdminUser = Depends(require_admin)) -> dict[str, str]:
    try:
        return start_browser_session(payload.platform_url)
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/browser-sessions/{session_id}")
def get_platform_browser(session_id: str, _admin: AdminUser = Depends(require_admin)) -> dict[str, str]:
    try:
        return get_browser_session(session_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/browser-sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def stop_platform_browser(session_id: str, _admin: AdminUser = Depends(require_admin)) -> None:
    try:
        stop_browser_session(session_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


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


def _source_asset_dict(item: CommerceImageSourceAsset) -> dict[str, Any]:
    return {
        "id": item.id,
        "name": item.file_name,
        "status": item.status,
        "url": f"/api/v1/images/source-assets/{item.id}/file",
        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }


@router.get("/source-assets")
def list_source_assets(status_value: str = "", _admin: AdminUser = Depends(require_admin)) -> dict[str, Any]:
    with session_scope() as session:
        statement = select(CommerceImageSourceAsset).order_by(CommerceImageSourceAsset.created_at.desc())
        if status_value.strip():
            statement = statement.where(CommerceImageSourceAsset.status == status_value.strip())
        rows = session.scalars(statement.limit(2000)).all()
        return {"items": [_source_asset_dict(item) for item in rows]}


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
        return {"items": [_source_asset_dict(item) for item in created]}


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
            # 产品序列号由创建产品组时生成，后续不得人工改写。
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
        # 产品档案、AI 任务和平台资料会删除。原图默认退回待分配，只有明确选择时才删除。
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
            source_assets = session.scalars(select(CommerceImageSourceAsset).where(CommerceImageSourceAsset.id.in_([item for item in source_ids if item]))).all()
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


@router.post("/products/{product_id}/prompt")
def generate_product_prompt(product_id: str, payload: PromptRequest, _admin: AdminUser = Depends(require_admin)) -> dict[str, Any]:
    with session_scope() as session:
        product = session.get(CommerceImageProduct, product_id)
        if product is None or product.status == "deleted":
            raise HTTPException(status_code=404, detail="图片产品不存在")
        try:
            template = template_by_id(payload.template_id)
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return build_prompt(product, template)


@router.post("/products/{product_id}/tasks", status_code=status.HTTP_201_CREATED)
def add_generation_task(product_id: str, payload: TaskCreateRequest, _admin: AdminUser = Depends(require_admin)) -> dict[str, Any]:
    with session_scope() as session:
        product = session.get(CommerceImageProduct, product_id)
        if product is None or product.status == "deleted":
            raise HTTPException(status_code=404, detail="图片产品不存在")
        if product.status == "needs_reshoot":
            raise HTTPException(status_code=409, detail="原始照片缺失，需重拍后才能提交出图")
        if session.scalar(select(CommerceImageTask).where(CommerceImageTask.product_id == product_id, CommerceImageTask.status.in_(("pending", "generating")))):
            raise HTTPException(status_code=409, detail="该产品已有未完成出图任务，请等待、终止或删除后再提交")
        try:
            template = template_by_id(payload.template_id)
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        task = create_task(session, product, template, payload.model, payload.output_plan)
        return task_dict(task)


@router.post("/tasks/{task_id}/control")
def control_generation_task(task_id: str, payload: TaskControlRequest, _admin: AdminUser = Depends(require_admin)) -> dict[str, Any]:
    with session_scope() as session:
        task = session.get(CommerceImageTask, task_id)
        if task is None:
            raise HTTPException(status_code=404, detail="生成任务不存在")
        if payload.action == "terminate":
            if task.status not in {"pending", "generating"}:
                raise HTTPException(status_code=409, detail="只有未完成任务可以终止")
            task.status = "cancelled"
        else:
            if task.status not in {"failed", "cancelled"}:
                raise HTTPException(status_code=409, detail="只有失败或已终止任务可以重试")
            task.status = "pending"
        task.updated_at = utc_now(); session.flush()
        return task_dict(task)


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_generation_task(task_id: str, _admin: AdminUser = Depends(require_admin)) -> None:
    with session_scope() as session:
        task = session.get(CommerceImageTask, task_id)
        if task is None:
            raise HTTPException(status_code=404, detail="生成任务不存在")
        session.delete(task)


@router.get("/tasks")
def list_generation_tasks(product_id: str = "", _admin: AdminUser = Depends(require_admin)) -> dict[str, Any]:
    with session_scope() as session:
        statement = select(CommerceImageTask).order_by(CommerceImageTask.created_at.desc())
        if product_id:
            statement = statement.where(CommerceImageTask.product_id == product_id)
        tasks = session.scalars(statement.limit(200)).all()
        return {"items": [task_dict(item) for item in tasks]}


@router.post("/tasks/{task_id}/outputs")
def attach_task_outputs(task_id: str, payload: TaskOutputsRequest, _admin: AdminUser = Depends(require_admin)) -> dict[str, Any]:
    allowed_types = {"白底图", "环境搭配图", "佩戴图", "商详图"}
    if payload.image_type not in allowed_types:
        raise HTTPException(status_code=422, detail="结果图片类型无效")
    with session_scope() as session:
        task = session.get(CommerceImageTask, task_id)
        if task is None:
            raise HTTPException(status_code=404, detail="生成任务不存在")
        outputs = list(task.output_images or [])
        existing_paths = {str(item.get("path") or "") for item in outputs}
        for item in payload.items:
            raw_path = str(item.get("path") or "")
            try:
                path = Path(raw_path).resolve(strict=True)
            except OSError as exc:
                raise HTTPException(status_code=422, detail="结果图片不存在或不可访问") from exc
            if not path.is_file() or path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}:
                raise HTTPException(status_code=422, detail="结果文件不是支持的图片")
            if str(path) not in existing_paths:
                outputs.append({"name": path.name, "path": str(path), "image_type": payload.image_type})
                existing_paths.add(str(path))
        task.output_images = outputs
        task.status = "completed"
        task.updated_at = utc_now()
        session.flush()
        return task_dict(task)


@router.get("/tasks/{task_id}/outputs/{index}/file", response_class=FileResponse)
def get_task_output_file(task_id: str, index: int, _admin: AdminUser = Depends(require_admin)) -> FileResponse:
    with session_scope() as session:
        task = session.get(CommerceImageTask, task_id)
        if task is None or index < 0 or index >= len(task.output_images or []):
            raise HTTPException(status_code=404, detail="结果图片不存在")
        raw_path = str((task.output_images or [])[index].get("path") or "")
        try:
            path = Path(raw_path).resolve(strict=True)
        except OSError as exc:
            raise HTTPException(status_code=404, detail="结果图片不可访问") from exc
        if not path.is_file():
            raise HTTPException(status_code=404, detail="结果图片不可访问")
        return FileResponse(path, filename=path.name)


@router.patch("/tasks/{task_id}/review")
def review_generation_task(task_id: str, payload: TaskReviewRequest, _admin: AdminUser = Depends(require_admin)) -> dict[str, Any]:
    allowed = {"unreviewed", "approved", "need_redo", "rejected"}
    if payload.review_status not in allowed:
        raise HTTPException(status_code=422, detail="审核状态无效")
    with session_scope() as session:
        task = session.get(CommerceImageTask, task_id)
        if task is None:
            raise HTTPException(status_code=404, detail="生成任务不存在")
        if payload.review_status == "approved" and not task.output_images:
            raise HTTPException(status_code=409, detail="任务尚未回传结果图，不能标记为可用")
        task.review_status = payload.review_status
        task.review_issues = [item.strip() for item in payload.issues if item.strip()][:30]
        task.review_comment = payload.comment.strip()
        task.status = "archived" if payload.review_status == "approved" else task.status
        task.updated_at = utc_now()
        session.flush()
        return task_dict(task)
