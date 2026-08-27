#!/usr/bin/env bash
set -euo pipefail

# Instalador del uploader para Arduino Nano ESP32.
# Ejecutar como usuario normal:
#   bash scripts/install/install_nano_esp32_uploader.sh

if [[ "${EUID}" -eq 0 ]]; then
    echo "[error] No ejecute este script con sudo."
    echo "[info] Ejecútelo como usuario normal; el script solicitará sudo cuando corresponda."
    exit 1
fi

echo "=============================================="
echo " PINV01-27 - Uploader Arduino Nano ESP32"
echo "=============================================="

echo "[1/5] Actualizando índice APT..."
sudo apt-get update

echo "[2/5] Instalando dfu-util y udev..."
sudo apt-get install -y dfu-util udev

echo "[3/5] Agregando ${USER} al grupo dialout..."
sudo usermod -aG dialout "${USER}"

echo "[4/5] Instalando permiso udev para Nano ESP32 en modo DFU..."
RULE_FILE="/etc/udev/rules.d/99-pinv0127-arduino.rules"
sudo tee "${RULE_FILE}" >/dev/null <<'RULES'
# PINV01-27 - Arduino Nano ESP32 en modo DFU
SUBSYSTEM=="usb", ATTR{idVendor}=="2341", ATTR{idProduct}=="0070", MODE="0660", GROUP="dialout"
RULES
sudo chmod 0644 "${RULE_FILE}"
sudo udevadm control --reload-rules
sudo udevadm trigger

echo "[5/5] Verificando instalación..."
DFU_BIN="$(command -v dfu-util || true)"
if [[ -z "${DFU_BIN}" ]]; then
    echo "[error] dfu-util no quedó instalado correctamente."
    exit 1
fi

echo "[ok] dfu-util: ${DFU_BIN}"
dfu-util --version | head -n 1 || true
echo "[ok] Regla udev: ${RULE_FILE}"

echo
echo "Instalación completada."
echo
echo "IMPORTANTE:"
echo "  - Cierre sesión y vuelva a entrar para aplicar el grupo dialout."
echo "  - La creación de /dev/mcu y /dev/adapter se hace por separado con:"
echo "      scripts/install/install_udev_rules.sh SERIAL_MCU SERIAL_ADAPTADOR"
echo "  - Para comprobar el Nano ESP32 en DFU:"
echo "      dfu-util --list"
