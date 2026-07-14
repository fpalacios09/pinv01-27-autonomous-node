# Matriz de plataforma de referencia

## Hardware objetivo

| Componente | Referencia |
|---|---|
| Computador de borde | NVIDIA Jetson Orin Nano 4 GB |
| Host MCU | Arduino Nano ESP32 |
| Enlace Jetson → MCU | USB serial, alias `/dev/mcu` |
| Enlace MCU → Jetson para hashes | Adaptador USB/UART, alias `/dev/adapter` |
| Conectividad de actualización | Raspberry Pi con módem 4G |

## Software objetivo

| Componente | Versión de referencia |
|---|---|
| JetPack | 5.1.3 |
| Jetson Linux / L4T | 35.5.0 |
| Ubuntu | 20.04 |
| Kernel | 5.10 |
| CUDA | 11.4.19 |
| cuDNN | 8.6.0 |
| TensorRT | 8.5.2 |
| Python del entorno | 3.8 |
| Kubo | 0.42.0 linux-arm64 |
| PyTorch | 2.1.0a0+41361538.nv23.06 |
| Torchvision | 0.16.2+c6f3977 |
| Ultralytics | 8.3.226 como punto de partida reproducible |

NVIDIA indica que JetPack 5.1.3 usa Jetson Linux 35.5.0, Ubuntu 20.04, CUDA 11.4.19, cuDNN 8.6.0 y TensorRT 8.5.2. Además, JetPack 5.1.3 conserva el mismo *compute stack* de JetPack 5.1.2. Por ello, la guía usa como referencia los wheels ARM64 de PyTorch y Torchvision publicados para JetPack 5.1.2 y exige verificar CUDA inmediatamente después de instalarlos.

Fuentes oficiales:

- NVIDIA JetPack 5.1.3: https://developer.nvidia.com/embedded/jetpack-sdk-513
- NVIDIA PyTorch for Jetson: https://docs.nvidia.com/deeplearning/frameworks/install-pytorch-jetson-platform/index.html
- Ultralytics en NVIDIA Jetson: https://docs.ultralytics.com/guides/nvidia-jetson/
- Kubo: https://docs.ipfs.tech/install/command-line/

## No mezclar plataformas

No instalar un wheel x86_64 ni una distribución estándar de PyTorch con CUDA para PC. La Jetson usa arquitectura ARM64 y necesita paquetes construidos para su versión de JetPack/Python.

## Captura de la plataforma instalada

```bash
cat /etc/nv_tegra_release
uname -a
lsb_release -a
python --version
nvcc --version || true
python -c "import torch; print(torch.__version__, torch.version.cuda, torch.cuda.is_available())"
python -c "import ultralytics; print(ultralytics.__version__)"
ipfs version
```
