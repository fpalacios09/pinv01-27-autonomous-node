# 4. Instalar IPFS Kubo en ARM64

La aplicación espera por defecto el binario en `/usr/local/bin/ipfs`.

## Instalación reproducible de Kubo 0.42.0

```bash
cd /tmp
wget https://dist.ipfs.tech/kubo/v0.42.0/kubo_v0.42.0_linux-arm64.tar.gz
tar -xvzf kubo_v0.42.0_linux-arm64.tar.gz
cd kubo
sudo bash install.sh
ipfs version
```

O ejecutar:

```bash
bash scripts/install/install_kubo_arm64.sh
```

## Inicializar el repositorio

Ejecutar como el mismo usuario que correrá el servicio:

```bash
ipfs init
```

Probar el daemon:

```bash
ipfs daemon
```

En otra terminal:

```bash
ipfs swarm peers | head
ipfs id
```

Detener con `Ctrl+C`.

## Prueba de descarga

```bash
timeout 60s ipfs cat CID_DE_PRUEBA > /tmp/ipfs_test.bin
```

El gestor `src/update_manager/node.py` inicia y detiene su propio daemon, intenta primero P2P y después gateways HTTPS, y valida que el CID descargado corresponda al archivo recibido.

## Criterio de éxito

```bash
which ipfs
ipfs version
```

Debe mostrarse `/usr/local/bin/ipfs` y la versión instalada.

Fuente oficial: https://docs.ipfs.tech/install/command-line/
