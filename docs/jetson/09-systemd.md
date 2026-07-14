# 9. Servicio systemd

El servicio ejecuta `src/update_manager/node.py` dentro del entorno Conda y reinicia el proceso si falla.

## Instalación automatizada

Ejecutar como el usuario normal:

```bash
bash scripts/install/install_systemd_service.sh yolo
```

El script detecta el usuario, repositorio, base de Conda y rutas absolutas. Luego crea `/etc/systemd/system/pinv0127.service` y ejecuta:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now pinv0127.service
```

`enable` es indispensable para el inicio automático.

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
