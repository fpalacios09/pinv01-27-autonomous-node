# 8. Aliases persistentes con udev

El proyecto usa:

- `/dev/mcu`: Arduino Nano ESP32 que recibe los conteos.
- `/dev/adapter`: adaptador USB/UART por el que llegan hashes CID/comandos.

## Aclaración importante

Una regla basada en `ATTRS{serial}` sigue al **mismo dispositivo físico aunque cambie de puerto USB o número tty**. No reserva un puerto USB para cualquier dispositivo.

## Identificar el tty

```bash
ls -l /dev/ttyACM* /dev/ttyUSB* 2>/dev/null
udevadm info -a -n /dev/ttyACM0 | less
```

Buscar el primer atributo `serial` único en la jerarquía USB, por ejemplo:

```text
ATTRS{serial}=="85435303533351F0F1"
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

## Eliminar las reglas

```bash
sudo rm /etc/udev/rules.d/99-pinv0127-serial.rules
sudo udevadm control --reload-rules
sudo udevadm trigger
```
