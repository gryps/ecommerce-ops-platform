from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import select

from app.api.v1.image.schemas import (
    PromptRequest,
    TaskControlRequest,
    TaskCreateRequest,
    TaskOutputsRequest,
    TaskReviewRequest,
)
from app.core.database import session_scope
from app.core.security import utc_now
from app.domain.models import AdminUser, CommerceImageProduct, CommerceImageTask
from app.services.auth import require_admin
from app.services.image import build_prompt, create_task, task_dict, template_by_id


router = APIRouter()


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
        task.updated_at = utc_now()
        session.flush()
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
