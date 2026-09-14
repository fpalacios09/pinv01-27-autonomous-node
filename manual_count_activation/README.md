# Manual Count Activation

Coloque en esta misma carpeta:

- `script.py`
- al menos un archivo de pesos `*.pt`
- `install_manual_count_service.sh`
- `remove_manual_count_service.sh`

Instalar e iniciar el modo manual:

```bash
bash install_manual_count_service.sh
```

Por defecto usa el entorno Conda `yolo`.

Para especificar otro:

```bash
bash install_manual_count_service.sh NOMBRE_ENTORNO
```

Ver logs:

```bash
journalctl -u pinv0127-manual-count.service -f
```

Reiniciar después de reemplazar `script.py` o los pesos:

```bash
sudo systemctl restart pinv0127-manual-count.service
```

Eliminar el servicio manual y opcionalmente reactivar el servicio principal/IPFS:

```bash
bash remove_manual_count_service.sh
```

Nota: `script.py` debe apuntar al nombre correcto del archivo `.pt` que existe en esta carpeta.
