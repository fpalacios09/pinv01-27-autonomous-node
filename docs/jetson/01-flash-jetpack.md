# 1. Flashear JetPack

## Objetivo

Instalar JetPack 5.1.3 en la Jetson Orin Nano utilizada como plataforma de referencia.

## Métodos admitidos

Para un Developer Kit oficial pueden utilizarse la imagen de SD correspondiente o NVIDIA SDK Manager. Para módulos o carriers de terceros, seguir el método indicado por el fabricante.

Documentación oficial:

- JetPack 5.1.3: https://developer.nvidia.com/embedded/jetpack-sdk-513
- Archivo de versiones JetPack: https://developer.nvidia.com/embedded/jetpack-archive

## Después del primer arranque

```bash
sudo apt update
sudo apt full-upgrade -y
sudo reboot
```

Verificar:

```bash
cat /etc/nv_tegra_release
lsb_release -a
```

Salida esperada para la referencia: L4T `35.5.0` y Ubuntu `20.04`.

## Criterio de éxito

La Jetson arranca normalmente, tiene acceso a una terminal y reporta la versión de L4T/JetPack esperada.
