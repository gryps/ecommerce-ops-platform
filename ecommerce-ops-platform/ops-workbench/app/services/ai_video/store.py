from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.core.database import session_scope
from app.domain.models import (
    AiVideoAsset,
    AiVideoGenerationTask,
    AiVideoProject,
    AiVideoShot,
    AiVideoTaskEvent,
)
from app.services.ai_video.models import Asset, GenerationTask, ProductProject, Shot, TaskEvent, WorkbenchStore, now_iso


def _parse_dt(value: str | datetime | None) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _iso(value: datetime | None) -> str:
    return value.isoformat() if value else now_iso()


class AiVideoRepository:
    """Database-backed AI video workbench store.

    ``path`` is kept only as a legacy JSON import location and as a stable
    anchor for existing tests. Normal reads and writes use SQLite/PostgreSQL.
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        self._import_lock = Lock()
        self._imported_legacy_json = False

    @property
    def storage_root(self) -> Path:
        return settings.runtime_dir / "ai-video"

    def ensure_ready(self) -> None:
        self.storage_root.mkdir(parents=True, exist_ok=True)
        (self.storage_root / "uploads").mkdir(parents=True, exist_ok=True)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with session_scope() as session:
            self._import_legacy_json_if_needed(session)

    def load(self) -> WorkbenchStore:
        self.ensure_ready()
        with session_scope() as session:
            projects = [
                ProductProject(
                    id=row.id,
                    name=row.name,
                    product_name=row.product_name,
                    selling_points=row.selling_points,
                    audience=row.audience,
                    tone=row.tone,
                    status=row.status,
                    created_at=_iso(row.created_at),
                    updated_at=_iso(row.updated_at),
                )
                for row in session.scalars(select(AiVideoProject).order_by(AiVideoProject.created_at.desc())).all()
            ]
            assets = [
                Asset(
                    id=row.id,
                    project_id=row.project_id,
                    kind=row.kind,
                    name=row.name,
                    file_path=row.file_path,
                    preview_url=row.preview_url,
                    notes=row.notes,
                    created_at=_iso(row.created_at),
                    updated_at=_iso(row.updated_at),
                )
                for row in session.scalars(select(AiVideoAsset).order_by(AiVideoAsset.created_at.desc())).all()
            ]
            shots = [
                Shot(
                    id=row.id,
                    project_id=row.project_id,
                    order=row.order_index,
                    title=row.title,
                    duration_seconds=row.duration_seconds,
                    visual_goal=row.visual_goal,
                    camera=row.camera,
                    prompt=row.prompt,
                    negative_prompt=row.negative_prompt,
                    required_asset_kinds=list(row.required_asset_kinds or []),
                    created_at=_iso(row.created_at),
                    updated_at=_iso(row.updated_at),
                )
                for row in session.scalars(select(AiVideoShot).order_by(AiVideoShot.project_id, AiVideoShot.order_index)).all()
            ]
            tasks = [
                GenerationTask(
                    id=row.id,
                    project_id=row.project_id,
                    engine=row.engine,
                    workflow_name=row.workflow_name,
                    prompt=row.prompt,
                    input_asset_ids=list(row.input_asset_ids or []),
                    provider_task_id=row.provider_task_id,
                    status=row.status,
                    output_paths=list(row.output_paths or []),
                    error=row.error,
                    created_at=_iso(row.created_at),
                    updated_at=_iso(row.updated_at),
                )
                for row in session.scalars(select(AiVideoGenerationTask).order_by(AiVideoGenerationTask.created_at.desc())).all()
            ]
        return WorkbenchStore(projects=projects, assets=assets, shots=shots, tasks=tasks)

    def save(self, store: WorkbenchStore) -> None:
        with session_scope() as session:
            session.query(AiVideoTaskEvent).delete()
            session.query(AiVideoGenerationTask).delete()
            session.query(AiVideoShot).delete()
            session.query(AiVideoAsset).delete()
            session.query(AiVideoProject).delete()
            for project in store.projects:
                session.add(self._project_row(project))
            for asset in store.assets:
                session.add(self._asset_row(asset))
            for shot in store.shots:
                session.add(self._shot_row(shot))
            for task in store.tasks:
                session.add(self._task_row(task))

    def add_project(self, project: ProductProject) -> ProductProject:
        project.name = project.name.strip()
        project.product_name = project.product_name.strip()
        if not project.name:
            raise ValueError("AI视频项目名不能为空")
        with session_scope() as session:
            duplicate = session.scalar(
                select(AiVideoProject.id).where(func.lower(AiVideoProject.name) == project.name.lower()).limit(1)
            )
            if duplicate:
                raise ValueError("AI视频项目名已存在")
            session.add(self._project_row(project))
        return project

    def delete_project(self, project_id: str) -> None:
        with session_scope() as session:
            project = self._require_project(session, project_id)
            task_ids = [
                row.id
                for row in session.scalars(select(AiVideoGenerationTask).where(AiVideoGenerationTask.project_id == project_id)).all()
            ]
            if task_ids:
                for event in session.scalars(select(AiVideoTaskEvent).where(AiVideoTaskEvent.task_id.in_(task_ids))).all():
                    session.delete(event)
                for task in session.scalars(select(AiVideoGenerationTask).where(AiVideoGenerationTask.id.in_(task_ids))).all():
                    session.delete(task)
            for shot in session.scalars(select(AiVideoShot).where(AiVideoShot.project_id == project_id)).all():
                session.delete(shot)
            for asset in session.scalars(select(AiVideoAsset).where(AiVideoAsset.project_id == project_id)).all():
                session.delete(asset)
            session.delete(project)

    def add_asset(self, asset: Asset) -> Asset:
        with session_scope() as session:
            self._require_project(session, asset.project_id)
            session.add(self._asset_row(asset))
        return asset

    def replace_project_shots(self, project_id: str, shots: list[Shot]) -> list[Shot]:
        with session_scope() as session:
            self._require_project(session, project_id)
            for row in session.scalars(select(AiVideoShot).where(AiVideoShot.project_id == project_id)).all():
                session.delete(row)
            for shot in shots:
                session.add(self._shot_row(shot))
        return shots

    def add_task(self, task: GenerationTask) -> GenerationTask:
        task.updated_at = now_iso()
        with session_scope() as session:
            self._require_project(session, task.project_id)
            session.add(self._task_row(task))
            session.add(
                AiVideoTaskEvent(
                    task_id=task.id,
                    event_type="created",
                    message="生成任务已创建",
                    payload={"engine": task.engine, "workflow_name": task.workflow_name},
                )
            )
        return task

    def get_task(self, task_id: str) -> GenerationTask:
        with session_scope() as session:
            row = session.get(AiVideoGenerationTask, task_id)
            if row is None:
                raise LookupError("AI视频任务不存在")
            return self._task_model(row)

    def task_events(self, task_id: str) -> list[TaskEvent]:
        with session_scope() as session:
            if session.get(AiVideoGenerationTask, task_id) is None:
                raise LookupError("AI视频任务不存在")
            rows = session.scalars(
                select(AiVideoTaskEvent)
                .where(AiVideoTaskEvent.task_id == task_id)
                .order_by(AiVideoTaskEvent.created_at)
            ).all()
            return [
                TaskEvent(
                    id=row.id,
                    task_id=row.task_id,
                    event_type=row.event_type,
                    message=row.message,
                    payload=dict(row.payload or {}),
                    created_at=_iso(row.created_at),
                )
                for row in rows
            ]

    def update_task_status(
        self,
        task_id: str,
        *,
        status: str,
        provider_task_id: str = "",
        output_paths: list[str] | None = None,
        error: str = "",
        event_type: str = "status_changed",
        message: str = "",
        payload: dict[str, Any] | None = None,
    ) -> GenerationTask:
        with session_scope() as session:
            row = session.get(AiVideoGenerationTask, task_id)
            if row is None:
                raise LookupError("AI视频任务不存在")
            row.status = status
            row.provider_task_id = provider_task_id or row.provider_task_id
            row.output_paths = list(output_paths if output_paths is not None else row.output_paths or [])
            row.error = error
            row.updated_at = datetime.now().astimezone()
            session.add(
                AiVideoTaskEvent(
                    task_id=task_id,
                    event_type=event_type,
                    message=message or status,
                    payload=payload or {},
                )
            )
            session.flush()
            return self._task_model(row)

    def _import_legacy_json_if_needed(self, session: Session) -> None:
        marker_path = self.path.with_suffix(f"{self.path.suffix}.imported")
        if self._imported_legacy_json or marker_path.exists() or not self.path.exists():
            self._imported_legacy_json = True
            return
        with self._import_lock:
            if self._imported_legacy_json or marker_path.exists():
                self._imported_legacy_json = True
                return
            if session.scalar(select(AiVideoProject.id).limit(1)):
                marker_path.touch()
                self._imported_legacy_json = True
                return
            store = WorkbenchStore.model_validate(json.loads(self.path.read_text(encoding="utf-8")))
            for project in store.projects:
                session.add(self._project_row(project))
            for asset in store.assets:
                session.add(self._asset_row(asset))
            for shot in store.shots:
                session.add(self._shot_row(shot))
            for task in store.tasks:
                session.add(self._task_row(task))
            marker_path.touch()
            self._imported_legacy_json = True

    @staticmethod
    def _require_project(session: Session, project_id: str) -> AiVideoProject:
        project = session.get(AiVideoProject, project_id)
        if project is None:
            raise LookupError("AI视频项目不存在")
        return project

    @staticmethod
    def _project_row(project: ProductProject) -> AiVideoProject:
        return AiVideoProject(
            id=project.id,
            name=project.name,
            product_name=project.product_name,
            selling_points=project.selling_points,
            audience=project.audience,
            tone=project.tone,
            status=project.status,
            created_at=_parse_dt(project.created_at),
            updated_at=_parse_dt(project.updated_at),
        )

    @staticmethod
    def _asset_row(asset: Asset) -> AiVideoAsset:
        return AiVideoAsset(
            id=asset.id,
            project_id=asset.project_id,
            kind=asset.kind,
            name=asset.name,
            file_path=asset.file_path,
            preview_url=asset.preview_url,
            notes=asset.notes,
            created_at=_parse_dt(asset.created_at),
            updated_at=_parse_dt(asset.updated_at),
        )

    @staticmethod
    def _shot_row(shot: Shot) -> AiVideoShot:
        return AiVideoShot(
            id=shot.id,
            project_id=shot.project_id,
            order_index=shot.order,
            title=shot.title,
            duration_seconds=shot.duration_seconds,
            visual_goal=shot.visual_goal,
            camera=shot.camera,
            prompt=shot.prompt,
            negative_prompt=shot.negative_prompt,
            required_asset_kinds=list(shot.required_asset_kinds),
            created_at=_parse_dt(shot.created_at),
            updated_at=_parse_dt(shot.updated_at),
        )

    @staticmethod
    def _task_row(task: GenerationTask) -> AiVideoGenerationTask:
        return AiVideoGenerationTask(
            id=task.id,
            project_id=task.project_id,
            engine=task.engine,
            workflow_name=task.workflow_name,
            prompt=task.prompt,
            input_asset_ids=list(task.input_asset_ids),
            provider_task_id=task.provider_task_id,
            status=task.status,
            output_paths=list(task.output_paths),
            error=task.error,
            created_at=_parse_dt(task.created_at),
            updated_at=_parse_dt(task.updated_at),
        )

    @staticmethod
    def _task_model(row: AiVideoGenerationTask) -> GenerationTask:
        return GenerationTask(
            id=row.id,
            project_id=row.project_id,
            engine=row.engine,
            workflow_name=row.workflow_name,
            prompt=row.prompt,
            input_asset_ids=list(row.input_asset_ids or []),
            provider_task_id=row.provider_task_id,
            status=row.status,
            output_paths=list(row.output_paths or []),
            error=row.error,
            created_at=_iso(row.created_at),
            updated_at=_iso(row.updated_at),
        )


repository = AiVideoRepository(settings.runtime_dir / "ai-video" / "databases" / "workbench.json")
