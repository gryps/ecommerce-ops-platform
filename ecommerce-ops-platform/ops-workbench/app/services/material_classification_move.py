from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.media import VIDEO_EXTENSIONS, probe_video
from app.domain.models import (
    MediaAsset,
    MediaAssetTag,
    Product,
    ShotTag,
)


INVALID_FILENAME = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


@dataclass(frozen=True)
class ClassificationItem:
    source_path: str
    tag_ids: list[str]


def safe_filename_part(value: str, *, fallback: str) -> str:
    clean = INVALID_FILENAME.sub("-", value).strip(" .-")
    clean = re.sub(r"\s+", " ", clean)
    return (clean or fallback)[:80]


def _available_destination(folder: Path, stem: str, suffix: str, reserved: set[Path]) -> Path:
    candidate = folder / f"{stem}{suffix}"
    sequence = 2
    while candidate.exists() or candidate in reserved:
        candidate = folder / f"{stem}-{sequence}{suffix}"
        sequence += 1
    return candidate


def classify_and_move_originals(
    session: Session,
    *,
    product_id: int,
    source_dir: str,
    items: list[ClassificationItem],
) -> list[MediaAsset]:
    product = session.get(Product, product_id)
    if product is None or product.status != "active":
        raise ValueError("产品不存在或已停用")
    if not items:
        raise ValueError("至少选择一个待归类视频")

    root = Path(source_dir).expanduser().resolve()
    if not root.is_dir():
        raise ValueError("素材目录不存在或不可访问")
    product_part = safe_filename_part(product.name, fallback=f"产品-{product.id}")
    product_folder = root if root.name.casefold() == product_part.casefold() else root / product_part

    requested_tag_ids = {tag_id for item in items for tag_id in item.tag_ids}
    if not requested_tag_ids:
        raise ValueError("每条视频至少选择一个标签")
    tags = session.scalars(
        select(ShotTag).where(ShotTag.id.in_(requested_tag_ids))
    ).all()
    tags_by_id = {tag.id: tag for tag in tags}
    if set(tags_by_id) != requested_tag_ids:
        raise ValueError("部分标签不存在或已停用")

    planned: list[tuple[Path, Path, list[ShotTag], dict]] = []
    reserved: set[Path] = set()
    seen_sources: set[str] = set()
    for item in items:
        source = Path(item.source_path).expanduser().resolve()
        normalized = str(source).casefold()
        if normalized in seen_sources:
            raise ValueError(f"视频重复选择：{source.name}")
        seen_sources.add(normalized)
        if source.parent != root and root not in source.parents:
            raise ValueError(f"视频不在当前素材目录内：{source.name}")
        if not source.is_file() or source.suffix.casefold() not in VIDEO_EXTENSIONS:
            raise ValueError(f"视频不存在或格式不受支持：{source.name}")
        item_tags = [tags_by_id[tag_id] for tag_id in dict.fromkeys(item.tag_ids)]
        if not item_tags:
            raise ValueError(f"视频未选择标签：{source.name}")
        seen_categories: set[str] = set()
        duplicate_category = None
        for tag in item_tags:
            if tag.category_id in seen_categories:
                duplicate_category = tag.category_id
                break
            seen_categories.add(tag.category_id)
        if duplicate_category is not None:
            raise ValueError(
                f"视频在同一标签分类下只能选择一个标签名称：{source.name}（{duplicate_category}）"
            )
        metadata = probe_video(source)
        tag_part = "-".join(safe_filename_part(tag.name, fallback="标签") for tag in item_tags)
        destination = _available_destination(
            product_folder, f"{product_part}-{tag_part}", source.suffix.casefold(), reserved
        )
        reserved.add(destination)
        planned.append((source, destination, item_tags, metadata))

    product_folder.mkdir(parents=True, exist_ok=True)
    moved: list[tuple[Path, Path]] = []
    try:
        for source, destination, _tags, _metadata in planned:
            shutil.move(str(source), str(destination))
            moved.append((source, destination))
    except Exception as exc:
        for original, destination in reversed(moved):
            if destination.exists() and not original.exists():
                shutil.move(str(destination), str(original))
        raise RuntimeError(f"移动原视频失败，已回退已移动文件：{exc}") from exc

    assets: list[MediaAsset] = []
    try:
        for source, destination, item_tags, metadata in planned:
            asset = MediaAsset(
                product_id=product.id,
                filename=destination.name,
                source_path=str(destination),
                original_source_path=str(source),
                duration_seconds=float(metadata.get("duration_seconds") or 0),
                width=int(metadata.get("width") or 0),
                height=int(metadata.get("height") or 0),
                status="classified",
            )
            session.add(asset)
            session.flush()
            session.add_all(
                [MediaAssetTag(asset_id=asset.id, tag_id=tag.id) for tag in item_tags]
            )
            assets.append(asset)
        session.flush()
    except Exception:
        for original, destination in reversed(moved):
            if destination.exists() and not original.exists():
                shutil.move(str(destination), str(original))
        raise
    return assets
