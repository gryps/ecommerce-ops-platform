from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


CATALOG_MODEL = "qwen-audio-3.0-tts-plus"
CATALOG_PATH = Path(__file__).resolve().parents[1] / "data" / "qwen_audio_3_tts_plus_voices.json"


@lru_cache(maxsize=1)
def load_voice_catalog() -> dict[str, Any]:
    payload = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    items = list(payload.get("items") or [])
    if payload.get("model") != CATALOG_MODEL or payload.get("count") != len(items):
        raise RuntimeError("音色目录文件无效")
    return payload


def voice_catalog_item(sequence: int) -> dict[str, Any] | None:
    items = load_voice_catalog()["items"]
    if sequence < 1 or sequence > len(items):
        return None
    item = items[sequence - 1]
    return dict(item) if item.get("sequence") == sequence else next((dict(row) for row in items if row.get("sequence") == sequence), None)


def voice_catalog_page(
    *,
    page: int = 1,
    page_size: int = 20,
    query: str = "",
    gender: str = "",
    age: str = "",
    scenario: str = "",
) -> dict[str, Any]:
    payload = load_voice_catalog()
    items = list(payload["items"])
    needle = query.strip().casefold()
    if needle:
        fields = (
            "sequence", "name", "voice", "gender", "age", "trait",
            "scenario", "language", "preview_filename",
        )
        items = [item for item in items if any(needle in str(item.get(field) or "").casefold() for field in fields)]
    if gender.strip():
        items = [item for item in items if item.get("gender") == gender.strip()]
    if age.strip():
        items = [item for item in items if str(item.get("age") or "") == age.strip()]
    if scenario.strip():
        items = [item for item in items if item.get("scenario") == scenario.strip()]
    size = max(1, min(page_size, 50))
    current = max(1, page)
    start = (current - 1) * size
    return {
        "model": payload["model"], "source": payload["source"], "total": len(items),
        "page": current, "page_size": size, "items": [dict(item) for item in items[start:start + size]],
        "genders": [value for value in ("女", "男") if any(item.get("gender") == value for item in payload["items"])],
        "ages": sorted(
            {str(item.get("age") or "") for item in payload["items"] if str(item.get("age") or "").isdigit()},
            key=int,
        ),
        "scenarios": sorted({str(item.get("scenario") or "") for item in payload["items"] if item.get("scenario")}),
    }
