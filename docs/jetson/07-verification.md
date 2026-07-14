# 7. Verificar Torch, CUDA y Ultralytics

## Diagnóstico completo

```bash
conda activate yolo
python examples/verify_jetson_stack.py
```

El script comprueba arquitectura y Python, importa Torch y Ultralytics, exige CUDA, carga un modelo YOLO y ejecuta una inferencia en `device=0`.

La primera ejecución puede descargar automáticamente los pesos del modelo.

## Prueba de conteo genérico

Con webcam USB:

```bash
python examples/generic_vehicle_counter.py --source 0 --show
```

Con video:

```bash
python examples/generic_vehicle_counter.py --source /ruta/video.mp4 --show
```

Con RTSP:

```bash
export PINV_VIDEO_SOURCE='rtsp://usuario:contrasena@IP:554/ruta'
python examples/generic_vehicle_counter.py --source "$PINV_VIDEO_SOURCE"
```

## Criterio de éxito

- El script informa una GPU NVIDIA.
- La inferencia usa `device=0`.
- El contador procesa frames sin error.
