# Firmware del Host MCU

Archivo principal: [`firmware/host_mcu/lora/lora.ino`](../../firmware/host_mcu/lora/lora.ino).

## Hardware de referencia

Arduino Nano ESP32, basado en ESP32-S3.

Documentación oficial: https://docs.arduino.cc/hardware/nano-esp32/

## Dependencias

1. Arduino IDE 2.x o Arduino CLI.
2. Paquete de placa **Arduino Nano ESP32**.
3. Librería **Blues Notecard** (`Notecard.h`).

## Configuración local

```bash
cd firmware/host_mcu/lora
cp config.example.h config.h
nano config.h
```

```cpp
#define PRODUCT_UID "com.example:pinv0127"
```

`config.h` no se versiona.

## Carga inicial

1. Abrir `lora.ino`.
2. Seleccionar `Arduino Nano ESP32`.
3. Seleccionar el puerto.
4. Compilar y cargar.
5. Verificar `Ready` en el monitor serie.

## Firmware binario para actualización remota

El gestor busca un archivo `*.ino.bin` en la carpeta `arduino/` del paquete recibido y usa `dfu-util` para `2341:0070`.

```bash
dfu-util --list
sudo cp rules/99-arduino-nano-esp32-dfu.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules
sudo udevadm trigger
```
