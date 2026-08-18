#!/usr/bin/env python3
from __future__ import annotations

import json
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OPS = ROOT / "ops-workbench"
RUNTIME = ROOT / "ops-workbench-runtime"
OUTPUT = RUNTIME / "DEPLOY_MANIFEST.json"


def run(command: list[str], cwd: Path = ROOT) -> str:
    try:
        return subprocess.check_output(command, cwd=cwd, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return ""


def main() -> int:
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "project_root": str(ROOT),
        "ops_workbench": str(OPS),
        "runtime": str(RUNTIME),
        "version": (ROOT / "VERSION").read_text(encoding="utf-8").strip() if (ROOT / "VERSION").exists() else "unknown",
        "git_commit": run(["git", "rev-parse", "HEAD"]),
        "git_branch": run(["git", "branch", "--show-current"]),
        "git_dirty": bool(run(["git", "status", "--short"])),
        "python": platform.python_version(),
        "node": run(["node", "--version"]),
        "npm": run(["npm", "--version"]),
        "services": {
            "product-video-automation": run(["systemctl", "--user", "is-active", "product-video-automation"]),
            "comfyui": run(["systemctl", "--user", "is-active", "comfyui"]),
        },
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(OUTPUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
