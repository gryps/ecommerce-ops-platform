from __future__ import annotations

from pydantic import BaseModel


class ModelProfile(BaseModel):
    stage: str
    label: str
    base_url: str = ""
    model: str = ""
    temperature: float = 0.2
    proxy_url: str = ""
    api_key: str = ""
    has_api_key: bool = False
    api_key_mask: str = ""


class ModelProfilesResponse(BaseModel):
    profiles: list[ModelProfile]


class ModelProfilesUpdateRequest(BaseModel):
    profiles: list[ModelProfile]
