#!/usr/bin/env bash
set -euo pipefail

# Instalador del uploader para Arduino Nano 33 BLE.
# Ejecutar como usuario normal:
#   bash scripts/install/install_nano_33_ble_uploader.sh
#
# Instala Arduino CLI + core arduino:mbed_nano.
# El core instala la variante bossac específica de Arduino.
# La Jetson NO compila firmware durante una actualización remota.

ARDUINO_CLI_VERSION="${ARDUINO_CLI_VERSION:-1.5.1}"

if [[ "${EUID}" -eq 0 ]]; then
    echo "[error] No ejecute este script con sudo."
    echo "[info] Ejecútelo como usuario normal; el script solicitará sudo cuando corresponda."
    exit 1
fi

echo "=============================================="
echo " PINV01-27 - Uploader Arduino Nano 33 BLE"
echo "=============================================="

ARCH="$(dpkg --print-architecture)"
if [[ "${ARCH}" != "arm64" ]]; then
    echo "[error] Este instalador está preparado para Jetson Linux ARM64."
    echo "[info] Arquitectura detectada: ${ARCH}"
    exit 1
fi

echo "[1/7] Instalando dependencias del sistema..."
sudo apt-get update
sudo apt-get install -y curl ca-certificates udev

echo "[2/7] Instalando Arduino CLI ${ARDUINO_CLI_VERSION} para ARM64..."
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT
DEB_NAME="arduino-cli_${ARDUINO_CLI_VERSION}-1_arm64.deb"
DEB_URL="https://github.com/arduino/arduino-cli/releases/download/v${ARDUINO_CLI_VERSION}/${DEB_NAME}"
DEB_PATH="${TMP_DIR}/${DEB_NAME}"

curl --fail --location --show-error "${DEB_URL}" --output "${DEB_PATH}"
sudo apt-get install -y "${DEB_PATH}"

ARDUINO_CLI_BIN="$(command -v arduino-cli || true)"
if [[ -z "${ARDUINO_CLI_BIN}" ]]; then
    echo "[error] arduino-cli no quedó instalado correctamente."
    exit 1
fi

echo "[ok] Arduino CLI: ${ARDUINO_CLI_BIN}"
arduino-cli version

echo "[3/7] Inicializando configuración de Arduino CLI..."
arduino-cli config init >/dev/null 2>&1 || true

echo "[4/7] Actualizando índice de cores..."
arduino-cli core update-index

echo "[5/7] Instalando core arduino:mbed_nano..."
arduino-cli core install arduino:mbed_nano

echo "[6/7] Agregando ${USER} al grupo dialout..."
sudo usermod -aG dialout "${USER}"

echo "[7/7] Verificando uploader del Nano 33 BLE..."
if ! arduino-cli core list | grep -q '^arduino:mbed_nano'; then
    echo "[error] El core arduino:mbed_nano no aparece instalado."
    exit 1
fi

echo "[ok] Core arduino:mbed_nano instalado."

BOSSAC_PATH="$(find "${HOME}/.arduino15/packages/arduino/tools/bossac" -type f -name bossac -perm -u+x 2>/dev/null | sort | tail -n 1)"
if [[ -n "${BOSSAC_PATH}" ]]; then
    echo "[ok] bossac Arduino: ${BOSSAC_PATH}"
else
    echo "[warning] No se encontró bossac con la ruta esperada."
    echo "[info] Revise: arduino-cli config dump"
fi

echo
echo "Instalación completada."
echo
echo "IMPORTANTE:"
echo "  - Cierre sesión y vuelva a entrar para aplicar el grupo dialout."
echo "  - La creación de /dev/mcu y /dev/adapter se hace por separado con:"
echo "      scripts/install/install_udev_rules.sh SERIAL_MCU SERIAL_ADAPTADOR"
echo
echo "Pruebas recomendadas:"
echo "  arduino-cli board list"
echo "  arduino-cli core list"
echo
echo "Carga manual de un binario ya compilado:"
echo '  arduino-cli upload --fqbn arduino:mbed_nano:nano33ble \'
echo '      --port "$(readlink -f /dev/mcu)" \'
echo '      --input-file ./firmware.ino.bin \'
echo '      --discovery-timeout 30s --verbose'
