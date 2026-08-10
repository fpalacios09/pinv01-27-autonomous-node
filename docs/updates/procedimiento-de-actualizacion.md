# Procedimiento para realizar actualizaciones remotas

Este documento describe el procedimiento para preparar, enviar y verificar actualizaciones remotas del nodo autónomo **PINV01-27** mediante IPFS y LoRa.

---

## 1. Estructura del paquete de actualización

Cada actualización debe organizarse dentro de una carpeta raíz con un nombre identificable, por ejemplo:

```text
update_00X/
├── arduino/
│   ├── readme.txt
│   └── sketch.ino.bin
├── python/
│   ├── readme.txt
│   ├── script.py
│   └── yolo26n.pt
└── readme.txt
```

Donde:

* `update_00X/`: carpeta raíz del paquete.
* `arduino/readme.txt`: debe contener únicamente `true` o `false`.

  * `true`: existe una actualización para el microcontrolador.
  * `false`: no se actualizará el microcontrolador.
* `arduino/sketch.ino.bin`: firmware compilado para el Arduino Nano ESP32.
* `python/readme.txt`: debe contener únicamente `true` o `false`.

  * `true`: existe una actualización para el código Python.
  * `false`: no se actualizará el código Python.
* `python/script.py`: archivo Python que será ejecutado por el nodo. El nombre `script.py` es obligatorio.
* `python/yolo26n.pt`: pesos del modelo YOLO utilizados por el script de actualización.
* `readme.txt`: archivo opcional con información general sobre la actualización, cambios realizados, versión y observaciones.

El nombre del archivo de pesos no tiene que ser necesariamente `yolo26n.pt`. Puede utilizarse otro nombre, siempre que el `script.py` incluido en la misma actualización utilice ese mismo nombre.

Por ejemplo:

```text
python/
├── readme.txt
├── script.py
└── modelo_v2.pt
```

En ese caso, `script.py` deberá cargar `modelo_v2.pt`.

> [!IMPORTANT]
> Los archivos `arduino/readme.txt` y `python/readme.txt` deben contener solamente `true` o `false`, sin comentarios ni texto adicional.

---

## 2. Preparación del archivo comprimido

La carpeta raíz puede comprimirse en formato:

* `.tar`
* `.tar.gz`

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

El nodo Jetson recibirá el CID por UART, descargará el paquete desde IPFS, verificará su integridad, descomprimirá el archivo y procesará las carpetas `python/` y `arduino/` según el contenido de sus respectivos archivos `readme.txt`.

Cuando `python/readme.txt` contiene:

```text
true
```

el nodo busca obligatoriamente:

```text
python/script.py
```

y ejecuta ese archivo.

Cuando llega una nueva actualización Python, el gestor de actualizaciones detiene el `script.py` anterior antes de iniciar el nuevo.

---

## 4. Formato del mensaje JSON de actualización y control

La información transmitida hacia el nodo utiliza un mensaje JSON con la siguiente estructura:

```json
{
  "command": "null",
  "hash": "Qmx..."
}
```

O

```json
{"command": "null","hash": "Qmx..."}
```

Los campos son:

| Campo     | Descripción                                              |
| --------- | -------------------------------------------------------- |
| `command` | Comando de control que debe ejecutar el nodo.            |
| `hash`    | CID de IPFS correspondiente al paquete de actualización. |

### 4.1 Envío de una actualización

Para enviar una actualización mediante IPFS, el campo `command` debe utilizar el valor:

```text
null
```

y el campo `hash` debe contener el CID generado por IPFS.

Ejemplo:

```json
{
  "command": "null",
  "hash": "Qmx..."
}
```

En este caso:

```text
command = null
        ↓
no se ejecuta un comando de control

hash = Qmx...
        ↓
CID del paquete de actualización
        ↓
descarga mediante IPFS
        ↓
verificación
        ↓
descompresión
        ↓
procesamiento del update
```

### 4.2 Comandos de control

El campo `command` puede utilizar los siguientes valores:

| Comando    | Función                                                                                                              |
| ---------- | -------------------------------------------------------------------------------------------------------------------- |
| `resetjet` | Reinicia la Jetson.                                                                                                  |
| `resetpi`  | Reinicia la Raspberry Pi.                                                                                            |
| `oncam`    | Enciende o habilita la cámara.                                                                                       |
| `offcam`   | Apaga o deshabilita la cámara.                                                                                       |
| `null`     | No ejecuta ningún comando de control; se utiliza para el envío normal de una actualización mediante el campo `hash`. |

Los comandos deben escribirse exactamente como se indican.

Ejemplo conceptual:

```json
{
  "command": "resetjet",
  "hash": "..."
}
```

Cuando se utiliza el sistema para enviar una actualización normal, debe utilizarse:

```json
{
  "command": "null",
  "hash": "CID_IPFS"
}
```

> [!IMPORTANT]
> No enviar comandos de control mientras se está procesando una actualización remota.

---

## 5. Seguimiento de la actualización

Después de enviar el paquete:

1. Verificar que el nodo remoto haya recibido el CID.
2. Confirmar que la Jetson haya descargado correctamente el paquete desde IPFS.
3. Verificar que el archivo haya sido descomprimido.
4. Confirmar que el nuevo `script.py` haya comenzado a ejecutarse.
5. Esperar aproximadamente entre **15 y 20 minutos**, según el intervalo configurado para el envío de datos.
6. Abrir Notehub.
7. Verificar que vuelvan a recibirse eventos con los datos generados por el nuevo código.

El tiempo de espera para visualizar nuevos eventos depende del intervalo configurado dentro del `script.py` y del flujo de comunicación con el Host MCU y Notehub.

---

## 6. Tipos de actualización

### 6.1 Actualización exclusiva de Python

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
└── yolo26n.pt
```

o los archivos adicionales requeridos por el nuevo `script.py`.

Por ejemplo:

```text
python/
├── readme.txt
├── script.py
└── modelo_v2.pt
```

El archivo de pesos debe coincidir con el modelo especificado dentro del propio `script.py`.

### 6.2 Actualización exclusiva del microcontrolador

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

### 6.3 Actualización conjunta

El sistema puede procesar actualizaciones de Python y Arduino dentro del mismo paquete:

```text
arduino/readme.txt = true
python/readme.txt  = true
```

Sin embargo, se recomienda evitar la actualización simultánea de Python y Arduino durante las pruebas iniciales o en despliegues críticos.

---

## 7. Recomendaciones operativas

* Enviar una sola actualización a la vez.
* Evitar actualizar simultáneamente el firmware y el código Python, salvo que sea estrictamente necesario.
* No enviar comandos de control mientras se procesa una actualización.
* Incluir siempre los pesos de YOLO requeridos por el nuevo `script.py`.
* Mantener los pesos del modelo dentro de la carpeta `python/` de la actualización.
* Asegurarse de que el nombre del modelo utilizado dentro de `script.py` coincida con el archivo `.pt` enviado.
* Probar el paquete completo en laboratorio antes de enviarlo al nodo desplegado.
* Verificar que el nuevo script funcione correctamente en el mismo entorno Conda utilizado por el servicio.
* Confirmar que las rutas `/dev/mcu` y `/dev/adapter` existan antes de probar la actualización.
* No modificar el nombre obligatorio `script.py`.
* No modificar manualmente el CID después de generado.
* Mantener una copia local del último paquete funcional.
* Registrar en el `readme.txt` de la carpeta raíz la versión, fecha y cambios incluidos.
* No incluir contraseñas, credenciales, claves privadas ni tokens dentro del paquete de actualización.

---

## 8. Reemplazo del código Python en ejecución

Cuando se recibe una nueva actualización Python con:

```text
python/readme.txt = true
```

el gestor de actualizaciones reemplaza el código Python que se encontraba ejecutándose.

El flujo es:

```text
nuevo update recibido
        ↓
python/readme.txt = true
        ↓
detección de python/script.py
        ↓
detención del script Python anterior
        ↓
ejecución del nuevo script.py
```

Por lo tanto, no es necesario detener manualmente el código anterior antes de enviar una nueva actualización.

Si se desea detener temporalmente el procesamiento principal sin iniciar otro algoritmo, puede enviarse un `script.py` mínimo que permanezca activo.

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

---

## 9. Ejemplo de `readme.txt` general

El archivo `readme.txt` de la carpeta raíz puede tener un contenido similar a:

```text
Proyecto: PINV01-27
Actualización: update_001
Fecha: 2026-08-10
Responsable: Equipo PINV01-27

Cambios:
- Se actualizó el algoritmo de conteo bidireccional.
- Se incorporó una nueva versión de los pesos YOLO.
- No se actualizó el firmware del microcontrolador.

Validación:
- Probado en Jetson Orin Nano.
- Comunicación UART verificada.
- Inferencia CUDA verificada.
- Descarga mediante IPFS verificada.
```

Este archivo es únicamente informativo y no controla la ejecución de la actualización.

Los archivos que sí controlan el procesamiento son:

```text
arduino/readme.txt
python/readme.txt
```

---

## 10. Verificación previa al envío

Antes de enviar el paquete, comprobar:

* [ ] La estructura de carpetas es correcta.
* [ ] Los archivos `readme.txt` de `arduino/` y `python/` contienen únicamente `true` o `false`.
* [ ] El archivo Python se llama exactamente `script.py`.
* [ ] El firmware compilado utiliza la extensión `.ino.bin`.
* [ ] Los pesos YOLO requeridos por `script.py` están incluidos.
* [ ] El nombre del archivo de pesos coincide con el utilizado dentro de `script.py`.
* [ ] El archivo `.tar` o `.tar.gz` puede abrirse correctamente.
* [ ] El nuevo código fue probado en laboratorio.
* [ ] No existen credenciales, contraseñas o tokens escritos directamente en el código.
* [ ] El nodo tiene conectividad a Internet para descargar desde IPFS.
* [ ] El CID generado corresponde al paquete que se desea enviar.
* [ ] Para una actualización normal, el mensaje utiliza `"command": "null"`.
* [ ] No se enviarán otros comandos durante la actualización.

---

## 11. Verificación posterior

Después de la actualización:

* [ ] La Jetson recibió el CID.
* [ ] La Jetson descargó y validó el paquete.
* [ ] El archivo comprimido se descomprimió correctamente.
* [ ] Se detectó correctamente la carpeta raíz del update.
* [ ] El nuevo `script.py` está en ejecución.
* [ ] El modelo YOLO se cargó sin errores.
* [ ] CUDA está disponible.
* [ ] La comunicación UART funciona.
* [ ] Los conteos vuelven a recibirse mediante LoRa.
* [ ] Los eventos aparecen correctamente en Notehub.
* [ ] No existen reinicios repetitivos del servicio `systemd`.

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

Los errores generados por el `script.py` ejecutado mediante una actualización pueden revisarse en el archivo:

```text
python_stderr.log
```

ubicado dentro de la carpeta `python/` correspondiente a la actualización descomprimida.

---

## 12. Flujo general de una actualización

```text
PINV01-27 Update Center
        ↓
archivo .tar / .tar.gz
        ↓
IPFS
        ↓
CID
        ↓
JSON
{"command":"null","hash":"Qmx..."}
        ↓
LoRa
        ↓
Host MCU
        ↓
UART /dev/adapter
        ↓
Jetson
        ↓
node.py
        ↓
descarga y verificación IPFS
        ↓
descompresión
        ↓
arduino/readme.txt
python/readme.txt
        ↓
procesamiento de la actualización
        ↓
nuevo firmware y/o script.py
```
