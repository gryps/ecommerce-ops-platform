from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.image.delivery import router as delivery_router
from app.api.v1.image.generation_tasks import router as generation_tasks_router
from app.api.v1.image.platform_templates import router as platform_templates_router
from app.api.v1.image.products import router as products_router
from app.api.v1.image.source_assets import router as source_assets_router
from app.api.v1.image.templates import router as templates_router


router = APIRouter(prefix="/images", tags=["commerce-image-production"])
router.include_router(templates_router)
router.include_router(platform_templates_router)
router.include_router(delivery_router)
router.include_router(source_assets_router)
router.include_router(products_router)
router.include_router(generation_tasks_router)

__all__ = ["router"]
