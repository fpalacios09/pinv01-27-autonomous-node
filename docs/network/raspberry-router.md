# Raspberry Pi como router 4G

La configuración de la Raspberry Pi y del módem 4G se mantiene en un repositorio independiente.

## Repositorio externo

Reemplazar antes de publicar:

```text
https://github.com/ORGANIZACION/REPOSITORIO-ROUTER-4G
```

## Validación desde la Jetson

```bash
ip route
ping -c 3 1.1.1.1
curl -I https://ipfs.io
ipfs swarm peers | head
```
