# 3. Instalar Miniconda para ARM64

La Jetson es ARM64/aarch64. No utilizar el instalador x86_64.

## Instalación manual

```bash
cd /tmp
wget -O miniconda.sh https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-aarch64.sh
bash miniconda.sh
```

Aceptar la licencia, instalar en `~/miniconda3` e inicializar Conda cuando el instalador lo solicite. Después:

```bash
source ~/.bashrc
conda --version
conda info --base
```

Crear el entorno de referencia:

```bash
conda create -n yolo python=3.8 pip -y
conda activate yolo
python -V
```

También puede usarse el script:

```bash
bash scripts/install/install_miniconda_arm64.sh
```

## Verificaciones importantes para systemd

```bash
conda info --base
conda env list
conda run -n yolo python -V
conda run -n yolo python -c "print('OK CONDA')"
```

La ruta usada por el servicio será normalmente:

```bash
$(conda info --base)/condabin/conda
```

## Criterio de éxito

`conda run -n yolo python -c "print('OK CONDA')"` imprime `OK CONDA` sin activar manualmente el entorno.
