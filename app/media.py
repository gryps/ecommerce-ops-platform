from __future__ import annotations

import json
import subprocess
from fractions import Fraction
from pathlib import Path

from app.config import settings


VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".avi", ".mkv", ".webm"}


def resolve_source_directory(value: str) -> Path:
    path = Path(value).expanduser().resolve()
    if not path.is_dir():
        raise ValueError("素材目录不存在或不是目录")
    for configured in settings.mount_roots:
        root = Path(configured).expanduser().resolve()
        if path == root or root in path.parents:
            return path
    raise ValueError("素材目录不在允许的挂载根目录中")


def _parse_rate(value: str | None) -> float:
    if not value or value in {"0/0", "N/A"}:
        return 0.0
    try:
        return round(float(Fraction(value)), 6)
    except (ValueError, ZeroDivisionError):
        return 0.0


def probe_video(path: Path) -> dict[str, object]:
    try:
        completed = subprocess.run(
            [
                settings.ffprobe_binary,
                "-v",
                "error",
                "-print_format",
                "json",
                "-show_streams",
                "-show_format",
                str(path),
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=settings.media_probe_timeout_seconds,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("未安装 ffprobe") from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("媒体探测超时") from exc
    except subprocess.CalledProcessError as exc:
        message = (exc.stderr or "").strip()
        raise RuntimeError(f"视频无法解码：{message or 'ffprobe 失败'}") from exc
    payload = json.loads(completed.stdout)
    video = next(
        (
            stream
            for stream in payload.get("streams", [])
            if stream.get("codec_type") == "video"
        ),
        None,
    )
    if video is None:
        raise RuntimeError("文件中没有视频轨")
    width = int(video.get("width") or 0)
    height = int(video.get("height") or 0)
    duration = float(
        video.get("duration") or payload.get("format", {}).get("duration") or 0
    )
    if width <= 0 or height <= 0 or duration <= 0:
        raise RuntimeError("视频尺寸或时长无效")
    return {
        "duration_seconds": round(duration, 3),
        "width": width,
        "height": height,
        "fps": _parse_rate(video.get("avg_frame_rate") or video.get("r_frame_rate")),
        "codec": str(video.get("codec_name") or ""),
        "pixel_format": str(video.get("pix_fmt") or ""),
    }
