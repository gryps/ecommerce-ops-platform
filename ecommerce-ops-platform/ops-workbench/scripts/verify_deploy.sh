#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
project_root="${PVA_PROJECT_ROOT:-$(cd . && pwd)/..}"
venv_dir="${PVA_VENV_DIR:-$project_root/.venv}"
platform_url="${PVA_PLATFORM_HEALTH_URL:-http://127.0.0.1:8000/api/health}"
comfyui_url="${PVA_COMFYUI_STATS_URL:-http://127.0.0.1:8188/system_stats}"

printf '== services ==\n'
systemctl --user is-active product-video-automation
systemctl --user is-active comfyui

printf '\n== python import ==\n'
"$venv_dir/bin/python" - <<'VERIFY_IMPORT_PY'
import importlib
for name in ["fastapi", "sqlalchemy", "alembic", "httpx"]:
    importlib.import_module(name)
    print(f"{name}: ok")
VERIFY_IMPORT_PY

printf '\n== database ==\n'
"$venv_dir/bin/python" - <<'VERIFY_DB_PY'
from app.core.database import database_url, get_engine
from sqlalchemy import text
print(database_url())
with get_engine().connect() as conn:
    try:
        version = conn.execute(text("select version_num from alembic_version")).scalar()
    except Exception as exc:
        version = f"unavailable: {exc}"
print(f"alembic_version: {version}")
VERIFY_DB_PY

printf '\n== frontend static ==\n'
test -f "../ops-workbench-runtime/static-workbench/index.html"
find "../ops-workbench-runtime/static-workbench/assets" -maxdepth 1 -type f | sed -n '1,5p'

printf '\n== platform health ==\n'
curl -sS --max-time 5 "$platform_url"
printf '\n'

printf '\n== comfyui health ==\n'
curl -sS --max-time 5 "$comfyui_url" | head -c 500
printf '\n'
