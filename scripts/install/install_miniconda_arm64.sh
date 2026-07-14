#!/usr/bin/env bash
set -euo pipefail
[[ "$(uname -m)" == "aarch64" ]] || { echo "ERROR: se requiere aarch64" >&2; exit 1; }
installer="/tmp/Miniconda3-latest-Linux-aarch64.sh"
wget -O "$installer" https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-aarch64.sh
bash "$installer" -b -p "$HOME/miniconda3"
"$HOME/miniconda3/bin/conda" init bash
echo "Miniconda instalado. Ejecute: source ~/.bashrc"
