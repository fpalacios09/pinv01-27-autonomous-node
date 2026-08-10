#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# PINV01-27 - Instalador del servicio OpenVPN
# ============================================================

# El instalador debe ejecutarse como usuario normal.
# Internamente utiliza sudo cuando necesita escribir en /etc.
[[ ${EUID} -ne 0 ]] || {
    echo "ERROR: Ejecute este instalador como usuario normal, no con sudo." >&2
    exit 1
}

# Ruta al archivo .ovpn recibida como primer argumento.
ovpn_source="${1:-}"

if [[ -z "$ovpn_source" ]]; then
    echo "Uso:"
    echo "  bash scripts/install/install_openvpn_service.sh /ruta/al/archivo.ovpn"
    exit 1
fi

if [[ ! -f "$ovpn_source" ]]; then
    echo "ERROR: No existe el archivo OVPN:"
    echo "  $ovpn_source"
    exit 1
fi

# ============================================================
# VERIFICAR OPENVPN
# ============================================================

if ! command -v openvpn >/dev/null 2>&1; then
    echo "ERROR: OpenVPN no está instalado."
    echo ""
    echo "Instalar con:"
    echo "  sudo apt update"
    echo "  sudo apt install -y openvpn"
    exit 1
fi

openvpn_bin="$(command -v openvpn)"

echo "[OK] OpenVPN encontrado en:"
echo "  $openvpn_bin"

# ============================================================
# RUTAS DEL REPOSITORIO
# ============================================================

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/../.." && pwd)"

service_template="$repo_root/systemd/pinv0127-vpn.service.example"

if [[ ! -f "$service_template" ]]; then
    echo "ERROR: No existe la plantilla del servicio:"
    echo "  $service_template"
    exit 1
fi

# ============================================================
# INSTALAR CONFIGURACIÓN PRIVADA
# ============================================================

echo ""
echo "[1/4] Creando directorio privado de configuración VPN..."

sudo install -d -m 0700 /etc/pinv0127/vpn

echo "[2/4] Instalando archivo OVPN..."

sudo install \
    -m 0600 \
    "$ovpn_source" \
    /etc/pinv0127/vpn/client.ovpn

# ============================================================
# INSTALAR SERVICIO
# ============================================================

echo "[3/4] Instalando servicio systemd..."

sudo install \
    -m 0644 \
    "$service_template" \
    /etc/systemd/system/pinv0127-vpn.service

# ============================================================
# ACTIVAR SERVICIO
# ============================================================

echo "[4/4] Activando servicio..."

sudo systemctl daemon-reload
sudo systemctl enable --now pinv0127-vpn.service

echo ""
echo "============================================================"
echo " PINV01-27 OpenVPN instalado correctamente"
echo "============================================================"
echo ""
echo "Configuración privada:"
echo "  /etc/pinv0127/vpn/client.ovpn"
echo ""
echo "Servicio:"
echo "  /etc/systemd/system/pinv0127-vpn.service"
echo ""
echo "Estado:"
echo ""

sudo systemctl --no-pager --full status pinv0127-vpn.service || true