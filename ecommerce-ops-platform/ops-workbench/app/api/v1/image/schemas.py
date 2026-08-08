from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


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
