#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

PYTHON_BIN=".venv/bin/python"
UVICORN_BIN=".venv/bin/uvicorn"
if [ ! -x "$PYTHON_BIN" ] || [ ! -x "$UVICORN_BIN" ]; then
  echo "虚拟环境不完整，正在重建 .venv..."
  python3 -m venv .venv
fi

"$PYTHON_BIN" -m pip install -r requirements-dev.txt
"$UVICORN_BIN" app.main:app --host 127.0.0.1 --port 8000 --reload
