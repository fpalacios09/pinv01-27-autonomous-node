# 2. Preparación del sistema base

```bash
sudo apt update
sudo apt install -y \
  git curl wget ca-certificates build-essential cmake pkg-config \
  python3-pip python3-dev libopenblas-dev \
  libjpeg-dev zlib1g-dev libfreetype6-dev \
  libgl1 libglib2.0-0 \
  nano unzip tar \
  udev
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
which git curl
```

El usuario aparece en `dialout` y las herramientas requeridas existen.

## Uploader del Host MCU

Las herramientas necesarias para cargar firmware en el Host MCU se instalan
por separado según la placa utilizada.

### Arduino Nano ESP32

```bash
bash scripts/install/install_nano_esp32_uploader.sh
```

Este instalador configura `dfu-util`, las reglas y permisos necesarios para
la carga del firmware mediante DFU.

### Arduino Nano 33 BLE

```bash
bash scripts/install/install_nano_33_ble_uploader.sh
```

Este instalador configura:

- Arduino CLI.
- El core `arduino:mbed_nano`.
- La versión de `bossac` utilizada por Arduino para el Nano 33 BLE.
- Los permisos necesarios para acceder al dispositivo mediante el grupo `dialout`.

Durante una actualización remota, la Jetson no compila el firmware del Host MCU.
El gestor de actualizaciones recibe un archivo `.ino.bin` previamente compilado y
únicamente realiza su carga en la placa correspondiente.

## Aliases udev del proyecto

Los aliases permanentes:

```text
/dev/mcu
/dev/adapter
```

se configuran de forma independiente mediante:

```bash
bash scripts/install/install_udev_rules.sh SERIAL_MCU SERIAL_ADAPTADOR
```

donde:

- `SERIAL_MCU` corresponde al número de serie USB del Host MCU.
- `SERIAL_ADAPTADOR` corresponde al número de serie USB del adaptador UART utilizado para recibir los hashes de actualización.
