from __future__ import annotations

import uuid
from typing import Any

import httpx

from app.config import settings


class ComfyUIClient:
    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = (base_url or settings.comfyui_base_url).rstrip("/")

    async def health(self) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self.base_url}/system_stats")
                response.raise_for_status()
                return {"ok": True, "base_url": self.base_url, "stats": response.json()}
        except Exception as exc:
            return {"ok": False, "base_url": self.base_url, "error": str(exc)}

    async def queue_prompt(self, workflow: dict[str, Any], client_id: str | None = None) -> dict[str, Any]:
        payload = {"prompt": workflow, "client_id": client_id or uuid.uuid4().hex}
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(f"{self.base_url}/prompt", json=payload)
            response.raise_for_status()
            return response.json()
