from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

from app.ai import load_model_profiles, openai_authorization
from app.models import ModelProfile
from app.services.model_call_logs import record_business_model_call


VIDEO_PROFILE_STAGE = "ai_video_generation"


@dataclass(frozen=True)
class VideoInputFile:
    role: str
    path: str = ""
    url: str = ""


@dataclass(frozen=True)
class StandardVideoRequest:
    mode: str
    prompt: str
    negative_prompt: str = ""
    input_files: list[VideoInputFile] = field(default_factory=list)
    duration: int = 5
    aspect_ratio: str = "9:16"
    resolution: str = "720p"
    seed: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class StandardSubmitResult:
    provider: str
    provider_task_id: str
    status: str
    raw_response: dict[str, Any]


@dataclass(frozen=True)
class StandardTaskStatus:
    provider: str
    provider_task_id: str
    status: str
    output_paths: list[str] = field(default_factory=list)
    error: str = ""
    raw_response: dict[str, Any] = field(default_factory=dict)


class VideoProviderAdapter:
    provider_name = "video_provider"

    async def submit(self, request: StandardVideoRequest) -> StandardSubmitResult:
        raise NotImplementedError

    async def get_status(self, provider_task_id: str) -> StandardTaskStatus:
        raise NotImplementedError


def load_video_model_profile() -> ModelProfile:
    profile = next(
        (item for item in load_model_profiles(include_api_key=True) if item.stage == VIDEO_PROFILE_STAGE),
        None,
    )
    if profile is None or not profile.base_url.strip() or not profile.model.strip() or not profile.api_key.strip():
        raise RuntimeError("AI 视频生成模型配置不完整，请先在模型配置中填写接口地址、模型和 API Key")
    return profile


def _video_submit_endpoint(base_url: str) -> str:
    clean = base_url.rstrip("/")
    if clean.endswith("/video/generations"):
        return clean
    return f"{clean}/video/generations" if clean.endswith("/v1") else f"{clean}/v1/video/generations"


def _video_status_endpoint(base_url: str, provider_task_id: str) -> str:
    clean = base_url.rstrip("/")
    if clean.endswith("/video/generations"):
        return f"{clean}/{provider_task_id}"
    return f"{clean}/video/generations/{provider_task_id}" if clean.endswith("/v1") else f"{clean}/v1/video/generations/{provider_task_id}"


def _normal_status(value: str) -> str:
    clean = value.strip().casefold()
    if clean in {"queued", "pending", "submitted", "created"}:
        return "queued"
    if clean in {"running", "processing", "in_progress"}:
        return "running"
    if clean in {"succeeded", "success", "completed", "complete", "done"}:
        return "succeeded"
    if clean in {"failed", "failure", "error", "cancelled", "canceled"}:
        return "failed"
    return "running" if clean else "running"


def _first_text(value: Any, keys: tuple[str, ...]) -> str:
    if not isinstance(value, dict):
        return ""
    for key in keys:
        item = value.get(key)
        if isinstance(item, str) and item.strip():
            return item.strip()
    return ""


def _output_paths(data: dict[str, Any]) -> list[str]:
    rows = data.get("output_paths") or data.get("outputs") or data.get("data") or []
    if isinstance(rows, dict):
        rows = [rows]
    paths: list[str] = []
    if isinstance(rows, list):
        for item in rows:
            if isinstance(item, str) and item.strip():
                paths.append(item.strip())
            elif isinstance(item, dict):
                url = _first_text(item, ("url", "video_url", "file_url", "path"))
                if url:
                    paths.append(url)
    single = _first_text(data, ("url", "video_url", "file_url", "output_url"))
    if single:
        paths.append(single)
    return list(dict.fromkeys(paths))


class OpenAICompatibleVideoAdapter(VideoProviderAdapter):
    provider_name = "openai_compatible_video"

    def __init__(self, profile: ModelProfile | None = None) -> None:
        self.profile = profile or load_video_model_profile()

    async def submit(self, request: StandardVideoRequest) -> StandardSubmitResult:
        payload = {
            "model": self.profile.model,
            "mode": request.mode,
            "prompt": request.prompt,
            "negative_prompt": request.negative_prompt,
            "input_files": [item.__dict__ for item in request.input_files],
            "duration": request.duration,
            "aspect_ratio": request.aspect_ratio,
            "resolution": request.resolution,
            "seed": request.seed,
            "metadata": request.metadata,
        }
        started = time.monotonic()
        data: dict[str, Any] = {}
        try:
            async with httpx.AsyncClient(timeout=60, proxy=self.profile.proxy_url.strip() or None) as client:
                response = await client.post(
                    _video_submit_endpoint(self.profile.base_url),
                    json=payload,
                    headers={
                        "Authorization": openai_authorization(self.profile.api_key),
                        "Content-Type": "application/json",
                    },
                )
                response.raise_for_status()
                data = response.json()
            provider_task_id = _first_text(data, ("id", "task_id", "provider_task_id", "request_id"))
            if not provider_task_id:
                raise RuntimeError("视频 API 未返回任务 ID")
            record_business_model_call(
                stage=VIDEO_PROFILE_STAGE,
                label=self.profile.label,
                provider=self.provider_name,
                model=self.profile.model,
                input_payload=payload,
                output_payload=data,
                success=True,
                duration_ms=int((time.monotonic() - started) * 1000),
                business_step="ai_video_submit",
                business_objects=[{"type": "ai_video_task", "id": request.metadata.get("task_id", "")}],
            )
            return StandardSubmitResult(
                provider=self.provider_name,
                provider_task_id=provider_task_id,
                status=_normal_status(str(data.get("status") or "submitted")),
                raw_response=data,
            )
        except Exception as exc:
            record_business_model_call(
                stage=VIDEO_PROFILE_STAGE,
                label=self.profile.label,
                provider=self.provider_name,
                model=self.profile.model,
                input_payload=payload,
                output_payload=data or {"error": str(exc)},
                success=False,
                duration_ms=int((time.monotonic() - started) * 1000),
                business_step="ai_video_submit",
                business_objects=[{"type": "ai_video_task", "id": request.metadata.get("task_id", "")}],
            )
            raise

    async def get_status(self, provider_task_id: str) -> StandardTaskStatus:
        started = time.monotonic()
        data: dict[str, Any] = {}
        try:
            async with httpx.AsyncClient(timeout=30, proxy=self.profile.proxy_url.strip() or None) as client:
                response = await client.get(
                    _video_status_endpoint(self.profile.base_url, provider_task_id),
                    headers={"Authorization": openai_authorization(self.profile.api_key)},
                )
                response.raise_for_status()
                data = response.json()
            status = _normal_status(str(data.get("status") or data.get("state") or "running"))
            error = _first_text(data, ("error", "error_message", "message")) if status == "failed" else ""
            record_business_model_call(
                stage=VIDEO_PROFILE_STAGE,
                label=self.profile.label,
                provider=self.provider_name,
                model=self.profile.model,
                input_payload={"provider_task_id": provider_task_id},
                output_payload=data,
                success=status != "failed",
                duration_ms=int((time.monotonic() - started) * 1000),
                business_step="ai_video_status",
                business_objects=[{"type": "provider_task", "id": provider_task_id}],
            )
            return StandardTaskStatus(
                provider=self.provider_name,
                provider_task_id=provider_task_id,
                status=status,
                output_paths=_output_paths(data),
                error=error,
                raw_response=data,
            )
        except Exception as exc:
            record_business_model_call(
                stage=VIDEO_PROFILE_STAGE,
                label=self.profile.label,
                provider=self.provider_name,
                model=self.profile.model,
                input_payload={"provider_task_id": provider_task_id},
                output_payload=data or {"error": str(exc)},
                success=False,
                duration_ms=int((time.monotonic() - started) * 1000),
                business_step="ai_video_status",
                business_objects=[{"type": "provider_task", "id": provider_task_id}],
            )
            raise


def task_mode_from_workflow(workflow_name: str) -> str:
    name = Path(workflow_name).stem.casefold()
    if "image_to_video" in name or "i2v" in name:
        return "i2v"
    if "first_last" in name:
        return "first_last_frame"
    return "t2v"
