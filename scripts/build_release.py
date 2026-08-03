#!/usr/bin/env python3
from __future__ import annotations

import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INCLUDE_PATHS = [
    "app",
    "deploy",
    "migrations",
    "scripts",
    "static-workbench",
    "tests",
    "docs",
    "storage/workspace/.gitkeep",
    "README.md",
    "PROJECT_CURRENT.md",
    "PROJECT_DECISIONS.md",
    "NEXT_TASK.md",
    "NEW_SESSION_PROMPT.md",
    "PROJECT_HANDOFF_ARCHIVE.md",
    "requirements.txt",
    "requirements-dev.txt",
    "alembic.ini",
    "pytest.ini",
    ".env.example",
    ".gitignore",
]
EXCLUDED_PARTS = {"__pycache__", ".pytest_cache", ".venv", "dist"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo"}


def should_include(path: Path) -> bool:
    relative = path.relative_to(ROOT)
    if any(part in EXCLUDED_PARTS for part in relative.parts):
        return False
    return path.suffix not in EXCLUDED_SUFFIXES


def iter_release_files() -> list[Path]:
    files: list[Path] = []
    for item in INCLUDE_PATHS:
        path = ROOT / item
        if path.is_file():
            if should_include(path):
                files.append(path)
        elif path.is_dir():
            files.extend(candidate for candidate in path.rglob("*") if candidate.is_file() and should_include(candidate))
        else:
            raise FileNotFoundError(f"Missing release path: {item}")
    return sorted(files, key=lambda value: value.relative_to(ROOT).as_posix())


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: build_release.py <output.zip>", file=sys.stderr)
        return 2
    output_path = Path(sys.argv[1])
    if not output_path.is_absolute():
        output_path = ROOT / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in iter_release_files():
            archive.write(path, path.relative_to(ROOT).as_posix())
    try:
        display_path = output_path.relative_to(ROOT).as_posix()
    except ValueError:
        display_path = output_path.as_posix()
    print(display_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
