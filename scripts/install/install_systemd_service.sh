#!/usr/bin/env bash
set -euo pipefail
[[ ${EUID} -ne 0 ]] || { echo "Ejecute como usuario normal, no con sudo." >&2; exit 1; }
conda_env="${1:-yolo}"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/../.." && pwd)"
node_script="$repo_root/src/update_manager/node.py"
working_dir="$(dirname "$node_script")"
command -v conda >/dev/null || { echo "ERROR: conda no está en PATH" >&2; exit 1; }
conda_base="$(conda info --base)"
conda_exe="$conda_base/condabin/conda"
[[ -x "$conda_exe" && -f "$node_script" ]] || { echo "ERROR: rutas inválidas" >&2; exit 1; }
conda run -n "$conda_env" python -c "import serial, psutil; print('Dependencias base OK')"
service_tmp="$(mktemp)"; trap 'rm -f "$service_tmp"' EXIT
cat > "$service_tmp" <<SERVICE
[Unit]
Description=PINV01-27 Autonomous Node
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$working_dir
Environment=PYTHONUNBUFFERED=1
EnvironmentFile=-/etc/default/pinv0127
ExecStart=/bin/bash -lc '$conda_exe run -n $conda_env --no-capture-output python -u $node_script'
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SERVICE
sudo install -m 0644 "$service_tmp" /etc/systemd/system/pinv0127.service
if [[ ! -f /etc/default/pinv0127 ]]; then
  sudo install -m 0600 "$repo_root/systemd/pinv0127.env.example" /etc/default/pinv0127
  echo "Se creó /etc/default/pinv0127. Edítelo para configurar cámara y modelo."
fi
sudo systemctl daemon-reload
sudo systemctl enable --now pinv0127.service
sudo systemctl --no-pager --full status pinv0127.service || true
