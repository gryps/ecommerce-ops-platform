from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.v1.image.schemas import BrowserSessionCreateRequest
from app.domain.models import AdminUser
from app.services.auth import require_admin
from app.services.platform_browser import get_browser_session, start_browser_session, stop_browser_session


router = APIRouter()


@router.post("/browser-sessions", status_code=status.HTTP_201_CREATED)
def start_platform_browser(payload: BrowserSessionCreateRequest, _admin: AdminUser = Depends(require_admin)) -> dict[str, str]:
    try:
        return start_browser_session(payload.platform_url)
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/browser-sessions/{session_id}")
def get_platform_browser(session_id: str, _admin: AdminUser = Depends(require_admin)) -> dict[str, str]:
    try:
        return get_browser_session(session_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/browser-sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def stop_platform_browser(session_id: str, _admin: AdminUser = Depends(require_admin)) -> None:
    try:
        stop_browser_session(session_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
