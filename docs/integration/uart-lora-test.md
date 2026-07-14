# Prueba Jetson → UART → LoRa

## Prerrequisitos

- Firmware `lora.ino` cargado.
- Alias `/dev/mcu` funcional.
- Usuario en `dialout`.
- Entorno `yolo` activo.

## Mensaje esperado

```json
{
  "stream_key": "carbikebustruck",
  "car_to_sl": 1,
  "bike_to_sl": 0,
  "heavy_to_sl": 0,
  "total_to_sl": 1,
  "car_from_sl": 0,
  "bike_from_sl": 1,
  "heavy_from_sl": 0,
  "total_from_sl": 1
}
```

## Prueba sintética sin cámara

```bash
conda activate yolo
python examples/send_test_count.py --port /dev/mcu
```

## Prueba con el contador

```bash
export PINV_VIDEO_SOURCE='rtsp://usuario:contrasena@IP:554/ruta'
export PINV_MODEL_PATH='/ruta/yolo26n.pt'
export PINV_MCU_PORT='/dev/mcu'
python src/vehicle_counter/script.py
```

Durante la primera validación usar un intervalo de prueba más corto que los 900 segundos de producción.

## Verificación

1. La Jetson abre `/dev/mcu`.
2. El MCU procesa el JSON.
3. Notehub recibe `count.qo`.
4. `heavy_*` suma buses y camiones.
