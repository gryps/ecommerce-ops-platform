from __future__ import annotations

import shutil
import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from urllib.parse import urlparse

from app.config import settings


@dataclass
class BrowserSession:
    id: str
    platform_url: str
    process: subprocess.Popen[bytes]
    profile_dir: Path


_sessions: dict[str, BrowserSession] = {}
_lock = Lock()


def _chrome_binary() -> str:
    candidates = [
        shutil.which("google-chrome"),
        shutil.which("google-chrome-stable"),
        "/mnt/c/Program Files/Google/Chrome/Application/chrome.exe",
        "/mnt/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return candidate
    raise RuntimeError("未找到 Chrome 或 Edge，无法启动平台浏览器")


def _validate_platform_url(value: str) -> str:
    url = value.strip()
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("请输入有效的平台商品发布页面地址")
    return url


def session_dict(session: BrowserSession) -> dict[str, str]:
    return {
        "id": session.id,
        "platform_url": session.platform_url,
        "status": "running" if session.process.poll() is None else "stopped",
    }


def start_browser_session(platform_url: str) -> dict[str, str]:
    url = _validate_platform_url(platform_url)
    with _lock:
        for session in _sessions.values():
            if session.process.poll() is None:
                raise RuntimeError("已有平台浏览器会话正在运行，请先退出当前自动化")
        session_id = uuid.uuid4().hex
        profile_dir = settings.workspace_dir / "image-commerce" / "browser-profiles" / session_id
        profile_dir.mkdir(parents=True, exist_ok=True)
        process = subprocess.Popen(
            [
                _chrome_binary(),
                "--new-window",
                "--no-first-run",
                "--no-default-browser-check",
                f"--user-data-dir={profile_dir}",
                url,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        session = BrowserSession(session_id, url, process, profile_dir)
        _sessions[session_id] = session
        return session_dict(session)


def get_browser_session(session_id: str) -> dict[str, str]:
    with _lock:
        session = _sessions.get(session_id)
        if session is None:
            raise LookupError("平台浏览器会话不存在")
        return session_dict(session)


def stop_browser_session(session_id: str) -> None:
    with _lock:
        session = _sessions.pop(session_id, None)
    if session is None:
        raise LookupError("平台浏览器会话不存在")
    if session.process.poll() is None:
        session.process.terminate()
        try:
            session.process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            session.process.kill()
