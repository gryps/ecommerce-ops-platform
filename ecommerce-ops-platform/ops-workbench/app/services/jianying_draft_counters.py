from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.models import JianyingDraft, WorkbenchSetting

DUPLICATE_COUNTER_COUNTS_KEY = "jianying_draft_duplicate_counter_counts"
DUPLICATE_COUNTER_RESETS_KEY = "jianying_draft_duplicate_counter_resets"


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
