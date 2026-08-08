#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

VENV_DIR="${PVA_VENV_DIR:-../../.venv}"
PYTHON_BIN="$VENV_DIR/bin/python"
UVICORN_BIN="$VENV_DIR/bin/uvicorn"

if [ ! -d "$VENV_DIR" ]; then
  python3 -m venv "$VENV_DIR"
fi

if [ ! -x "$PYTHON_BIN" ] || [ ! -x "$UVICORN_BIN" ]; then
  echo "虚拟环境不完整，正在重建 $VENV_DIR..."
  python3 -m venv "$VENV_DIR"
fi

export PYTHONDONTWRITEBYTECODE=1
"$PYTHON_BIN" -m pip install -r requirements-dev.txt
"$UVICORN_BIN" app.main:app --host 127.0.0.1 --port 8000 --reload
