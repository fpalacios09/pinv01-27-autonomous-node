# 5. Instalar PyTorch con CUDA en Jetson

> No instalar primero el wheel genérico de PyPI. En Jetson, PyTorch debe coincidir con JetPack, Python y ARM64.

## Entorno

```bash
conda activate yolo
python -V
```

Debe ser Python 3.8 para los wheels de esta guía.

## Dependencias

```bash
sudo apt update
sudo apt install -y python3-pip libopenblas-dev
python -m pip install --upgrade pip
python -m pip install numpy==1.23.5
```

## PyTorch y Torchvision de referencia

JetPack 5.1.3 conserva el mismo *compute stack* que 5.1.2. La siguiente combinación se usa como referencia práctica para la plataforma del proyecto:

```bash
python -m pip uninstall -y torch torchvision || true

python -m pip install --no-cache-dir \
  'https://github.com/ultralytics/assets/releases/download/v0.0.0/torch-2.1.0a0+41361538.nv23.06-cp38-cp38-linux_aarch64.whl'

python -m pip install --no-cache-dir \
  'https://github.com/ultralytics/assets/releases/download/v0.0.0/torchvision-0.16.2+c6f3977-cp38-cp38-linux_aarch64.whl'
```

## Verificación obligatoria

```bash
python - <<'PYTORCH_CHECK'
import torch
print('Torch:', torch.__version__)
print('CUDA de Torch:', torch.version.cuda)
print('CUDA disponible:', torch.cuda.is_available())
if torch.cuda.is_available():
    print('GPU:', torch.cuda.get_device_name(0))
PYTORCH_CHECK
```

Debe imprimir `CUDA disponible: True`.

Si imprime `False`, no continuar con Ultralytics. Revisar [`10-troubleshooting.md`](10-troubleshooting.md).

Fuentes:

- NVIDIA PyTorch for Jetson: https://docs.nvidia.com/deeplearning/frameworks/install-pytorch-jetson-platform/index.html
- Ultralytics Jetson guide: https://docs.ultralytics.com/guides/nvidia-jetson/
