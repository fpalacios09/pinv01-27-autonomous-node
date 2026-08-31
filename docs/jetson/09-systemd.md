# 9. Servicio systemd

El servicio ejecuta el `node.py` correspondiente a la variante de Host MCU instalada y reinicia el proceso si falla.

Las variantes disponibles son:

```text
src/update_manager/nano_esp32/node.py
src/update_manager/nano_33_ble/node.py
```

## Instalación automatizada

Ejecutar como el usuario normal.

### Arduino Nano ESP32

```bash
bash scripts/install/install_systemd_service.sh yolo nano_esp32
```

### Arduino Nano 33 BLE

```bash
bash scripts/install/install_systemd_service.sh yolo nano_33_ble
```

El primer argumento es el entorno Conda y el segundo identifica la variante del Host MCU.

Si se omite el segundo argumento, el instalador utiliza `nano_esp32` para mantener compatibilidad con instalaciones anteriores:

```bash
bash scripts/install/install_systemd_service.sh yolo
```

El script detecta el usuario, repositorio, base de Conda y rutas absolutas. Luego crea `/etc/systemd/system/pinv0127.service` y ejecuta:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now pinv0127.service
```

`enable` es indispensable para el inicio automático.

## Verificar el `node.py` seleccionado

Después de instalar:

```bash
systemctl cat pinv0127.service
```

La línea `ExecStart` debe contener una de estas rutas:

```text
src/update_manager/nano_esp32/node.py
```

o:

```text
src/update_manager/nano_33_ble/node.py
```

según la placa instalada.

## Variables privadas del servicio

El instalador crea `/etc/default/pinv0127` con permisos `0600` si el archivo no existe. Editarlo para definir la fuente RTSP y el modelo sin guardar credenciales en Git:

```bash
sudo nano /etc/default/pinv0127
sudo chmod 600 /etc/default/pinv0127
sudo systemctl restart pinv0127.service
```

Los scripts Python hijos lanzados por el gestor de actualizaciones heredan estas variables.

## Instalación manual

```bash
sudo cp systemd/pinv0127.service.example /etc/systemd/system/pinv0127.service
sudo nano /etc/systemd/system/pinv0127.service
```

Reemplazar `REPLACE_NODE_SCRIPT` por la ruta absoluta correspondiente.

Ejemplo para Nano ESP32:

```text
/ruta/al/repositorio/src/update_manager/nano_esp32/node.py
```

Ejemplo para Nano 33 BLE:

```text
/ruta/al/repositorio/src/update_manager/nano_33_ble/node.py
```

Luego:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now pinv0127.service
sudo systemctl status pinv0127.service
```

## Logs

```bash
journalctl -u pinv0127.service -f
journalctl -u pinv0127.service -b --no-pager
```

## Prueba de reinicio

```bash
sudo reboot
```

Después:

```bash
systemctl is-enabled pinv0127.service
systemctl is-active pinv0127.service
sudo systemctl status pinv0127.service
```

Resultados esperados: `enabled` y `active`.
