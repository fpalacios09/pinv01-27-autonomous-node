#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# PINV01-27
# Eliminación del servicio de conteo manual
# ============================================================

SERVICE_NAME="pinv0127-manual-count.service"
SERVICE_PATH="/etc/systemd/system/${SERVICE_NAME}"
MAIN_SERVICE="pinv0127.service"

echo "============================================================"
echo " PINV01-27 - Eliminación del servicio de conteo manual"
echo "============================================================"
echo

# ============================================================
# VERIFICAR SI EXISTE
# ============================================================

if [[ ! -f "${SERVICE_PATH}" ]]; then
    echo "[info] El servicio manual no está instalado:"
    echo
    echo "       ${SERVICE_PATH}"
else

    # ========================================================
    # DETENER
    # ========================================================

    echo "[info] Deteniendo ${SERVICE_NAME}..."
    sudo systemctl stop "${SERVICE_NAME}" 2>/dev/null || true

    # ========================================================
    # DESHABILITAR
    # ========================================================

    echo "[info] Deshabilitando ${SERVICE_NAME}..."
    sudo systemctl disable "${SERVICE_NAME}" 2>/dev/null || true

    # ========================================================
    # ELIMINAR ARCHIVO
    # ========================================================

    echo "[info] Eliminando:"
    echo
    echo "       ${SERVICE_PATH}"

    sudo rm -f "${SERVICE_PATH}"

    # ========================================================
    # RECARGAR SYSTEMD
    # ========================================================

    sudo systemctl daemon-reload
    sudo systemctl reset-failed

    echo
    echo "[ok] Servicio manual eliminado."
fi

# ============================================================
# COMPROBAR QUE NO QUEDE EL PROCESO
# ============================================================

echo
echo "[info] Comprobando estado..."

if systemctl is-active \
    --quiet "${SERVICE_NAME}" 2>/dev/null
then
    echo
    echo "ADVERTENCIA:"
    echo "${SERVICE_NAME} todavía aparece activo."
else
    echo "[ok] ${SERVICE_NAME} no está activo."
fi

# ============================================================
# OPCIÓN PARA REACTIVAR SERVICIO PRINCIPAL/IPFS
# ============================================================

if systemctl cat "${MAIN_SERVICE}" >/dev/null 2>&1; then

    echo
    echo "Se encontró el servicio principal/IPFS:"
    echo
    echo "  ${MAIN_SERVICE}"
    echo

    read -r -p \
    "¿Desea habilitarlo e iniciarlo nuevamente? [s/N]: " answer

    case "${answer}" in
        s|S|si|SI|sí|Sí)

            echo
            echo "[info] Reactivando ${MAIN_SERVICE}..."

            sudo systemctl enable --now "${MAIN_SERVICE}"

            sleep 2

            echo
            sudo systemctl \
                --no-pager \
                --full \
                status "${MAIN_SERVICE}" || true
            ;;

        *)
            echo
            echo "[info] ${MAIN_SERVICE} permanecerá detenido."
            ;;
    esac
fi

echo
echo "============================================================"
echo " FINALIZADO"
echo "============================================================"
