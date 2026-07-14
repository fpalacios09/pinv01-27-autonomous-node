# 10. Solución de problemas

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

## No existe `/dev/mcu` o `/dev/adapter`

```bash
sudo udevadm control --reload-rules
sudo udevadm trigger
ls -l /dev/ttyACM* /dev/ttyUSB* 2>/dev/null
```

Verificar serial, sintaxis y grupo `dialout`.

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
