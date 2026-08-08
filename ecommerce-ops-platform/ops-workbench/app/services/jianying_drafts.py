from __future__ import annotations

import json
import re
import shutil
import subprocess
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.domain.models import CopyContent, JianyingDraft, MusicResource, NarrationAsset, WorkbenchSetting

SETTING_KEY = "jianying_draft_directory"
DUPLICATE_COUNTER_COUNTS_KEY = "jianying_draft_duplicate_counter_counts"
DUPLICATE_COUNTER_RESETS_KEY = "jianying_draft_duplicate_counter_resets"
COPY_ONLY_DURATION_MICROSECONDS = 5_000_000
MAX_FALLBACK_AUDIO_SECONDS = 30 * 60


def _microseconds(seconds: float) -> int:
    return max(0, round(seconds * 1_000_000))


def _probe_audio_duration_seconds(path: Path) -> float:
    result = subprocess.run(
        [
            settings.ffprobe_binary,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=nw=1:nk=1",
            str(path),
        ],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=settings.media_probe_timeout_seconds,
    )
    try:
        duration = float(result.stdout.decode("utf-8").strip())
    except ValueError:
        duration = 0
    if result.returncode != 0 or duration <= 0:
        detail = result.stderr.decode("utf-8", errors="replace")[-300:]
        raise ValueError(detail or "音频时长读取失败")
    return duration


def _safe_audio_duration_microseconds(path: Path, fallback_seconds: float = 0) -> int:
    try:
        return _microseconds(_probe_audio_duration_seconds(path))
    except ValueError:
        if 0 < fallback_seconds <= MAX_FALLBACK_AUDIO_SECONDS:
            return _microseconds(fallback_seconds)
        raise


def _windows_path(path: Path) -> str:
    resolved = str(path.resolve())
    if resolved.startswith("/mnt/") and len(resolved) > 6:
        drive = resolved[5].upper()
        tail = resolved[7:].replace("/", "\\")
        return f"{drive}:\\{tail}"
    return resolved


def _jianying_path(path: Path) -> str:
    return _windows_path(path).replace("\\", "/")


def _material_id() -> str:
    return str(uuid.uuid4()).upper()


def _sanitize_name(value: str) -> str:
    clean = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "-", value.strip())
    clean = re.sub(r"\s+", " ", clean).strip(" .")
    return clean[:120] or "无视频剪映草稿"


def _timestamped_name(value: str) -> str:
    base = _sanitize_name(value or "无视频剪映草稿")
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return _sanitize_name(f"{base}-{stamp}")


def _duplicate_combo_key(
    copy_content_id: str | None,
    narration_asset_id: str | None,
    music_resource_id: str | None,
) -> str:
    return "|".join(
        [
            f"copy={copy_content_id or ''}",
            f"narration={narration_asset_id or ''}",
            f"music={music_resource_id or ''}",
        ]
    )


def _matching_draft_record_count(
    session: Session,
    *,
    copy_content_id: str | None,
    narration_asset_id: str | None,
    music_resource_id: str | None,
) -> int:
    return int(
        session.scalar(
            select(func.count(JianyingDraft.id)).where(
                JianyingDraft.copy_content_id == copy_content_id if copy_content_id else JianyingDraft.copy_content_id.is_(None),
                JianyingDraft.narration_asset_id == narration_asset_id if narration_asset_id else JianyingDraft.narration_asset_id.is_(None),
                JianyingDraft.music_resource_id == music_resource_id if music_resource_id else JianyingDraft.music_resource_id.is_(None),
            )
        )
        or 0
    )


def _counter_value(
    session: Session,
    setting_key: str,
    *,
    copy_content_id: str | None,
    narration_asset_id: str | None,
    music_resource_id: str | None,
) -> int:
    item = session.get(WorkbenchSetting, setting_key)
    if item is None:
        return 0
    return int((item.value or {}).get(_duplicate_combo_key(copy_content_id, narration_asset_id, music_resource_id)) or 0)


def _set_counter_value(
    session: Session,
    setting_key: str,
    *,
    copy_content_id: str | None,
    narration_asset_id: str | None,
    music_resource_id: str | None,
    value: int,
) -> None:
    item = session.get(WorkbenchSetting, setting_key)
    payload = dict(item.value or {}) if item is not None else {}
    payload[_duplicate_combo_key(copy_content_id, narration_asset_id, music_resource_id)] = max(0, int(value))
    if item is None:
        item = WorkbenchSetting(key=setting_key, value=payload)
        session.add(item)
    else:
        item.value = payload


def _generated_counter_value(
    session: Session,
    *,
    copy_content_id: str | None,
    narration_asset_id: str | None,
    music_resource_id: str | None,
) -> int:
    stored_count = _counter_value(
        session,
        DUPLICATE_COUNTER_COUNTS_KEY,
        copy_content_id=copy_content_id,
        narration_asset_id=narration_asset_id,
        music_resource_id=music_resource_id,
    )
    record_count = _matching_draft_record_count(
        session,
        copy_content_id=copy_content_id,
        narration_asset_id=narration_asset_id,
        music_resource_id=music_resource_id,
    )
    return max(stored_count, record_count)


def _record_jianying_draft_generation(
    session: Session,
    *,
    copy_content_id: str | None,
    narration_asset_id: str | None,
    music_resource_id: str | None,
    generated_count: int,
) -> None:
    _set_counter_value(
        session,
        DUPLICATE_COUNTER_COUNTS_KEY,
        copy_content_id=copy_content_id,
        narration_asset_id=narration_asset_id,
        music_resource_id=music_resource_id,
        value=generated_count,
    )


def _stored_directory(session: Session) -> str:
    item = session.get(WorkbenchSetting, SETTING_KEY)
    if item is None:
        return ""
    return str((item.value or {}).get("path") or "")


def _is_writable_directory(path: Path) -> bool:
    if not path.is_dir():
        return False
    try:
        probe = path / f".codexwork-write-test-{uuid.uuid4().hex}"
        probe.write_text("", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return True
    except OSError:
        return False


def validate_jianying_draft_directory(path_value: str) -> Path:
    path = Path(path_value).expanduser().resolve()
    if not _is_writable_directory(path):
        raise ValueError("剪映草稿目录不存在或不可写")
    return path


def save_jianying_draft_directory(session: Session, path_value: str) -> str:
    path = validate_jianying_draft_directory(path_value)
    item = session.get(WorkbenchSetting, SETTING_KEY)
    payload = {"path": str(path), "windows_path": _windows_path(path), "confirmed_at": int(time.time())}
    if item is None:
        item = WorkbenchSetting(key=SETTING_KEY, value=payload)
        session.add(item)
    else:
        item.value = payload
    session.flush()
    return str(path)


def _candidate_directories() -> list[Path]:
    candidates: list[Path] = []
    home = Path.home()
    candidates.extend(
        [
            home / "AppData/Local/JianyingPro/User Data/Projects/com.lveditor.draft",
            home / "AppData/Local/JianyingPro/User Data/Projects/com.lveditor.draft/root_draft",
            home / "AppData/Local/CapCut/User Data/Projects/com.lveditor.draft",
        ]
    )
    for users_root in (Path("/mnt/c/Users"), Path("/mnt/d/Users"), Path("/mnt/e/Users")):
        if not users_root.is_dir():
            continue
        for user_dir in users_root.iterdir():
            if not user_dir.is_dir():
                continue
            candidates.extend(
                [
                    user_dir / "AppData/Local/JianyingPro/User Data/Projects/com.lveditor.draft",
                    user_dir / "AppData/Local/JianyingPro/User Data/Projects/com.lveditor.draft/root_draft",
                    user_dir / "AppData/Local/CapCut/User Data/Projects/com.lveditor.draft",
                ]
            )
    seen: set[str] = set()
    result: list[Path] = []
    for candidate in candidates:
        key = str(candidate)
        if key not in seen:
            result.append(candidate)
            seen.add(key)
    return result


def detect_jianying_draft_directory(session: Session) -> dict[str, Any]:
    stored = _stored_directory(session)
    if stored:
        path = Path(stored).expanduser().resolve()
        if _is_writable_directory(path):
            return {"path": str(path), "windows_path": _windows_path(path), "source": "saved", "exists": True}
    for candidate in _candidate_directories():
        if _is_writable_directory(candidate):
            path = candidate.resolve()
            return {"path": str(path), "windows_path": _windows_path(path), "source": "detected", "exists": True}
    return {"path": stored, "windows_path": _windows_path(Path(stored)) if stored else "", "source": "missing", "exists": False}


def _next_draft_root(destination_dir: Path, name: str) -> Path:
    base = _sanitize_name(name)
    candidate = destination_dir / base
    if not candidate.exists():
        return candidate
    index = 2
    while True:
        candidate = destination_dir / f"{base}-{index}"
        if not candidate.exists():
            return candidate
        index += 1


def _subtitle_end_microseconds(narration: NarrationAsset | None) -> int:
    if narration is None:
        return 0
    end = 0.0
    for row in list(narration.subtitle_cues or []):
        try:
            end = max(end, float(row.get("end_seconds") or 0))
        except (TypeError, ValueError):
            continue
    return _microseconds(end)


def _narration_duration_microseconds(narration: NarrationAsset | None) -> int:
    if narration is None:
        return 0
    audio_path = Path(narration.audio_path)
    if audio_path.is_file():
        fallback = 0.0
        metadata = dict(narration.metadata_json or {})
        for key in ("duration_seconds", "audio_duration_seconds"):
            try:
                fallback = float(metadata.get(key) or 0)
            except (TypeError, ValueError):
                fallback = 0.0
            if fallback > 0:
                break
        return _safe_audio_duration_microseconds(audio_path, fallback)
    metadata = dict(narration.metadata_json or {})
    for key in ("duration_seconds", "audio_duration_seconds"):
        try:
            value = float(metadata.get(key) or 0)
        except (TypeError, ValueError):
            value = 0
        if value > 0:
            return _microseconds(value)
    return _subtitle_end_microseconds(narration)


def _effective_subtitle_end_microseconds(subtitle_end: int, narration_duration: int) -> int:
    if subtitle_end <= 0:
        return 0
    if narration_duration > 0:
        return min(subtitle_end, narration_duration)
    return subtitle_end


def _copy_text_duration_microseconds(effective_subtitle_end: int, narration_duration: int, total_duration: int) -> int:
    narration_text_duration = max(effective_subtitle_end, narration_duration)
    if narration_text_duration > 0:
        return narration_text_duration
    if total_duration > 0:
        return min(total_duration, COPY_ONLY_DURATION_MICROSECONDS)
    return COPY_ONLY_DURATION_MICROSECONDS


def _text_material(content: str) -> tuple[str, dict[str, Any]]:
    material_id = _material_id()
    encoded_content = json.dumps(
        {
            "text": content,
            "styles": [
                {
                    "range": [0, len(content.encode("utf-16-le"))],
                    "fill": {"content": {"solid": {"color": [1, 1, 1]}}},
                    "size": 8,
                }
            ],
            "layer_weight": 1,
            "effect": [],
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return material_id, {
        "id": material_id,
        "content": encoded_content,
        "type": "text",
        "font_name": "",
        "font_size": 8.0,
        "text_color": "#FFFFFFFF",
        "text_alpha": 1.0,
        "border_color": "#000000FF",
        "border_width": 0.0,
        "border_alpha": 1.0,
        "background_color": "#00000000",
        "background_alpha": 0.0,
        "background_style": 0,
        "background_round_radius": 0.0,
        "background_width": 0.14,
        "background_height": 0.14,
        "background_horizontal_offset": 0.0,
        "background_vertical_offset": 0.0,
        "has_shadow": False,
        "shadow_alpha": 0.8,
        "shadow_angle": -45.0,
        "shadow_color": "#000000FF",
        "shadow_distance": 8.0,
        "shadow_smoothing": 1.0,
        "text_alignment": 1,
        "vertical": False,
        "fixed_width": -1.0,
        "fixed_height": -1.0,
        "letter_spacing": 0.0,
        "line_feed": 1,
        "line_spacing": 0.02,
        "is_rich_text": False,
        "use_effect_default_color": False,
    }


def _empty_materials() -> dict[str, list[dict[str, Any]]]:
    return {
        "videos": [],
        "audios": [],
        "texts": [],
        "stickers": [],
        "video_effects": [],
        "material_animations": [],
        "transitions": [],
        "masks": [],
        "common_masks": [],
        "canvases": [],
        "speeds": [],
        "audio_fades": [],
        "placeholder_infos": [],
        "vocal_separations": [],
        "sound_channel_mappings": [],
        "smart_crops": [],
        "manual_deformations": [],
    }


def _audio_material(material_id: str, path: Path, duration: int, role: str) -> dict[str, Any]:
    return {
        "id": material_id,
        "type": "extract_music" if role == "music" else "record",
        "name": path.name,
        "music_id": "",
        "path": _jianying_path(path),
        "duration": duration,
        "wave_points": [],
        "category_id": "",
        "category_name": "local",
        "source_platform": 0,
        "tone_category_id": "",
        "tone_category_name": "",
        "tone_effect_id": "",
        "tone_effect_name": "",
        "is_ai_generate_content": False,
        "local_material_id": material_id,
    }


def _track(track_type: str, segments: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "id": _material_id(),
        "type": track_type,
        "name": "",
        "attribute": 0,
        "segments": segments,
    }


def _audio_segment(material_id: str, duration: int, volume: float, render_index: int) -> dict[str, Any]:
    return {
        "id": _material_id(),
        "material_id": material_id,
        "source_timerange": {"start": 0, "duration": duration},
        "target_timerange": {"start": 0, "duration": duration},
        "extra_material_refs": [],
        "clip": None,
        "speed": 1.0,
        "volume": volume,
        "last_nonzero_volume": volume,
        "visible": True,
        "render_index": render_index,
        "render_uniform_index": -1,
        "track_attribute": 0,
        "track_render_index": render_index,
        "uniform_scale": {"on": True, "value": 1.0},
        "common_keyframes": [],
        "keyframe_refs": [],
        "template_id": "",
        "template_scene": "default",
    }


def _text_segment(material_id: str, start: int, duration: int, role: str, render_index: int) -> dict[str, Any]:
    return {
        "id": _material_id(),
        "material_id": material_id,
        "target_timerange": {"start": start, "duration": duration},
        "extra_material_refs": [],
        "clip": {
            "alpha": 1.0,
            "rotation": 0.0,
            "scale": {"x": 1.0, "y": 1.0},
            "transform": {"x": 0.0, "y": -0.78 if role == "subtitle" else 0.78},
            "flip": {"horizontal": False, "vertical": False},
        },
        "speed": 1.0,
        "volume": 1.0,
        "visible": True,
        "render_index": render_index,
        "render_uniform_index": -1,
        "track_attribute": 0,
        "track_render_index": render_index,
        "role": role,
        "common_keyframes": [],
        "keyframe_refs": [],
        "template_id": "",
        "template_scene": "default",
    }


def _copy_audio_to_draft(source: Path, draft_root: Path, prefix: str) -> Path:
    audio_root = draft_root / "assets" / "audio"
    audio_root.mkdir(parents=True, exist_ok=True)
    suffix = source.suffix.lower() or ".wav"
    target = audio_root / f"{prefix}-{uuid.uuid4().hex}{suffix}"
    shutil.copy2(source, target)
    return target


def _sidecar_meta(draft_id: str, name: str, draft_root: Path, destination: Path, total_duration: int, material_count: int) -> dict[str, Any]:
    now_us = int(time.time() * 1_000_000)
    return {
        "cloud_draft_cover": False,
        "cloud_draft_sync": False,
        "cloud_package_completed_time": "",
        "draft_cloud_capcut_purchase_info": "",
        "draft_cloud_last_action_download": False,
        "draft_cloud_package_type": "",
        "draft_cloud_purchase_info": "",
        "draft_cloud_template_id": "",
        "draft_cloud_tutorial_info": "",
        "draft_cloud_videocut_purchase_info": "",
        "draft_cover": "draft_cover.jpg",
        "draft_deeplink_url": "",
        "draft_enterprise_info": {"draft_enterprise_extra": "", "draft_enterprise_id": "", "draft_enterprise_name": "", "enterprise_material": []},
        "draft_fold_path": _jianying_path(draft_root),
        "draft_id": draft_id,
        "draft_is_ae_produce": False,
        "draft_is_ai_packaging_used": False,
        "draft_is_ai_shorts": False,
        "draft_is_ai_translate": False,
        "draft_is_article_video_draft": False,
        "draft_is_cloud_temp_draft": False,
        "draft_is_from_deeplink": "false",
        "draft_is_invisible": False,
        "draft_is_pippit_draft": False,
        "draft_is_web_article_video": False,
        "draft_materials": [],
        "draft_materials_copied_info": [],
        "draft_name": name,
        "draft_need_rename_folder": False,
        "draft_new_version": "",
        "draft_removable_storage_device": "",
        "draft_root_path": _jianying_path(destination),
        "draft_segment_extra_info": [],
        "draft_timeline_materials_size_": material_count,
        "draft_type": "",
        "draft_web_article_video_enter_from": "",
        "pippit_avatar_url": "",
        "pippit_extra_info": "",
        "pippit_id": "",
        "pippit_user_name": "",
        "tm_draft_cloud_completed": "",
        "tm_draft_cloud_entry_id": -1,
        "tm_draft_cloud_modified": 0,
        "tm_draft_cloud_parent_entry_id": -1,
        "tm_draft_cloud_space_id": -1,
        "tm_draft_cloud_user_id": -1,
        "tm_draft_create": now_us,
        "tm_draft_modified": now_us,
        "tm_draft_removed": 0,
        "tm_duration": total_duration,
    }


def duplicate_jianying_draft_usage_count(
    session: Session,
    *,
    copy_content_id: str | None,
    narration_asset_id: str | None,
    music_resource_id: str | None,
) -> int:
    raw_count = _generated_counter_value(
        session,
        copy_content_id=copy_content_id,
        narration_asset_id=narration_asset_id,
        music_resource_id=music_resource_id,
    )
    reset_value = _counter_value(
        session,
        DUPLICATE_COUNTER_RESETS_KEY,
        copy_content_id=copy_content_id,
        narration_asset_id=narration_asset_id,
        music_resource_id=music_resource_id,
    )
    return max(0, raw_count - reset_value)


def reset_jianying_draft_duplicate_counter(
    session: Session,
    *,
    copy_content_id: str | None,
    narration_asset_id: str | None,
    music_resource_id: str | None,
) -> int:
    raw_count = _generated_counter_value(
        session,
        copy_content_id=copy_content_id,
        narration_asset_id=narration_asset_id,
        music_resource_id=music_resource_id,
    )
    _set_counter_value(
        session,
        DUPLICATE_COUNTER_RESETS_KEY,
        copy_content_id=copy_content_id,
        narration_asset_id=narration_asset_id,
        music_resource_id=music_resource_id,
        value=raw_count,
    )
    session.flush()
    return 0


def create_jianying_draft(
    session: Session,
    *,
    name: str,
    destination_dir: str,
    copy_content_id: str | None,
    narration_asset_id: str | None,
    music_resource_id: str | None,
    created_by: str | None,
) -> JianyingDraft:
    copy = session.get(CopyContent, copy_content_id) if copy_content_id else None
    if copy_content_id and copy is None:
        raise ValueError("文案不存在")
    narration = session.get(NarrationAsset, narration_asset_id) if narration_asset_id else None
    if narration_asset_id and (narration is None or narration.status != "approved"):
        raise ValueError("旁白与字幕不存在或尚未确认")
    if narration and not Path(narration.audio_path).is_file():
        raise ValueError("旁白音频文件不可访问")
    music = session.get(MusicResource, music_resource_id) if music_resource_id else None
    if music_resource_id and (
        music is None or music.status != "ready" or not Path(music.file_path).is_file()
    ):
        raise ValueError("背景音乐不存在或尚未就绪")
    if copy is None and narration is None and music is None:
        raise ValueError("至少选择文案、字幕/旁白或背景音乐中的一种")

    destination = validate_jianying_draft_directory(destination_dir)
    generated_usage_count = _generated_counter_value(
        session,
        copy_content_id=copy.id if copy else None,
        narration_asset_id=narration.id if narration else None,
        music_resource_id=music.id if music else None,
    )
    duplicate_usage_count = duplicate_jianying_draft_usage_count(
        session,
        copy_content_id=copy.id if copy else None,
        narration_asset_id=narration.id if narration else None,
        music_resource_id=music.id if music else None,
    )
    draft_name = _timestamped_name(name or "无视频剪映草稿")
    draft_root = _next_draft_root(destination, draft_name).resolve()

    subtitle_end = _subtitle_end_microseconds(narration)
    narration_duration = _narration_duration_microseconds(narration)
    effective_subtitle_end = _effective_subtitle_end_microseconds(subtitle_end, narration_duration)
    music_duration = _safe_audio_duration_microseconds(Path(music.file_path), music.duration_seconds) if music else 0
    timed_duration = max(effective_subtitle_end, narration_duration, music_duration)
    total_duration = timed_duration or COPY_ONLY_DURATION_MICROSECONDS

    draft = JianyingDraft(
        name=draft_root.name,
        copy_content_id=copy.id if copy else None,
        narration_asset_id=narration.id if narration else None,
        music_resource_id=music.id if music else None,
        created_by=created_by,
        status="generating",
    )
    session.add(draft)
    session.flush()

    draft_root.mkdir(parents=False, exist_ok=False)
    text_materials: list[dict[str, Any]] = []
    copy_text_segments: list[dict[str, Any]] = []
    subtitle_text_segments: list[dict[str, Any]] = []
    if copy and copy.content_text.strip():
        material_id, material = _text_material(copy.content_text.strip())
        text_materials.append(material)
        copy_text_segments.append(
            {
                "id": _material_id(),
                "material_id": material_id,
                "target_timerange": {
                    "start": 0,
                    "duration": _copy_text_duration_microseconds(effective_subtitle_end, narration_duration, total_duration),
                },
                "role": "copy",
            }
        )

    cues = list(narration.subtitle_cues or []) if narration else []
    max_subtitle_end = effective_subtitle_end
    for row in cues:
        content_text = str(row.get("text") or "").strip()
        if not content_text:
            continue
        try:
            start_seconds = max(0.0, float(row.get("start_seconds") or 0))
            end_seconds = max(start_seconds, float(row.get("end_seconds") or 0))
        except (TypeError, ValueError):
            continue
        start = _microseconds(start_seconds)
        end = _microseconds(end_seconds)
        if max_subtitle_end > 0:
            if start >= max_subtitle_end:
                continue
            end = min(end, max_subtitle_end)
        duration = end - start
        if duration <= 0:
            continue
        material_id, material = _text_material(content_text)
        text_materials.append(material)
        subtitle_text_segments.append(
            {
                "id": _material_id(),
                "material_id": material_id,
                "target_timerange": {"start": start, "duration": duration},
                "role": "subtitle",
            }
        )

    audio_materials: list[dict[str, Any]] = []
    audio_tracks: list[dict[str, Any]] = []
    for role, path, duration, volume in (
        ("narration", Path(narration.audio_path) if narration else None, narration_duration, 1.0),
        ("music", Path(music.file_path) if music else None, music_duration, 0.35),
    ):
        if path is None or not path.is_file() or duration <= 0:
            continue
        material_id = _material_id()
        local_path = _copy_audio_to_draft(path, draft_root, role)
        audio_materials.append(_audio_material(material_id, local_path, duration, role))
        segment = _audio_segment(material_id, duration, volume, len(audio_tracks))
        segment["role"] = role
        audio_tracks.append(segment)

    now = int(time.time())
    materials = _empty_materials()
    materials["audios"] = audio_materials
    materials["texts"] = text_materials
    tracks = [
        _track("video", []),
        _track("audio", audio_tracks),
    ]
    if copy_text_segments:
        tracks.append(
            _track("text", [
                _text_segment(item["material_id"], item["target_timerange"]["start"], item["target_timerange"]["duration"], item["role"], index)
                for index, item in enumerate(copy_text_segments)
            ])
        )
    if subtitle_text_segments:
        tracks.append(
            _track("text", [
                _text_segment(item["material_id"], item["target_timerange"]["start"], item["target_timerange"]["duration"], item["role"], index)
                for index, item in enumerate(subtitle_text_segments)
            ])
        )

    content = {
        "id": draft.id,
        "name": draft.name,
        "create_time": now,
        "update_time": now,
        "canvas_config": {"ratio": "9:16", "width": 1080, "height": 1920},
        "duration": total_duration,
        "fps": 30,
        "platform": {"app_source": "lv", "app_version": "6.0.0", "os": "windows"},
        "last_modified_platform": {"app_source": "lv", "app_version": "6.0.0", "os": "windows"},
        "materials": materials,
        "tracks": tracks,
        "extra_info": None,
        "free_render_index_mode_on": False,
        "new_version": "6.0.0",
        "render_index_track_mode_on": True,
        "version": 360000,
    }
    meta = _sidecar_meta(
        draft.id,
        draft.name,
        draft_root,
        destination,
        total_duration,
        len(audio_materials) + len(text_materials),
    )
    (draft_root / "draft_content.json").write_text(
        json.dumps(content, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
    (draft_root / "draft_info.json").write_text(
        json.dumps(content, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
    (draft_root / "draft_meta_info.json").write_text(
        json.dumps(meta, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
    (draft_root / "README.txt").write_text(
        "本草稿不包含视频片段。为兼容剪映时间线，草稿保留空视频轨道；请在剪映专业版打开后自行添加、裁剪和排列视频。文案、字幕、旁白和背景音乐已按选择写入草稿。\n",
        encoding="utf-8",
    )
    (draft_root / "draft_agency_config.json").write_text(
        json.dumps({"common": {}, "materials": []}, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    (draft_root / "draft_biz_config.json").write_text("", encoding="utf-8")
    (draft_root / "draft_settings").write_text(
        json.dumps({"canvas_config": content["canvas_config"], "fps": 30}, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    (draft_root / "performance_opt_info.json").write_text(
        json.dumps({"performance_level": 0}, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    (draft_root / "timeline_layout.json").write_text(
        json.dumps({"scale": 1.0, "scroll_offset": 0}, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    draft.snapshot = {
        "copy": {"id": copy.id, "text": copy.content_text.strip()} if copy else None,
        "narration": {
            "id": narration.id,
            "text": narration.approved_text.strip(),
            "audio_path": narration.audio_path,
            "cues": cues,
        } if narration else None,
        "music": {"id": music.id, "name": music.name, "path": music.file_path} if music else None,
        "destination_dir": str(destination),
        "duration_microseconds": total_duration,
        "duration_source": "timed_materials" if timed_duration else "copy_only_default",
        "duplicate_usage_count_before_create": duplicate_usage_count,
    }
    draft.status = "ready"
    draft.draft_path = str(draft_root)
    _record_jianying_draft_generation(
        session,
        copy_content_id=draft.copy_content_id,
        narration_asset_id=draft.narration_asset_id,
        music_resource_id=draft.music_resource_id,
        generated_count=generated_usage_count + 1,
    )
    session.flush()
    return draft
