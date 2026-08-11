# Integración del router 4G con Raspberry Pi

El nodo autónomo PINV01-27 utiliza una Raspberry Pi con un módem 4G para proporcionar conectividad a Internet a la NVIDIA Jetson.

La configuración completa de la Raspberry Pi se mantiene en un repositorio independiente:

- [Raspberry Pi 4G Router](https://github.com/fpalacios09/raspberry-4g-router)

## Función dentro de la arquitectura PINV01-27

La Raspberry Pi actúa como gateway de Internet para la Jetson. Sus principales responsabilidades son:

- Establecer la conexión 4G mediante el módem celular.
- Compartir la conexión a Internet con la Jetson.
- Proporcionar conectividad para la descarga de actualizaciones mediante IPFS.
- Permitir que la Jetson permanezca independiente de una red cableada permanente.

## Secuencia de integración recomendada

1. Configurar y validar el router Raspberry Pi siguiendo las instrucciones del repositorio dedicado.
2. Conectar la Raspberry Pi y la Jetson mediante la interfaz de red seleccionada.
3. Verificar que la Jetson reciba una dirección IP.
4. Confirmar la conectividad a Internet desde la Jetson:

```bash
ping -c 4 1.1.1.1
```

5. Confirmar la resolución DNS:

```bash
ping -c 4 github.com
```

6. Verificar la conectividad de IPFS:

```bash
ipfs swarm peers
```

7. Probar el acceso a un objeto IPFS:

```bash
ipfs cat <CID>
```

## Criterios de validación

La integración del router se considera operativa cuando:

- La Jetson tiene una dirección IP.
- La Jetson puede acceder a Internet.
- La resolución DNS funciona.
- El daemon de IPFS puede conectarse a peers.
- El gestor de actualizaciones puede descargar y verificar un paquete de actualización.

## Repositorio relacionado

URL del repositorio:

```text
https://github.com/fpalacios09/raspberry-4g-router
```
