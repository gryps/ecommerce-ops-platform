#!/usr/bin/env python3
from __future__ import annotations

import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = ROOT.parent / "ops-workbench-runtime"
INCLUDE_PATHS = [
    (ROOT / "app", "app"),
    (ROOT / "deploy", "deploy"),
    (ROOT / "migrations", "migrations"),
    (ROOT / "scripts", "scripts"),
    (RUNTIME_ROOT / "static-workbench", "static-workbench"),
    (ROOT / "tests", "tests"),
    (ROOT / "README.md", "README.md"),
    (ROOT / "requirements.txt", "requirements.txt"),
    (ROOT / "requirements-dev.txt", "requirements-dev.txt"),
    (ROOT / "alembic.ini", "alembic.ini"),
    (ROOT / "pytest.ini", "pytest.ini"),
    (ROOT / ".env.example", ".env.example"),
]
EXCLUDED_PARTS = {"__pycache__", ".pytest_cache", ".venv", "dist"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo"}


def should_include(path: Path) -> bool:
    if any(part in EXCLUDED_PARTS for part in path.parts):
        return False
    return path.suffix not in EXCLUDED_SUFFIXES


def iter_release_files() -> list[tuple[Path, str]]:
    files: list[tuple[Path, str]] = []
    for source, archive_root in INCLUDE_PATHS:
        path = source
        if path.is_file():
            if should_include(path):
                files.append((path, archive_root))
        elif path.is_dir():
            files.extend(
                (candidate, str(Path(archive_root) / candidate.relative_to(path)))
                for candidate in path.rglob("*")
                if candidate.is_file() and should_include(candidate)
            )
        else:
            raise FileNotFoundError(f"Missing release path: {path}")
    return sorted(files, key=lambda value: value[1])


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: build_release.py <output.zip>", file=sys.stderr)
        return 2
    output_path = Path(sys.argv[1])
    if not output_path.is_absolute():
        output_path = ROOT / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path, archive_name in iter_release_files():
            archive.write(path, archive_name)
    try:
        display_path = output_path.relative_to(ROOT).as_posix()
    except ValueError:
        display_path = output_path.as_posix()
    print(display_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
