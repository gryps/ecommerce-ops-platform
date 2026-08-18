from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


AssetKind = Literal["product", "character", "environment", "prop", "keyframe", "reference"]
TaskEngine = Literal["comfyui", "vendor_video"]
TaskStatus = Literal["draft", "queued", "running", "succeeded", "failed", "cancelled"]
WorkflowMode = Literal["t2v", "i2v", "first_last_frame", "workflow"]


def new_id() -> str:
    return uuid.uuid4().hex


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ProductProject(BaseModel):
    id: str = Field(default_factory=new_id)
    name: str
    product_name: str = ""
    selling_points: str = ""
    audience: str = ""
    tone: str = ""
    status: str = "draft"
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)


class Asset(BaseModel):
    id: str = Field(default_factory=new_id)
    project_id: str
    kind: AssetKind
    name: str
    file_path: str = ""
    preview_url: str = ""
    notes: str = ""
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)


class ImageProductionAssetImport(BaseModel):
    project_id: str
    task_id: str
    output_index: int = Field(ge=0)


class Shot(BaseModel):
    id: str = Field(default_factory=new_id)
    project_id: str
    order: int
    title: str
    duration_seconds: float = 3.0
    visual_goal: str = ""
    camera: str = ""
    prompt: str = ""
    negative_prompt: str = ""
    required_asset_kinds: list[AssetKind] = Field(default_factory=list)
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)


class GenerationTask(BaseModel):
    id: str = Field(default_factory=new_id)
    project_id: str
    engine: TaskEngine
    workflow_name: str
    prompt: str = ""
    input_asset_ids: list[str] = Field(default_factory=list)
    provider_task_id: str = ""
    status: TaskStatus = "draft"
    output_paths: list[str] = Field(default_factory=list)
    error: str = ""
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)


class TaskEvent(BaseModel):
    id: str = Field(default_factory=new_id)
    task_id: str
    event_type: str
    message: str = ""
    payload: dict = Field(default_factory=dict)
    created_at: str = Field(default_factory=now_iso)


class WorkflowTemplate(BaseModel):
    name: str
    label: str
    description: str = ""
    default_engine: TaskEngine
    mode: WorkflowMode
    required_asset_kinds: list[AssetKind] = Field(default_factory=list)
    available: bool = True
    availability_note: str = ""


class WorkbenchStore(BaseModel):
    projects: list[ProductProject] = Field(default_factory=list)
    assets: list[Asset] = Field(default_factory=list)
    shots: list[Shot] = Field(default_factory=list)
    tasks: list[GenerationTask] = Field(default_factory=list)
