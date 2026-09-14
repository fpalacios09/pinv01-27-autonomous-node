#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# PINV01-27
# Instalador del servicio de conteo manual
# ============================================================

SERVICE_NAME="pinv0127-manual-count.service"
SERVICE_PATH="/etc/systemd/system/${SERVICE_NAME}"

# Servicio principal utilizado por el gestor/IPFS
MAIN_SERVICE="pinv0127.service"

# Entorno Conda por defecto
CONDA_ENV="${1:-yolo}"

# ============================================================
# NO EJECUTAR DIRECTAMENTE COMO ROOT
# ============================================================

if [[ ${EUID} -eq 0 ]]; then
    echo "ERROR: ejecute este script como usuario normal."
    echo
    echo "Uso:"
    echo "  bash $0"
    echo
    echo "o:"
    echo "  bash $0 NOMBRE_ENTORNO_CONDA"
    exit 1
fi

# ============================================================
# RUTAS
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COUNT_SCRIPT="${SCRIPT_DIR}/script.py"

echo "============================================================"
echo " PINV01-27 - Activación manual del conteo"
echo "============================================================"
echo
echo "[info] Carpeta:"
echo "       ${SCRIPT_DIR}"
echo
echo "[info] Entorno Conda:"
echo "       ${CONDA_ENV}"
echo

# ============================================================
# 1. VERIFICAR script.py
# ============================================================

if [[ ! -f "${COUNT_SCRIPT}" ]]; then
    echo "ERROR:"
    echo "No se encontró:"
    echo
    echo "  ${COUNT_SCRIPT}"
    echo
    echo "Debe existir un archivo llamado exactamente:"
    echo
    echo "  script.py"
    echo
    echo "dentro de esta misma carpeta."
    exit 1
fi

echo "[ok] script.py encontrado."

# ============================================================
# 2. VERIFICAR PESOS .pt
# ============================================================

mapfile -d '' PT_FILES < <(
    find "${SCRIPT_DIR}" \
        -maxdepth 1 \
        -type f \
        -name '*.pt' \
        -print0
)

if (( ${#PT_FILES[@]} == 0 )); then
    echo
    echo "ERROR:"
    echo "No se encontró ningún archivo de pesos *.pt en:"
    echo
    echo "  ${SCRIPT_DIR}"
    echo
    echo "Copie los pesos YOLO dentro de esta carpeta."
    exit 1
fi

echo
echo "[ok] Pesos encontrados:"

for pt in "${PT_FILES[@]}"; do
    echo "     - $(basename "${pt}")"
done

# ============================================================
# 3. VERIFICAR SINTAXIS DE script.py
# ============================================================

echo
echo "[info] Verificando sintaxis de script.py..."

python3 -m py_compile "${COUNT_SCRIPT}" || {
    echo
    echo "ERROR: script.py contiene errores de sintaxis."
    exit 1
}

echo "[ok] Sintaxis correcta."

# ============================================================
# 4. VERIFICAR CONDA
# ============================================================

echo
echo "[info] Buscando Conda..."

if ! command -v conda >/dev/null 2>&1; then
    echo
    echo "ERROR: conda no está disponible en PATH."
    echo
    echo "Compruebe la instalación de Miniconda/Conda."
    exit 1
fi

CONDA_BASE="$(conda info --base)"
CONDA_EXE="${CONDA_BASE}/condabin/conda"

if [[ ! -x "${CONDA_EXE}" ]]; then
    echo
    echo "ERROR:"
    echo "No se encontró:"
    echo
    echo "  ${CONDA_EXE}"
    exit 1
fi

echo "[ok] Conda:"
echo "     ${CONDA_EXE}"

# ============================================================
# 5. VERIFICAR ENTORNO CONDA
# ============================================================

echo
echo "[info] Verificando entorno Conda '${CONDA_ENV}'..."

if ! "${CONDA_EXE}" run \
        -n "${CONDA_ENV}" \
        python -c "import sys; print(sys.executable)" \
        >/dev/null 2>&1
then
    echo
    echo "ERROR:"
    echo "No se pudo ejecutar el entorno Conda:"
    echo
    echo "  ${CONDA_ENV}"
    exit 1
fi

echo "[ok] Entorno Conda disponible."

# ============================================================
# 6. VERIFICAR DEPENDENCIAS PRINCIPALES
# ============================================================

echo
echo "[info] Verificando dependencias principales..."

"${CONDA_EXE}" run \
    -n "${CONDA_ENV}" \
    python -c "
import cv2
import torch
import serial
from ultralytics import YOLO
print('Dependencias principales OK')
" || {
    echo
    echo "ERROR:"
    echo "Faltan dependencias Python en el entorno:"
    echo
    echo "  ${CONDA_ENV}"
    exit 1
}

# ============================================================
# 7. EVITAR CONFLICTO CON SERVICIO PRINCIPAL
# ============================================================

if systemctl cat "${MAIN_SERVICE}" >/dev/null 2>&1; then

    MAIN_ACTIVE="$(
        systemctl is-active "${MAIN_SERVICE}" 2>/dev/null || true
    )"

    MAIN_ENABLED="$(
        systemctl is-enabled "${MAIN_SERVICE}" 2>/dev/null || true
    )"

    if [[ "${MAIN_ACTIVE}" == "active" ||
          "${MAIN_ENABLED}" == "enabled" ]]; then

        echo
        echo "============================================================"
        echo " ADVERTENCIA"
        echo "============================================================"
        echo
        echo "El servicio principal/IPFS:"
        echo
        echo "  ${MAIN_SERVICE}"
        echo
        echo "está activo o habilitado."
        echo
        echo "No debe ejecutarse simultáneamente con el conteo manual"
        echo "porque ambos procesos podrían intentar utilizar /dev/mcu."
        echo

        read -r -p \
        "¿Detener y deshabilitar ${MAIN_SERVICE}? [s/N]: " answer

        case "${answer}" in
            s|S|si|SI|sí|Sí)

                echo
                echo "[info] Deteniendo servicio principal..."

                sudo systemctl disable --now "${MAIN_SERVICE}"

                echo
                echo "[ok] ${MAIN_SERVICE} detenido y deshabilitado."
                ;;

            *)
                echo
                echo "Operación cancelada."
                exit 1
                ;;
        esac
    fi
fi

# ============================================================
# 8. CREAR SERVICIO
# ============================================================

echo
echo "[info] Generando servicio systemd..."

SERVICE_TMP="$(mktemp)"
trap 'rm -f "${SERVICE_TMP}"' EXIT

cat > "${SERVICE_TMP}" <<SERVICE
[Unit]
Description=PINV01-27 Manual Vehicle Counting
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${USER}
WorkingDirectory=${SCRIPT_DIR}
Environment=PYTHONUNBUFFERED=1
ExecStart=${CONDA_EXE} run -n ${CONDA_ENV} --no-capture-output python -u ${COUNT_SCRIPT}
Restart=always
RestartSec=5
TimeoutStopSec=20
KillSignal=SIGTERM
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SERVICE

sudo install \
    -m 0644 \
    "${SERVICE_TMP}" \
    "${SERVICE_PATH}"

echo "[ok] Servicio creado:"
echo
echo "     ${SERVICE_PATH}"

# ============================================================
# 9. RECARGAR SYSTEMD
# ============================================================

echo
echo "[info] Recargando systemd..."
sudo systemctl daemon-reload

# ============================================================
# 10. HABILITAR + INICIAR
# ============================================================

echo
echo "[info] Habilitando servicio..."
sudo systemctl enable "${SERVICE_NAME}"

echo
echo "[info] Iniciando servicio..."
sudo systemctl restart "${SERVICE_NAME}"

sleep 3

# ============================================================
# 11. MOSTRAR ESTADO
# ============================================================

echo
echo "============================================================"
echo " ESTADO DEL SERVICIO"
echo "============================================================"
echo

sudo systemctl \
    --no-pager \
    --full \
    status "${SERVICE_NAME}" || true

echo
echo "============================================================"
echo " INSTALACIÓN FINALIZADA"
echo "============================================================"
echo
echo "Servicio:"
echo
echo "  ${SERVICE_NAME}"
echo
echo "script.py:"
echo
echo "  ${COUNT_SCRIPT}"
echo
echo "WorkingDirectory:"
echo
echo "  ${SCRIPT_DIR}"
echo
echo "Comandos útiles:"
echo
echo "  sudo systemctl status ${SERVICE_NAME}"
echo
echo "  sudo systemctl restart ${SERVICE_NAME}"
echo
echo "  sudo systemctl stop ${SERVICE_NAME}"
echo
echo "  journalctl -u ${SERVICE_NAME} -f"
echo
echo "Para cambiar el algoritmo:"
echo
echo "  1. Reemplace script.py y/o los pesos."
echo "  2. Ejecute:"
echo
echo "     sudo systemctl restart ${SERVICE_NAME}"
echo
