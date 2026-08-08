from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Literal


OperationStatus = Literal["processing", "completed", "failed"]


@dataclass(frozen=True)
class OperationState:
    operation_id: str
    kind: str
    status: OperationStatus
    detail: str
    updated_at: datetime


_states: dict[str, OperationState] = {}
_lock = Lock()
_retention = timedelta(hours=24)


def _prune(now: datetime) -> None:
    expired = [key for key, value in _states.items() if now - value.updated_at > _retention]
    for key in expired:
        _states.pop(key, None)


def begin_operation(operation_id: str, kind: str) -> OperationState:
    """Atomically register a browser-visible long-running operation."""
    now = datetime.now(timezone.utc)
    with _lock:
        _prune(now)
        existing = _states.get(operation_id)
        if existing is not None:
            raise ValueError("该操作已经提交，请等待原操作完成")
        state = OperationState(operation_id, kind, "processing", "", now)
        _states[operation_id] = state
        return state


def finish_operation(operation_id: str, status: Literal["completed", "failed"], detail: str = "") -> OperationState:
    now = datetime.now(timezone.utc)
    with _lock:
        current = _states.get(operation_id)
        if current is None:
            raise KeyError(operation_id)
        state = OperationState(operation_id, current.kind, status, detail[:1000], now)
        _states[operation_id] = state
        return state


def get_operation(operation_id: str) -> OperationState | None:
    now = datetime.now(timezone.utc)
    with _lock:
        _prune(now)
        return _states.get(operation_id)
