# 2. Preparación del sistema base

```bash
sudo apt update
sudo apt install -y \
  git curl wget ca-certificates build-essential cmake pkg-config \
  python3-pip python3-dev libopenblas-dev \
  libjpeg-dev zlib1g-dev libfreetype6-dev \
  libgl1 libglib2.0-0 \
  nano unzip tar \
  dfu-util udev
```

Agregar el usuario a `dialout`:

```bash
sudo usermod -aG dialout "$USER"
```

Cerrar sesión y volver a entrar para que el grupo se aplique.

Verificar espacio:

```bash
df -h
free -h
```

El modelo, los logs, los archivos IPFS y los entornos de Python pueden consumir varios gigabytes. Se recomienda usar almacenamiento suficiente y evitar que la partición raíz quede sin espacio.

## Criterio de éxito

```bash
groups
which git curl dfu-util
```

El usuario aparece en `dialout` y las herramientas requeridas existen.
