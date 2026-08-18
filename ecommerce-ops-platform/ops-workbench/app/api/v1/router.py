from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.ai_video_production import router as ai_video_production_router
from app.api.v1.auth import router as auth_router
from app.api.v1.human_workflow import router as human_workflow_router
from app.api.v1.image_production import router as image_production_router
from app.api.v1.model_profiles import router as model_profiles_router
from app.api.v1.music_resources import router as music_resources_router
from app.api.v1.operations import router as operations_router
from app.api.v1.products import router as products_router

router = APIRouter(prefix="/api/v1")
router.include_router(auth_router)
router.include_router(model_profiles_router)
router.include_router(products_router)
router.include_router(music_resources_router)
router.include_router(human_workflow_router)
router.include_router(image_production_router)
router.include_router(ai_video_production_router)
router.include_router(operations_router)
