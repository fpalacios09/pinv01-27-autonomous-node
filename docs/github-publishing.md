# Publicar el repositorio en GitHub

Antes de publicar, revisar `SECURITY.md`, elegir una licencia y sustituir la URL del repositorio de la Raspberry Pi.

## Con GitHub CLI

```bash
cd pinv01-27-autonomous-node
git add .
git commit -m "Initial reproducible Jetson setup"
gh repo create pinv01-27-autonomous-node --public --source=. --remote=origin --push
```

## Con un repositorio creado desde la web

```bash
cd pinv01-27-autonomous-node
git branch -M main
git remote add origin https://github.com/USUARIO/pinv01-27-autonomous-node.git
git push -u origin main
```

No copiar contraseñas RTSP ni `firmware/host_mcu/lora/config.h` al repositorio.
