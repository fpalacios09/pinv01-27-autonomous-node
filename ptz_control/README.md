# PTZ Control — PINV01-27

Módulo auxiliar para el repositorio `pinv01-27-autonomous-node`.

Permite validar y controlar una cámara PTZ HiLook/Hikvision desde una NVIDIA Jetson Orin Nano mediante ONVIF. También incluye una herramienta opcional para visualizar el RTSP mediante OpenCV/X11 mientras se mueve la cámara.

La configuración fue validada en:

* NVIDIA Jetson Orin Nano.
* JetPack 5.x / Ubuntu 20.04.
* Miniconda.
* Python 3.8.
* Cámara HiLook `PTZ-N4225I-DE`.
* ONVIF habilitado.
* RTSP accesible desde la Jetson.

> Este módulo utiliza un entorno Conda independiente llamado `onvif` para no modificar el entorno principal `yolo` ni sus versiones de PyTorch, CUDA, cuDNN o TensorRT.

## Estructura

```text
ptz\_control/
├── .gitignore
├── README.md
├── camera\_env.example.sh
├── requirements.txt
├── setup\_onvif.sh
├── validate\_onvif.py
├── ptz\_move\_test.py
├── ptz\_control.py
├── ptz\_control\_view.py
├── run\_validate.sh
├── run\_move\_test.sh
├── run\_control.sh
└── run\_control\_view.sh
```

## 1\. Requisitos previos

La Jetson debe poder alcanzar la cámara:

```bash
ping 192.168.100.41
```

ONVIF debe estar habilitado en la cámara y el usuario debe tener permisos PTZ.

Miniconda debe estar instalado según `docs/jetson/03-miniconda.md`.

## 2\. Crear el entorno ONVIF

Desde la raíz del repositorio:

```bash
cd ptz\_control
chmod +x \*.sh
./setup\_onvif.sh
```

El instalador crea/reutiliza el entorno Conda `onvif` con Python 3.8 e instala las dependencias necesarias sin tocar el entorno `yolo`.

## 3\. Configurar las credenciales

```bash
cp camera\_env.example.sh camera\_env.sh
nano camera\_env.sh
```

## 4\. Validar ONVIF

```bash
./run\_validate.sh
```

Una ejecución correcta debe terminar con:

```text
\[OK] Servicio PTZ disponible.
\[OK] Validación finalizada correctamente.
```

## 5\. Prueba corta de movimiento

```bash
./run\_move\_test.sh
```

Realiza un pequeño movimiento a la derecha y luego envía `Stop`.

## 6\. Control PTZ desde terminal

```bash
./run\_control.sh
```

Controles: `w`, `a`, `s`, `d`, `+`, `-`, `q`. Presiona Enter después de cada comando.

## 7\. Control PTZ + RTSP por X11

Este modo es opcional y requiere que el entorno `onvif` pueda importar `cv2`:

```bash
conda run -n onvif python -c "import cv2; print(cv2.\_\_version\_\_)"
./run\_control\_view.sh
```

Con MobaXterm, `echo $DISPLAY` debe mostrar algo como `localhost:10.0`. La visualización por X11 puede ser lenta; eso no afecta la velocidad del comando ONVIF.

