# Firmware del Host MCU

El repositorio mantiene variantes independientes del firmware para cada Host MCU soportado.

## Arduino Nano ESP32

Archivo principal:

[`firmware/host_mcu/nano_esp32/lora/lora.ino`](../../firmware/host_mcu/nano_esp32/lora/lora.ino)

Hardware: Arduino Nano ESP32, basado en ESP32-S3.

Documentación oficial: https://docs.arduino.cc/hardware/nano-esp32/

### Dependencias

1. Arduino IDE 2.x o Arduino CLI.
2. Paquete de placa compatible con **Arduino Nano ESP32**.
3. Librería **Blues Notecard** (`Notecard.h`).

### Configuración local

```bash
cd firmware/host_mcu/nano_esp32/lora
cp config.example.h config.h
nano config.h
```

```cpp
#define PRODUCT_UID "com.example:pinv0127"
```

`config.h` no se versiona.

### Carga inicial

1. Abrir `lora.ino`.
2. Seleccionar `Arduino Nano ESP32`.
3. Seleccionar el puerto correspondiente.
4. Compilar y cargar.
5. Verificar `Ready` en el monitor serie.

### Uploader para actualización remota

En la Jetson:

```bash
bash scripts/install/install_nano_esp32_uploader.sh
```

El instalador configura `dfu-util`, el acceso mediante `dialout` y el permiso udev requerido para el dispositivo DFU `2341:0070`.

El gestor correspondiente es:

```text
src/update_manager/nano_esp32/node.py
```

El gestor busca un archivo `*.ino.bin` dentro de la carpeta `arduino/` del paquete recibido y realiza la carga mediante DFU.

Para comprobar manualmente la detección DFU:

```bash
dfu-util --list
```

## Arduino Nano 33 BLE

Archivo principal:

[`firmware/host_mcu/nano_33_ble/lora/lora.ino`](../../firmware/host_mcu/nano_33_ble/lora/lora.ino)

Hardware: Arduino Nano 33 BLE, basado en nRF52840.

Documentación oficial: https://docs.arduino.cc/hardware/nano-33-ble/

### Dependencias

1. Arduino IDE 2.x o Arduino CLI.
2. Core **Arduino Mbed OS Nano Boards** (`arduino:mbed_nano`).
3. Librería **Blues Notecard** (`Notecard.h`).

### Configuración local

```bash
cd firmware/host_mcu/nano_33_ble/lora
cp config.example.h config.h
nano config.h
```

```cpp
#define PRODUCT_UID "com.example:pinv0127"
```

`config.h` no se versiona.

### Carga inicial

1. Abrir `lora.ino`.
2. Seleccionar `Arduino Nano 33 BLE`.
3. Seleccionar el puerto correspondiente.
4. Compilar y cargar.
5. Verificar `Ready` en el puerto utilizado por el firmware.

### Uploader para actualización remota

En la Jetson:

```bash
bash scripts/install/install_nano_33_ble_uploader.sh
```

El instalador configura Arduino CLI, el core `arduino:mbed_nano` y la versión de `bossac` incluida por Arduino para esta plataforma.

El gestor correspondiente es:

```text
src/update_manager/nano_33_ble/node.py
```

Durante una actualización remota:

1. El gestor localiza `/dev/mcu`.
2. Resuelve el alias al dispositivo tty real.
3. Arduino CLI realiza el reset de 1200 bps.
4. El Nano 33 BLE entra al bootloader y se reenumera por USB.
5. Arduino CLI detecta el puerto del bootloader.
6. `bossac` carga el archivo `.ino.bin`.
7. La placa se reinicia y vuelve a ejecutar el firmware.

La Jetson no compila el firmware durante este proceso.

## Firmware binario para actualización remota

Para ambas variantes, el paquete remoto utiliza:

```text
arduino/
├── readme.txt
└── sketch.ino.bin
```

El archivo `.ino.bin` debe haber sido compilado previamente para la misma placa que utiliza el nodo.

> [!IMPORTANT]
> Un firmware compilado para Nano ESP32 no debe cargarse en un Nano 33 BLE y un firmware compilado para Nano 33 BLE no debe cargarse en un Nano ESP32.

El procedimiento completo de actualización está documentado en:

[`docs/updates/procedimiento-de-actualizacion.md`](../updates/procedimiento-de-actualizacion.md)
