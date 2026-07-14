# 6. Instalar Ultralytics

PyTorch con CUDA debe estar funcionando antes de este paso.

```bash
conda activate yolo
python -m pip install 'ultralytics==8.3.226'
python -m pip install pyserial==3.5 psutil matplotlib
```

Verificar que la instalación no reemplazó PyTorch por una versión CPU:

```bash
python - <<'ULTRALYTICS_CHECK'
import torch
import ultralytics
print('Ultralytics:', ultralytics.__version__)
print('Torch:', torch.__version__)
print('CUDA disponible:', torch.cuda.is_available())
assert torch.cuda.is_available(), 'PyTorch quedó sin CUDA'
ULTRALYTICS_CHECK
```

## Nota sobre OpenCV

El paquete `opencv-python` distribuido por pip normalmente no incluye CUDA. Para este proyecto, la aceleración crítica se realiza con PyTorch/TensorRT. Por ello, `cv2.cuda.getCudaEnabledDeviceCount()` puede ser `0` aunque Torch use correctamente la GPU.

## Congelar el entorno validado

```bash
pip freeze > environment/pip-freeze.txt
conda env export --no-builds > environment/environment-lock.yml
```

Fuente oficial de instalación: https://docs.ultralytics.com/quickstart/
