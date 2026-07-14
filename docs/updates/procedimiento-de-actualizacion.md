# Procedimiento para realizar actualizaciones remotas

Este documento describe el procedimiento para preparar, enviar y verificar actualizaciones remotas del nodo autónomo **PINV01-27** mediante IPFS y LoRa.

---

## 1. Estructura obligatoria del paquete de actualización

Cada actualización debe organizarse dentro de una carpeta raíz con un nombre identificable, por ejemplo:

```text
update_00X/
├── arduino/
│   ├── readme.txt
│   └── sketch.ino.bin
├── python/
│   ├── readme.txt
│   ├── script.py
│   └── best.pt
└── readme.txt
```

Donde:

- `update_00X/`: carpeta raíz del paquete.
- `arduino/readme.txt`: debe contener únicamente `true` o `false`.
  - `true`: existe una actualización para el microcontrolador.
  - `false`: no se actualizará el microcontrolador.
- `arduino/sketch.ino.bin`: firmware compilado para el Arduino o Nano ESP32.
- `python/readme.txt`: debe contener únicamente `true` o `false`.
  - `true`: existe una actualización para el código Python.
  - `false`: no se actualizará el código Python.
- `python/script.py`: archivo Python que será ejecutado por el nodo. El nombre `script.py` es obligatorio.
- `python/best.pt`: pesos del modelo YOLO utilizados por el nuevo script.
- `readme.txt`: información general sobre la actualización, cambios realizados, versión y observaciones.

> [!IMPORTANT]
> Los archivos `arduino/readme.txt` y `python/readme.txt` deben contener solamente `true` o `false`, sin comentarios ni texto adicional.

---

## 2. Preparación del archivo comprimido

La carpeta raíz debe comprimirse en formato:

- `.tar`
- `.tar.gz`

Ejemplo:

```text
update_001.tar
```

o:

```text
update_001.tar.gz
```

### Crear un archivo `.tar` en Linux

```bash
tar -cvf update_001.tar update_001/
```

### Crear un archivo `.tar.gz` en Linux

```bash
tar -czvf update_001.tar.gz update_001/
```

### Verificar el contenido antes de enviarlo

Para un archivo `.tar`:

```bash
tar -tvf update_001.tar
```

Para un archivo `.tar.gz`:

```bash
tar -tzvf update_001.tar.gz
```

La estructura mostrada debe coincidir con la definida en la sección anterior.

---

## 3. Envío de la actualización

Una vez creado el archivo comprimido:

1. Abrir la interfaz gráfica **PINV01-27 Update Center**.
2. Iniciar el daemon de IPFS.
3. Seleccionar el archivo `.tar` o `.tar.gz`.
4. Presionar el botón para enviar la actualización.
5. Verificar que la aplicación muestre el CID generado por IPFS.
6. Confirmar que el CID sea transmitido al nodo remoto mediante LoRa.

El nodo Jetson recibirá el CID por UART, descargará el paquete desde IPFS, verificará su integridad y procesará las carpetas `python/` y `arduino/` según el contenido de sus respectivos archivos `readme.txt`.

---

## 4. Seguimiento de la actualización

Después de enviar el paquete:

1. Esperar aproximadamente entre **15 y 20 minutos**, según el intervalo configurado para la comunicación LoRa.
2. Abrir la pestaña de recepción de datos en **PINV01-27 Update Center**.
3. Presionar **Listen**.
4. Esperar la llegada de datos desde el nodo.
5. Revisar los mensajes recibidos para confirmar que el sistema volvió a operar correctamente.

Para guardar los datos en un nuevo archivo CSV:

1. Cambiar el nombre del archivo.
2. Aplicar el cambio antes de iniciar la escucha.

Si no se cambia el nombre, los nuevos datos se agregarán al archivo CSV actual.

Los archivos CSV se guardan en la carpeta:

```text
internal/
```

---

## 5. Tipos de actualización

### 5.1 Actualización exclusiva de Python

Configurar:

```text
arduino/readme.txt = false
python/readme.txt  = true
```

La carpeta `python/` debe contener como mínimo:

```text
python/
├── readme.txt
├── script.py
└── best.pt
```

### 5.2 Actualización exclusiva del microcontrolador

Configurar:

```text
arduino/readme.txt = true
python/readme.txt  = false
```

La carpeta `arduino/` debe contener:

```text
arduino/
├── readme.txt
└── sketch.ino.bin
```

### 5.3 Actualización conjunta

Aunque el sistema puede procesar ambas carpetas, se recomienda evitar la actualización simultánea de Python y Arduino durante las pruebas iniciales o en despliegues críticos.

Configurar:

```text
arduino/readme.txt = true
python/readme.txt  = true
```

---

## 6. Recomendaciones operativas

- Enviar una sola actualización a la vez.
- Evitar actualizar simultáneamente el firmware y el código Python, salvo que sea estrictamente necesario.
- No enviar comandos de control, como reinicio de la Jetson o activación de la cámara, mientras se procesa una actualización.
- Incluir siempre los pesos de YOLO requeridos por el nuevo `script.py`.
- Probar el paquete completo en laboratorio antes de enviarlo al nodo desplegado.
- Verificar que el nuevo script funcione correctamente en el mismo entorno Conda utilizado por el servicio.
- Confirmar que las rutas `/dev/mcu` y `/dev/adapter` existan antes de probar la actualización.
- No modificar el nombre obligatorio `script.py`.
- No modificar manualmente el CID después de generado.
- Mantener una copia local del último paquete funcional.
- Registrar en el `readme.txt` de la carpeta raíz la versión, fecha y cambios incluidos.

---

## 7. Detención temporal del código en ejecución

Cuando sea necesario reemplazar temporalmente el algoritmo principal, puede enviarse un `script.py` mínimo que permanezca en ejecución sin abrir una interfaz gráfica.

Ejemplo:

```python
import time

print("Script temporal activo. El procesamiento principal está detenido.")

try:
    while True:
        time.sleep(60)
except KeyboardInterrupt:
    print("Script temporal finalizado.")
```

Este método permite reemplazar el código actual sin depender de una ventana de OpenCV.

---

## 8. Ejemplo de `readme.txt` general

El archivo `readme.txt` de la carpeta raíz puede tener un contenido similar a:

```text
Proyecto: PINV01-27
Actualización: update_001
Fecha: 2026-07-14
Responsable: Equipo PINV01-27

Cambios:
- Se actualizó el algoritmo de conteo bidireccional.
- Se incorporó una nueva versión de los pesos YOLO.
- No se actualizó el firmware del microcontrolador.

Validación:
- Probado en Jetson Orin Nano.
- Comunicación UART verificada.
- Inferencia CUDA verificada.
```

Este archivo es informativo y no controla la ejecución de la actualización.

---

## 9. Verificación previa al envío

Antes de enviar el paquete, comprobar:

- [ ] La estructura de carpetas es correcta.
- [ ] Los archivos `readme.txt` de `arduino/` y `python/` contienen únicamente `true` o `false`.
- [ ] El archivo Python se llama exactamente `script.py`.
- [ ] El firmware compilado utiliza la extensión `.ino.bin`.
- [ ] Los pesos YOLO requeridos están incluidos.
- [ ] El archivo `.tar` o `.tar.gz` puede abrirse correctamente.
- [ ] El nuevo código fue probado en laboratorio.
- [ ] No existen credenciales, contraseñas o tokens escritos directamente en el código.
- [ ] El nodo tiene conectividad a internet para descargar desde IPFS.
- [ ] No se enviarán otros comandos durante la actualización.

---

## 10. Verificación posterior

Después de la actualización:

- [ ] La Jetson descargó y validó el paquete.
- [ ] El archivo comprimido se descomprimió correctamente.
- [ ] El nuevo `script.py` está en ejecución.
- [ ] El modelo YOLO se cargó sin errores.
- [ ] CUDA está disponible.
- [ ] La comunicación UART funciona.
- [ ] Los conteos vuelven a recibirse mediante LoRa.
- [ ] Los datos se registran correctamente en el archivo CSV o plataforma remota.
- [ ] No existen reinicios repetitivos del servicio `systemd`.

Para revisar el servicio:

```bash
sudo systemctl status pinv0127.service
```

Para consultar los últimos registros:

```bash
journalctl -u pinv0127.service -n 100 --no-pager
```

Para seguir los registros en tiempo real:

```bash
journalctl -u pinv0127.service -f
```
