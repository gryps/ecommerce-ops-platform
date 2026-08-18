#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

ops_workbench_dir="$(pwd)"
project_root="${PVA_PROJECT_ROOT:-$(cd "$ops_workbench_dir/.." && pwd)}"
runtime_dir="${PVA_RUNTIME_DIR:-$project_root/ops-workbench-runtime}"
venv_dir="${PVA_VENV_DIR:-$project_root/.venv}"
host="${PVA_SERVICE_HOST:-0.0.0.0}"
port="${PVA_SERVICE_PORT:-8000}"
unit_dir="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
service_name="product-video-automation.service"
unit_source="$ops_workbench_dir/deploy/$service_name"
unit_target="$unit_dir/$service_name"

if [ ! -x "$venv_dir/bin/python" ]; then
  echo "Missing $venv_dir/bin/python. Create the runtime venv first." >&2
  exit 1
fi
if [ ! -f "$unit_source" ]; then
  echo "Missing systemd unit template: $unit_source" >&2
  exit 1
fi

install -d -m 0755 "$unit_dir"
python3 - "$unit_source" "$unit_target" "$ops_workbench_dir" "$runtime_dir" "$venv_dir" "$host" "$port" <<'UNIT_RENDER_PY'
from pathlib import Path
import sys
source, target, ops_dir, runtime_dir, venv_dir, host, port = sys.argv[1:]
text = Path(source).read_text(encoding="utf-8")
replacements = {
    "@OPS_WORKBENCH_DIR@": ops_dir,
    "@RUNTIME_DIR@": runtime_dir,
    "@VENV_DIR@": venv_dir,
    "@HOST@": host,
    "@PORT@": port,
}
for key, value in replacements.items():
    text = text.replace(key, value)
Path(target).write_text(text, encoding="utf-8")
UNIT_RENDER_PY
chmod 0644 "$unit_target"

systemctl --user daemon-reload
systemctl --user enable --now "$service_name"
systemctl --user --no-pager --full status "$service_name"

if command -v loginctl >/dev/null 2>&1; then
  linger_state="$(loginctl show-user "$USER" -p Linger --value 2>/dev/null || true)"
  if [ "$linger_state" != "yes" ]; then
    echo "Warning: user lingering is disabled. Run: sudo loginctl enable-linger $USER" >&2
  fi
fi
