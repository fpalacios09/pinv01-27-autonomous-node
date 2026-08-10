\# 10. OpenVPN



La Jetson puede conectarse automáticamente a una VPN mediante OpenVPN

al iniciar el sistema.



La configuración real `.ovpn` no se almacena en el repositorio porque

puede contener credenciales, certificados, claves privadas y datos de

la infraestructura de red.



\## Instalar OpenVPN



```bash

sudo apt update

sudo apt install -y openvpn

```



Verificar:



```bash

openvpn --version

```



\## Probar la VPN manualmente



Antes de instalar el servicio se recomienda comprobar que el archivo

`.ovpn` funciona correctamente.



```bash

sudo openvpn --config /ruta/al/archivo.ovpn

```



Ejemplo:



```bash

sudo openvpn --config \\

/home/orin/Desktop/pinv0127/pfSense-UDP4-1194-Torre1-config.ovpn

```



Si la conexión se establece correctamente, finalizar la prueba con:



```text

Ctrl+C

```



\## Instalar el servicio



Desde la raíz del repositorio:



```bash

bash scripts/install/install\_openvpn\_service.sh \\

/ruta/al/archivo.ovpn

```



Ejemplo:



```bash

bash scripts/install/install\_openvpn\_service.sh \\

/home/orin/Desktop/pinv0127/pfSense-UDP4-1194-Torre1-config.ovpn

```



El instalador copia la configuración privada a:



```text

/etc/pinv0127/vpn/client.ovpn

```



con permisos `0600`.



El directorio:



```text

/etc/pinv0127/vpn/

```



se crea con permisos `0700`.



También se instala:



```text

/etc/systemd/system/pinv0127-vpn.service

```



y el servicio queda habilitado automáticamente para iniciar con la Jetson.



\## Verificar el servicio



```bash

systemctl is-enabled pinv0127-vpn.service

systemctl is-active pinv0127-vpn.service

```



Los resultados esperados son:



```text

enabled

active

```



Ver información completa:



```bash

sudo systemctl status pinv0127-vpn.service

```



\## Logs



Últimos registros:



```bash

journalctl -u pinv0127-vpn.service -n 100 --no-pager

```



Logs en tiempo real:



```bash

journalctl -u pinv0127-vpn.service -f

```



\## Verificar la interfaz VPN



```bash

ip addr

```



Normalmente OpenVPN crea una interfaz:



```text

tun0

```



Puede verificarse directamente:



```bash

ip addr show tun0

```



También pueden comprobarse las rutas:



```bash

ip route

```



\## Reiniciar la VPN



```bash

sudo systemctl restart pinv0127-vpn.service

```



\## Detener la VPN



```bash

sudo systemctl stop pinv0127-vpn.service

```



\## Deshabilitar el inicio automático



```bash

sudo systemctl disable --now pinv0127-vpn.service

```



\## Sustituir la configuración VPN



Para instalar un nuevo archivo puede volver a ejecutarse:



```bash

bash scripts/install/install\_openvpn\_service.sh \\

/ruta/al/nuevo-archivo.ovpn

```



\## Verificación después de reiniciar



Reiniciar:



```bash

sudo reboot

```



Después:



```bash

systemctl is-enabled pinv0127-vpn.service

systemctl is-active pinv0127-vpn.service

```



Los resultados esperados son:



```text

enabled

active

```



\## Seguridad



Los archivos `.ovpn` no deben almacenarse en GitHub.



Un archivo OVPN puede contener:



\- certificados;

\- claves privadas;

\- direcciones IP;

\- nombres de servidores;

\- credenciales;

\- configuración interna de la VPN.



Se recomienda utilizar archivos `.ovpn` autocontenidos.



Si el archivo hace referencia a certificados, claves o archivos de

credenciales externos, estos también deberán copiarse de manera segura

a `/etc/pinv0127/vpn/`.

