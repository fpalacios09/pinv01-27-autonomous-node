#!/usr/bin/env bash
set -euo pipefail
[[ $# -eq 2 ]] || { echo "Uso: $0 SERIAL_MCU SERIAL_ADAPTADOR" >&2; exit 1; }
tmp="$(mktemp)"
cat > "$tmp" <<RULES
SUBSYSTEM=="tty", ATTRS{serial}=="$1", SYMLINK+="mcu", MODE="0660", GROUP="dialout"
SUBSYSTEM=="tty", ATTRS{serial}=="$2", SYMLINK+="adapter", MODE="0660", GROUP="dialout"
RULES
sudo install -m 0644 "$tmp" /etc/udev/rules.d/99-pinv0127-serial.rules
rm -f "$tmp"
sudo usermod -aG dialout "$USER"
sudo udevadm control --reload-rules
sudo udevadm trigger
echo "Reglas instaladas. Reconecte los dispositivos y vuelva a iniciar sesión."
