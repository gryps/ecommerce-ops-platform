"""Compatibility facade for commerce image production API.

The implementation is split by bounded context under ``app.api.v1.image``.
This module keeps the old import path stable for the main API router and tests.
"""

from app.api.v1.image import router
from app.api.v1.image.schemas import (
    BrowserSessionCreateRequest,
    ImageProductPayload,
    PlatformProfileBatchUpdatePayload,
    PlatformProfilePayload,
    PlatformTemplatePayload,
    PromptRequest,
    SourceAssetProductCreateRequest,
    TaskControlRequest,
    TaskCreateRequest,
    TaskOutputsRequest,
    TaskReviewRequest,
)
from app.api.v1.image.source_assets import create_product_from_source_assets
from app.api.v1.image.products import delete_image_product

__all__ = [
    "BrowserSessionCreateRequest",
    "ImageProductPayload",
    "PlatformProfileBatchUpdatePayload",
    "PlatformProfilePayload",
    "PlatformTemplatePayload",
    "PromptRequest",
    "SourceAssetProductCreateRequest",
    "TaskControlRequest",
    "TaskCreateRequest",
    "TaskOutputsRequest",
    "TaskReviewRequest",
    "create_product_from_source_assets",
    "delete_image_product",
    "router",
]
