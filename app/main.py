from __future__ import annotations

import asyncio
import shutil
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import router as workbench_v1_router
from app.config import settings
from app.core.database import migrate_workbench_schema
from app.services.model_call_logs import maybe_cleanup_expired_model_call_logs


async def _maintenance_loop(stop: asyncio.Event) -> None:
    while not stop.is_set():
        await asyncio.to_thread(maybe_cleanup_expired_model_call_logs)
        try:
            await asyncio.wait_for(stop.wait(), timeout=3600)
        except TimeoutError:
            continue


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Prepare only the directories and schema used by the current workbench."""
    settings.workspace_dir.mkdir(parents=True, exist_ok=True)
    migrate_workbench_schema()
    stop = asyncio.Event()
    maintenance = asyncio.create_task(_maintenance_loop(stop))
    try:
        yield
    finally:
        stop.set()
        await maintenance


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(workbench_v1_router)


@app.get("/api/health")
def health() -> dict[str, bool]:
    return {
        "ok": True,
        "ffmpeg_available": shutil.which(settings.ffmpeg_binary) is not None,
        "ffprobe_available": shutil.which(settings.ffprobe_binary) is not None,
    }


app.mount(
    "/workbench",
    StaticFiles(directory="static-workbench", html=True),
    name="production-workbench",
)


@app.get("/", include_in_schema=False)
def redirect_to_workbench() -> RedirectResponse:
    return RedirectResponse(url="/workbench/", status_code=307)
