#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

version="${1:-$(date +%Y%m%d-%H%M%S)}"
package_dir="../ops-workbench-runtime/releases"
package_name="product-video-automation-${version}.zip"

mkdir -p "$package_dir"

python3 scripts/build_release.py "$package_dir/$package_name"
