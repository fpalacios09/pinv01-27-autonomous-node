#!/usr/bin/env bash
set -euo pipefail
ENV_NAME="onvif"
PYTHON_VERSION="3.8"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"

echo "[INFO] Entorno Conda independiente: $ENV_NAME"
command -v conda >/dev/null 2>&1 || { echo "[ERROR] Conda no disponible. Instala Miniconda según docs/jetson/03-miniconda.md"; exit 1; }

sudo apt update
sudo apt install -y libxml2-dev libxslt1-dev python3-dev build-essential

if conda env list | awk '{print $1}' | grep -qx "$ENV_NAME"; then
  echo "[INFO] El entorno $ENV_NAME ya existe; se reutiliza."
else
  conda create -n "$ENV_NAME" "python=$PYTHON_VERSION" pip -y
fi

conda run -n "$ENV_NAME" python -m pip install --upgrade pip setuptools wheel
conda run -n "$ENV_NAME" python -m pip install -r requirements.txt
conda run -n "$ENV_NAME" python -c "from onvif import ONVIFCamera; import platformdirs; print('[OK] ONVIF importado'); print('[OK] platformdirs', platformdirs.__version__)"

echo "[OK] Instalación terminada."
echo "Siguiente: cp camera_env.example.sh camera_env.sh && nano camera_env.sh && ./run_validate.sh"
