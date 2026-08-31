# 8. Aliases persistentes con udev

El proyecto usa:

- `/dev/mcu`: Host MCU instalado en el nodo, Arduino Nano ESP32 o Arduino Nano 33 BLE.
- `/dev/adapter`: adaptador USB/UART por el que llegan hashes CID/comandos.

## Aclaración importante

Una regla basada en `ATTRS{serial}` sigue al **mismo dispositivo físico aunque cambie de puerto USB o número tty**. No reserva un puerto USB para cualquier dispositivo.

El alias `/dev/mcu` identifica el puerto normal del Host MCU mediante su número de serie USB.

## Identificar el tty

```bash
ls -l /dev/ttyACM* /dev/ttyUSB* 2>/dev/null
udevadm info -a -n /dev/ttyACM0 | less
```

Buscar el primer atributo `serial` único en la jerarquía USB, por ejemplo:

```text
ATTRS{serial}=="85435303533351F0F1"
```

También puede consultarse mediante:

```bash
udevadm info --query=property --name=/dev/ttyACM0 | grep -E 'ID_SERIAL|ID_VENDOR|ID_MODEL'
```

## Crear las reglas

```bash
sudo cp rules/99-pinv0127-serial.rules.example /etc/udev/rules.d/99-pinv0127-serial.rules
sudo nano /etc/udev/rules.d/99-pinv0127-serial.rules
```

```udev
SUBSYSTEM=="tty", ATTRS{serial}=="SERIAL_DEL_MCU", SYMLINK+="mcu", MODE="0660", GROUP="dialout"
SUBSYSTEM=="tty", ATTRS{serial}=="SERIAL_DEL_ADAPTADOR", SYMLINK+="adapter", MODE="0660", GROUP="dialout"
```

O automatizar:

```bash
bash scripts/install/install_udev_rules.sh SERIAL_MCU SERIAL_ADAPTADOR
```

## Nano ESP32 y permiso DFU

El alias `/dev/mcu` y el permiso para acceder al Nano ESP32 en modo DFU son configuraciones diferentes.

El uploader del Nano ESP32 instala adicionalmente la regla:

```text
rules/99-arduino.rules
```

para permitir el acceso al dispositivo DFU `2341:0070`.

```bash
bash scripts/install/install_nano_esp32_uploader.sh
```

## Nano 33 BLE y reenumeración del bootloader

En el Nano 33 BLE, `/dev/mcu` se utiliza para localizar el puerto normal de la placa.

Durante una actualización, Arduino CLI realiza el reset de 1200 bps. El puerto normal puede desaparecer y el bootloader puede aparecer temporalmente con otro nombre, por ejemplo:

```text
/dev/ttyACM0
        ↓
bootloader
        ↓
/dev/ttyACM1
```

El gestor resuelve inicialmente `/dev/mcu` al tty real y Arduino CLI se encarga de detectar el puerto temporal del bootloader.

Por tanto, no es necesario que `/dev/mcu` permanezca disponible durante toda la reenumeración del bootloader.

## Probar la regla

```bash
udevadm info -q path -n /dev/ttyACM0
sudo udevadm test "$(udevadm info -q path -n /dev/ttyACM0)"
```

## Recargar correctamente

```bash
sudo udevadm control --reload-rules
sudo udevadm trigger
```

Desconectar y reconectar ambos dispositivos.

## Verificar

```bash
ls -l /dev/mcu /dev/adapter
readlink -f /dev/mcu
readlink -f /dev/adapter
groups
```

## Eliminar las reglas de aliases

```bash
sudo rm /etc/udev/rules.d/99-pinv0127-serial.rules
sudo udevadm control --reload-rules
sudo udevadm trigger
```
