#!/usr/bin/env bash
set -euo pipefail

if [[ ${EUID} -eq 0 ]]; then
    echo "ERROR: ejecute este script como usuario normal, no con sudo." >&2
    exit 1
fi

conda_env="${1:-yolo}"
mcu_variant="${2:-nano_esp32}"

case "${mcu_variant}" in
    nano_esp32|nano_33_ble)
        ;;
    *)
        echo "ERROR: variante de Host MCU no válida: ${mcu_variant}" >&2
        echo "Variantes soportadas: nano_esp32, nano_33_ble" >&2
        echo "Uso: $0 [ENTORNO_CONDA] [nano_esp32|nano_33_ble]" >&2
        exit 2
        ;;
esac

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/../.." && pwd)"

node_script="${repo_root}/src/update_manager/${mcu_variant}/node.py"
working_dir="$(dirname "${node_script}")"

command -v conda >/dev/null 2>&1 || {
    echo "ERROR: conda no está en PATH." >&2
    exit 1
}

conda_base="$(conda info --base)"
conda_exe="${conda_base}/condabin/conda"

if [[ ! -x "${conda_exe}" ]]; then
    echo "ERROR: no se encontró el ejecutable de Conda: ${conda_exe}" >&2
    exit 1
fi

if [[ ! -f "${node_script}" ]]; then
    echo "ERROR: no se encontró el gestor de actualizaciones:" >&2
    echo "       ${node_script}" >&2
    exit 1
fi

echo "=============================================="
echo " PINV01-27 - Instalación del servicio systemd"
echo "=============================================="
echo "[info] Entorno Conda : ${conda_env}"
echo "[info] Host MCU      : ${mcu_variant}"
echo "[info] node.py       : ${node_script}"
echo "[info] Working dir   : ${working_dir}"

echo "[1/4] Verificando dependencias Python base..."
conda run -n "${conda_env}" python -c \
    "import serial, psutil; print('Dependencias base OK')"

echo "[2/4] Generando servicio systemd..."
service_tmp="$(mktemp)"
trap 'rm -f "${service_tmp}"' EXIT

cat > "${service_tmp}" <<SERVICE
[Unit]
Description=PINV01-27 Autonomous Node (${mcu_variant})
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${USER}
WorkingDirectory=${working_dir}
Environment=PYTHONUNBUFFERED=1
EnvironmentFile=-/etc/default/pinv0127
ExecStart=/bin/bash -lc '${conda_exe} run -n ${conda_env} --no-capture-output python -u ${node_script}'
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SERVICE

sudo install -m 0644 "${service_tmp}" /etc/systemd/system/pinv0127.service

echo "[3/4] Preparando archivo de variables privadas..."
if [[ ! -f /etc/default/pinv0127 ]]; then
    sudo install -m 0600 \
        "${repo_root}/systemd/pinv0127.env.example" \
        /etc/default/pinv0127

    echo "[info] Se creó /etc/default/pinv0127."
    echo "[info] Edítelo para configurar cámara y modelo."
else
    echo "[info] /etc/default/pinv0127 ya existe; no se reemplazará."
fi

echo "[4/4] Habilitando e iniciando el servicio..."
sudo systemctl daemon-reload
sudo systemctl enable --now pinv0127.service

echo
echo "[ok] Servicio instalado."
echo "[ok] Variante MCU: ${mcu_variant}"
echo "[ok] Gestor: ${node_script}"
echo
sudo systemctl --no-pager --full status pinv0127.service || true
