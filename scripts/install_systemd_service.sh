#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

unit_dir="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
service_names=(
  "product-video-automation.service"
)

if [ ! -x ".venv/bin/python" ]; then
  echo "Missing .venv/bin/python. Run scripts/run_dev.sh once to create the environment." >&2
  exit 1
fi

install -d -m 0755 "$unit_dir"
for service_name in "${service_names[@]}"; do
  unit_source="$PWD/deploy/$service_name"
  unit_target="$unit_dir/$service_name"
  if [ ! -f "$unit_source" ]; then
    echo "Missing systemd unit: $unit_source" >&2
    exit 1
  fi
  install -m 0644 "$unit_source" "$unit_target"
done
systemctl --user daemon-reload
systemctl --user enable --now "${service_names[@]}"
for service_name in "${service_names[@]}"; do
  systemctl --user --no-pager --full status "$service_name"
done

if command -v loginctl >/dev/null 2>&1; then
  linger_state="$(loginctl show-user "$USER" -p Linger --value 2>/dev/null || true)"
  if [ "$linger_state" != "yes" ]; then
    echo "Warning: user lingering is disabled. Run: sudo loginctl enable-linger $USER" >&2
  fi
fi
