from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class BootstrapRequest(BaseModel):
    username: str = Field(min_length=3, max_length=80)
    password: str = Field(min_length=10, max_length=200)
    display_name: str = Field(default="", max_length=80)
    phone: str = Field(default="", max_length=40)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=200)


class BootstrapStatusResponse(BaseModel):
    initialized: bool


class UserResponse(BaseModel):
    id: str
    username: str
    display_name: str
    phone: str
    is_active: bool


class UserProfileUpdateRequest(BaseModel):
    display_name: str = Field(default="", max_length=80)
    phone: str = Field(default="", max_length=40)


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=200)
    new_password: str = Field(min_length=10, max_length=200)


class LoginResponse(BaseModel):
    token: str
    expires_at: datetime
    user: UserResponse


class ProductCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=160)


class ProductUpdateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=160)


class ProductResponse(BaseModel):
    id: int
    system_code: str
    name: str
    status: str
    asset_count: int
    created_at: datetime
    updated_at: datetime


class MusicResourceLinkRequest(BaseModel):
    name: str = Field(default="", max_length=200)
    share_url: str = Field(min_length=1, max_length=2000)
    rights_confirmed: bool


class MusicResourceUpdateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    custom_tags: list[str] | None = Field(default=None, max_length=50)


class MusicResourceResponse(BaseModel):
    id: str
    name: str
    source_type: str
    source_url: str
    file_path: str
    rights_confirmed: bool
    status: str
    duration_seconds: float
    custom_tags: list[str]
    error: str
    created_at: datetime
    updated_at: datetime
