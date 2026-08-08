from __future__ import annotations

from sqlalchemy.orm import Session

from app.domain.models import CommerceImageProduct, CommerceImageTask


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
