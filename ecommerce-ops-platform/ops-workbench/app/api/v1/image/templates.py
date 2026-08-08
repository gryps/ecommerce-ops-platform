from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from app.domain.models import AdminUser
from app.services.auth import require_admin
from app.services.image import list_templates


router = APIRouter()


@router.get("/templates")
def get_image_templates(_admin: AdminUser = Depends(require_admin)) -> dict[str, Any]:
    return {"items": list_templates()}
