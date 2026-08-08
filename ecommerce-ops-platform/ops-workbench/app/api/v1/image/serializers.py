from __future__ import annotations

from typing import Any

from app.domain.models import (
    CommerceImageSourceAsset,
    CommercePlatformTemplate,
    CommerceProductPlatformProfile,
)


def source_asset_dict(item: CommerceImageSourceAsset) -> dict[str, Any]:
    return {
        "id": item.id,
        "name": item.file_name,
        "status": item.status,
        "url": f"/api/v1/images/source-assets/{item.id}/file",
        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }


def template_dict(item: CommercePlatformTemplate) -> dict[str, Any]:
    return {
        "id": item.id,
        "name": item.name,
        "platform": item.platform,
        "entry_url": item.entry_url,
        "fields": list(item.fields or []),
        "image_slots": list(item.image_slots or []),
        "status": item.status,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }


def profile_dict(profile: CommerceProductPlatformProfile) -> dict[str, Any]:
    return {
        "id": profile.id,
        "product_id": profile.product_id,
        "template_id": profile.template_id,
        "values": dict(profile.values or {}),
        "image_selections": dict(profile.image_selections or {}),
        "status": profile.status,
        "draft_url": profile.draft_url,
        "process_log": list(profile.process_log or []),
        "created_at": profile.created_at,
        "updated_at": profile.updated_at,
    }
