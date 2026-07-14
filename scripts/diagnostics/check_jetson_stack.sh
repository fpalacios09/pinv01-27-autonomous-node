#!/usr/bin/env bash
set -u
echo '=== Sistema ==='
uname -a
cat /etc/nv_tegra_release 2>/dev/null || true
lsb_release -a 2>/dev/null || true
echo '=== CUDA ==='
nvcc --version 2>/dev/null || true
echo '=== Python ==='
python -V
python - <<'STACK_CHECK'
modules = ['torch', 'torchvision', 'ultralytics', 'cv2', 'serial', 'psutil']
for name in modules:
    try:
        module = __import__(name)
        print(name, getattr(module, '__version__', 'OK'))
    except Exception as exc:
        print(name, 'ERROR:', exc)
try:
    import torch
    print('torch.version.cuda =', torch.version.cuda)
    print('torch.cuda.is_available() =', torch.cuda.is_available())
    if torch.cuda.is_available(): print('GPU =', torch.cuda.get_device_name(0))
except Exception:
    pass
STACK_CHECK
echo '=== IPFS ==='
command -v ipfs || true
ipfs version 2>/dev/null || true
echo '=== Dispositivos ==='
ls -l /dev/mcu /dev/adapter 2>/dev/null || true
