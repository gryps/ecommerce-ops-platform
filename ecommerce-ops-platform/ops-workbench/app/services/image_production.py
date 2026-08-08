from __future__ import annotations

import re
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.core.security import utc_now
from app.domain.models import CommerceImageGroup, CommerceImageProduct, CommerceImageTask


IMAGE_TEMPLATES: tuple[dict[str, object], ...] = (
    {
        "id": "main-white",
        "name": "白底主图",
        "image_type": "generated_main",
        "aspect_ratio": "1:1",
        "scene": "生成一张电商白底商品主图。画面干净，产品居中，背景纯白或接近纯白，柔和摄影棚光线，产品边缘清晰，材质细节清楚。",
        "negative": "不要添加额外装饰，不要改变珠子数量，不要改变金属颜色，不要改变流苏方向，不要生成多余产品。",
        "recommended_models": ["通义万相", "腾讯混元"],
        "input_image_types": ["source_images"],
    },
    {
        "id": "scene-chinese",
        "name": "中式环境图",
        "image_type": "generated_scene",
        "aspect_ratio": "4:5",
        "scene": "生成一张高级中式风格电商环境图。发簪放置在浅色绸缎、木质首饰盘或简洁梳妆台上，画面优雅、干净、有自然柔光。",
        "negative": "背景不要喧宾夺主，不要遮挡产品，不要改变产品结构，不要出现文字、水印或 logo。",
        "recommended_models": ["即梦/Seedream", "腾讯混元", "通义万相"],
        "input_image_types": ["source_images"],
    },
    {
        "id": "wearing",
        "name": "佩戴图",
        "image_type": "generated_wearing",
        "aspect_ratio": "4:5",
        "scene": "生成一张发簪佩戴图。模特为黑色或深棕色盘发，发簪自然插入发髻，露出完整装饰部分和合理长度的簪杆，画面干净、自然、真实。",
        "negative": "不要把发簪变成发夹、发钗或普通头饰，不要遮挡主要装饰，不要增加珠子，不要改变流苏数量。",
        "recommended_models": ["即梦/Seedream", "腾讯混元"],
        "input_image_types": ["source_images"],
    },
    {
        "id": "mobile-detail",
        "name": "手机竖屏商详图",
        "image_type": "generated_mobile_detail",
        "aspect_ratio": "9:16",
        "scene": "生成一张 9:16 手机竖屏电商详情图。画面上方展示发簪整体，下方留出可排版空间或展示材质细节，适合淘宝、抖音、小红书商品详情页。",
        "negative": "不要出现无关文字、水印、logo，不要改变颜色、装饰数量、流苏位置和簪杆比例。",
        "recommended_models": ["通义万相"],
        "input_image_types": ["source_images"],
    },
)


def normalize_code(value: str) -> str:
    return re.sub(r"\s+", "", value).upper()


def list_templates() -> list[dict[str, object]]:
    return [dict(item) for item in IMAGE_TEMPLATES]


def template_by_id(template_id: str) -> dict[str, object]:
    for item in IMAGE_TEMPLATES:
        if item["id"] == template_id:
            return dict(item)
    raise LookupError("图片模板不存在")


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


def build_prompt(product: CommerceImageProduct, template: dict[str, object]) -> dict[str, object]:
    negative = str(template["negative"])
    prompt = "\n".join(
        [
            "任务目标：",
            "输入图片是同一产品的实拍原图，请先分析原图主体、结构、颜色、材质和细节，再生成电商商品图提示词。",
            "",
            "产品标识：",
            f"产品编号：{product.product_code}",
            f"产品名称：{product.name}",
            "",
            "画面要求：",
            str(template["scene"]),
            "",
            "保真要求：",
            "必须以实拍原图为准，保持同一商品的整体造型、颜色、材质、结构比例、装饰数量、连接位置和左右方向。",
            "",
            "禁止：",
            "- 不要编造原图中不存在的配件、颜色、纹理、文字、水印或 logo。",
            "- 不要改变商品结构、颜色、材质、数量、相对位置和主体方向。",
            f"- {negative}",
        ]
    )
    checkpoints = [
        "是否仍是同一支发簪",
        "颜色是否一致",
        "珠子数量是否一致",
        "流苏数量和位置是否一致",
        "簪杆长度是否合理",
        "材质是否被改掉",
        "背景是否干净且适合电商上架",
    ]
    return {
        "template_id": template["id"],
        "template_name": template["name"],
        "recommended_models": list(template["recommended_models"]),
        "input_image_types": list(template["input_image_types"]),
        "prompt_zh": prompt,
        "negative_prompt_zh": negative,
        "fidelity_rules": [],
        "checkpoints": checkpoints,
    }


def create_task(session: Session, product: CommerceImageProduct, template: dict[str, object], model: str, output_plan: dict[str, int] | None = None) -> CommerceImageTask:
    prompt = build_prompt(product, template)
    selected_model = model.strip() or str(prompt["recommended_models"][0])
    plan = {str(key): max(0, min(int(value), 100)) for key, value in (output_plan or {}).items() if isinstance(value, int)}
    task = CommerceImageTask(
        product_id=product.id,
        template_id=str(template["id"]),
        template_name=str(template["name"]),
        model=selected_model,
        prompt=str(prompt["prompt_zh"]),
        negative_prompt=str(prompt["negative_prompt_zh"]),
        input_image_types=list(prompt["input_image_types"]),
        output_plan=plan,
    )
    session.add(task)
    session.flush()
    return task


def task_dict(task: CommerceImageTask) -> dict:
    output_images = [
        dict(item) | {"url": f"/api/v1/images/tasks/{task.id}/outputs/{index}/file"}
        for index, item in enumerate(task.output_images or [])
    ]
    return {
        "id": task.id,
        "product_id": task.product_id,
        "template_id": task.template_id,
        "template_name": task.template_name,
        "model": task.model,
        "prompt": task.prompt,
        "negative_prompt": task.negative_prompt,
        "input_image_types": list(task.input_image_types or []),
        "output_plan": dict(task.output_plan or {}),
        "output_images": output_images,
        "status": task.status,
        "review_status": task.review_status,
        "review_issues": list(task.review_issues or []),
        "review_comment": task.review_comment,
        "created_at": task.created_at,
        "updated_at": task.updated_at,
    }
