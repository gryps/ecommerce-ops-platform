from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

from app.config import settings
from app.services.ai_video.comfyui_client import ComfyUIClient
from app.services.ai_video.models import GenerationTask
from app.services.ai_video.provider_adapters import (
    OpenAICompatibleVideoAdapter,
    StandardVideoRequest,
    VideoInputFile,
    VideoProviderAdapter,
    task_mode_from_workflow,
)
from app.services.ai_video.store import repository


WORKFLOW_ROOT = Path(__file__).resolve().parents[3] / "workflows" / "comfyui"
OutputDownloader = Callable[[str, Path, int], Awaitable[str]]


def workflow_path(workflow_name: str) -> Path:
    safe_name = Path(workflow_name).name
    path = WORKFLOW_ROOT / f"{safe_name}.json"
    if path.exists():
        return path
    return WORKFLOW_ROOT / f"{safe_name}.example.json"


def load_workflow(workflow_name: str, task: GenerationTask) -> dict[str, Any]:
    path = workflow_path(workflow_name)
    if not path.exists():
        raise FileNotFoundError(f"未找到 ComfyUI workflow：{workflow_name}")
    raw = path.read_text(encoding="utf-8")
    rendered = (
        raw.replace("{{positive_prompt}}", task.prompt)
        .replace("{{negative_prompt}}", "")
        .replace("{{image_path}}", "")
        .replace("{{seed}}", "0")
    )
    workflow = json.loads(rendered)
    if "description" in workflow and "placeholder" in str(workflow["description"]).casefold():
        raise ValueError("当前 workflow 仍是占位文件，请先从 ComfyUI 导出 API 格式 workflow")
    return workflow


def build_video_request(task: GenerationTask) -> StandardVideoRequest:
    store = repository.load()
    assets = {asset.id: asset for asset in store.assets if asset.id in task.input_asset_ids}
    input_files = [
        VideoInputFile(
            role="start_image" if index == 0 else asset.kind,
            path=asset.file_path,
            url=asset.preview_url,
        )
        for index, asset in enumerate(assets.values())
    ]
    return StandardVideoRequest(
        mode=task_mode_from_workflow(task.workflow_name),
        prompt=task.prompt,
        input_files=input_files,
        metadata={"project_id": task.project_id, "task_id": task.id, "workflow_name": task.workflow_name},
    )


def _output_extension(url: str) -> str:
    suffix = Path(urlparse(url).path).suffix.lower()
    return suffix if suffix in {".mp4", ".mov", ".webm", ".m4v"} else ".mp4"


async def download_remote_output(url: str, target_dir: Path, index: int) -> str:
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"output-{index + 1:02d}{_output_extension(url)}"
    async with httpx.AsyncClient(timeout=120) as client:
        async with client.stream("GET", url) as response:
            response.raise_for_status()
            with target.open("wb") as output:
                async for chunk in response.aiter_bytes():
                    if chunk:
                        output.write(chunk)
    return str(target)


async def localize_output_paths(
    task: GenerationTask,
    output_paths: list[str],
    downloader: OutputDownloader | None = None,
) -> list[str]:
    target_dir = settings.runtime_dir / "ai-video" / "outputs" / task.project_id / task.id
    resolved: list[str] = []
    fetch = downloader or download_remote_output
    for index, value in enumerate(output_paths):
        if value.startswith(("http://", "https://")):
            resolved.append(await fetch(value, target_dir, index))
        else:
            resolved.append(value)
    return resolved


async def submit_generation_task(
    task_id: str,
    client: ComfyUIClient | None = None,
    video_adapter: VideoProviderAdapter | None = None,
) -> GenerationTask:
    task = repository.get_task(task_id)
    if task.engine == "vendor_video":
        try:
            request = build_video_request(task)
            result = await (video_adapter or OpenAICompatibleVideoAdapter()).submit(request)
            return repository.update_task_status(
                task_id,
                status="running" if result.status in {"queued", "running"} else result.status,
                provider_task_id=result.provider_task_id,
                event_type="submitted",
                message="任务已提交到视频模型 API",
                payload={"provider": result.provider, "response": result.raw_response},
            )
        except Exception as exc:
            return repository.update_task_status(
                task_id,
                status="failed",
                error=str(exc),
                event_type="submit_failed",
                message="视频模型 API 提交失败",
                payload={"error": str(exc), "workflow_name": task.workflow_name},
            )
    if task.engine != "comfyui":
        return repository.update_task_status(
            task_id,
            status="failed",
            error=f"未知 AI 视频任务引擎：{task.engine}",
            event_type="adapter_missing",
            message="未知 AI 视频任务引擎",
            payload={"engine": task.engine},
        )
    try:
        workflow = load_workflow(task.workflow_name, task)
        queued = await (client or ComfyUIClient()).queue_prompt(workflow)
        return repository.update_task_status(
            task_id,
            status="running",
            provider_task_id=str(queued.get("prompt_id") or ""),
            event_type="submitted",
            message="任务已提交到 ComfyUI",
            payload=queued,
        )
    except Exception as exc:
        return repository.update_task_status(
            task_id,
            status="failed",
            error=str(exc),
            event_type="submit_failed",
            message="任务提交失败",
            payload={"error": str(exc), "workflow_name": task.workflow_name},
        )


async def refresh_generation_task(
    task_id: str,
    video_adapter: VideoProviderAdapter | None = None,
    output_downloader: OutputDownloader | None = None,
) -> GenerationTask:
    task = repository.get_task(task_id)
    if task.engine != "vendor_video":
        return repository.update_task_status(
            task_id,
            status=task.status,
            event_type="status_checked",
            message="当前任务不是厂商视频 API 任务",
            payload={"engine": task.engine, "status": task.status},
        )
    if not task.provider_task_id:
        return repository.update_task_status(
            task_id,
            status="failed",
            error="任务尚未提交到视频模型 API，缺少厂商任务 ID",
            event_type="status_check_failed",
            message="缺少厂商任务 ID",
        )
    try:
        result = await (video_adapter or OpenAICompatibleVideoAdapter()).get_status(task.provider_task_id)
        output_paths = result.output_paths
        if result.status == "succeeded" and output_paths:
            output_paths = await localize_output_paths(task, output_paths, output_downloader)
        return repository.update_task_status(
            task_id,
            status=result.status,
            output_paths=output_paths,
            error=result.error,
            event_type="status_checked",
            message="已同步视频模型 API 任务状态",
            payload={
                "provider": result.provider,
                "response": result.raw_response,
                "remote_output_paths": result.output_paths,
                "output_paths": output_paths,
            },
        )
    except Exception as exc:
        return repository.update_task_status(
            task_id,
            status="failed",
            error=str(exc),
            event_type="status_check_failed",
            message="视频模型 API 状态同步失败",
            payload={"error": str(exc), "provider_task_id": task.provider_task_id},
        )
