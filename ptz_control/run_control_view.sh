#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[ -f "$HERE/camera_env.sh" ] || { echo "[ERROR] Falta camera_env.sh. Copia camera_env.example.sh y edítalo."; exit 1; }
source "$HERE/camera_env.sh"
exec conda run --no-capture-output -n onvif python "${HERE}/ptz_control_view.py"
