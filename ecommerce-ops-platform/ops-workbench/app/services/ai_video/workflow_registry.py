from __future__ import annotations

from pathlib import Path

from app.services.ai_video.models import WorkflowTemplate


_WORKFLOW_TEMPLATES = [
    WorkflowTemplate(
        name="text_to_video",
        label="文生视频",
        description="使用业务提示词直接生成宣传片片段，适合先跑创意方向。",
        default_engine="vendor_video",
        mode="t2v",
    ),
    WorkflowTemplate(
        name="image_to_video",
        label="图生视频",
        description="用用户提供的商品图驱动视频生成，场景图和关键帧由模型生成。",
        default_engine="vendor_video",
        mode="i2v",
        required_asset_kinds=["product"],
    ),
    WorkflowTemplate(
        name="first_last_frame_video",
        label="首尾帧视频",
        description="根据商品图和分镜先生成首尾帧，再控制镜头起止状态。",
        default_engine="vendor_video",
        mode="first_last_frame",
        required_asset_kinds=["product"],
    ),
    WorkflowTemplate(
        name="comfyui_business_workflow",
        label="ComfyUI业务工作流",
        description="平台登记商品图和任务，场景、关键帧、风格图等节点在 ComfyUI 画布里生成。",
        default_engine="comfyui",
        mode="workflow",
        required_asset_kinds=["product"],
    ),
]


def list_workflow_templates(workflows_dir: Path | None = None) -> list[WorkflowTemplate]:
    if workflows_dir is None:
        return [template.model_copy(deep=True) for template in _WORKFLOW_TEMPLATES]

    templates: list[WorkflowTemplate] = []
    for template in _WORKFLOW_TEMPLATES:
        item = template.model_copy(deep=True)
        if item.default_engine == "comfyui":
            workflow_file = workflows_dir / f"{item.name}.json"
            example_file = workflows_dir / f"{item.name}.example.json"
            item.available = workflow_file.exists()
            if not item.available:
                item.availability_note = "尚未配置真实 ComfyUI workflow 文件"
                if example_file.exists():
                    item.availability_note += "，当前仅有 example 占位文件"
        templates.append(item)
    return templates
