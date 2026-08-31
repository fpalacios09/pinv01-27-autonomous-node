# 11. Solución de problemas

## Torch muestra CUDA `False`

```bash
python -c "import torch; print(torch.__version__); print(torch.version.cuda); print(torch.cuda.is_available())"
```

Si `torch.version.cuda` es `None`, se instaló un wheel CPU. Reinstalar los wheels ARM64 compatibles con JetPack.

## El servicio queda `disabled`

```bash
sudo systemctl enable --now pinv0127.service
systemctl is-enabled pinv0127.service
```

`start` o `restart` no habilitan el inicio automático.

## El servicio no ve Conda

```bash
CONDA_BASE="$(conda info --base)"
ls -l "$CONDA_BASE/condabin/conda"
```

Usar rutas absolutas y no depender de `.bashrc`.

## El instalador systemd indica una variante inválida

Las variantes soportadas son:

```text
nano_esp32
nano_33_ble
```

Ejemplos:

```bash
bash scripts/install/install_systemd_service.sh yolo nano_esp32
bash scripts/install/install_systemd_service.sh yolo nano_33_ble
```

## El servicio apunta a un `node.py` incorrecto

```bash
systemctl cat pinv0127.service
```

Verificar que `ExecStart` apunte a:

```text
src/update_manager/nano_esp32/node.py
```

o:

```text
src/update_manager/nano_33_ble/node.py
```

según la placa instalada.

## No existe `/dev/mcu` o `/dev/adapter`

```bash
sudo udevadm control --reload-rules
sudo udevadm trigger
ls -l /dev/ttyACM* /dev/ttyUSB* 2>/dev/null
```

Verificar serial, sintaxis y grupo `dialout`.

```bash
groups
```

## Nano ESP32 no aparece en DFU

```bash
dfu-util --list
```

Verificar que el uploader esté instalado:

```bash
bash scripts/install/install_nano_esp32_uploader.sh
```

y comprobar el acceso al dispositivo DFU `2341:0070`.

## Nano 33 BLE no puede actualizarse

Verificar Arduino CLI y el core:

```bash
arduino-cli version
arduino-cli core list
arduino-cli board list
```

Debe aparecer el core:

```text
arduino:mbed_nano
```

Comprobar además el alias:

```bash
ls -l /dev/mcu
readlink -f /dev/mcu
```

Si falta el uploader:

```bash
bash scripts/install/install_nano_33_ble_uploader.sh
```

## IPFS queda esperando

```bash
ipfs daemon
ipfs swarm peers
tail -n 100 ~/Desktop/updates_ipfs/ipfs_daemon.log
```

## OpenCV CUDA aparece `False`

Esto no implica que Torch esté usando CPU:

```bash
python -c "import torch; print(torch.cuda.is_available())"
```
