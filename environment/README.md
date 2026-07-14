# Entorno Python

`environment.yml` no instala PyTorch ni Torchvision porque sus wheels dependen de JetPack, Python y ARM64.

Orden: crear Python 3.8, instalar Torch, instalar Torchvision, instalar Ultralytics, verificar CUDA y exportar un lock validado.
