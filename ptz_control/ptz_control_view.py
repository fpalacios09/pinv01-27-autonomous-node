#!/usr/bin/env python3
import os
import sys
import time
from urllib.parse import quote
from onvif import ONVIFCamera

try:
    import cv2
except ImportError:
    print("[ERROR] cv2 no disponible en entorno onvif; usa ./run_control.sh")
    sys.exit(1)


def req(name):
    value = os.getenv(name)
    if not value:
        print(f"[ERROR] Falta {name}")
        sys.exit(1)
    return value


IP = req("PTZ_IP")
PORT = int(os.getenv("PTZ_PORT", "80"))
USER = req("PTZ_USER")
PASSWORD = req("PTZ_PASSWORD")
PATH = os.getenv("PTZ_RTSP_PATH", "/Stream")

SPEED = float(os.getenv("PTZ_MOVE_SPEED", "0.25"))
MOVE_TIME = float(os.getenv("PTZ_MOVE_TIME", "0.20"))
W = int(os.getenv("PTZ_DISPLAY_WIDTH", "640"))
H = int(os.getenv("PTZ_DISPLAY_HEIGHT", "360"))

URL = (
    f"rtsp://{quote(USER, safe='')}:{quote(PASSWORD, safe='')}"
    f"@{IP}:554{PATH}"
)

camera = ONVIFCamera(IP, PORT, USER, PASSWORD)
media = camera.create_media_service()
ptz = camera.create_ptz_service()
profiles = media.GetProfiles()
token = profiles[0].token


def stop():
    request = ptz.create_type("Stop")
    request.ProfileToken = token
    request.PanTilt = True
    request.Zoom = True
    ptz.Stop(request)


def move(x=0, y=0, zoom=0):
    request = ptz.create_type("ContinuousMove")
    request.ProfileToken = token
    velocity = {}

    if x or y:
        velocity["PanTilt"] = {"x": x, "y": y}
    if zoom:
        velocity["Zoom"] = {"x": zoom}

    request.Velocity = velocity
    ptz.ContinuousMove(request)
    time.sleep(MOVE_TIME)
    stop()


def set_home():
    """Guarda la posición actual como Home en la cámara."""
    try:
        stop()
        request = ptz.create_type("SetHomePosition")
        request.ProfileToken = token
        ptz.SetHomePosition(request)
        print("[OK] Posición actual guardada como HOME.")
    except Exception as error:
        print(f"[ERROR] No se pudo guardar HOME: {error}")


def goto_home():
    """Mueve la cámara a la posición Home guardada."""
    try:
        stop()
        request = ptz.create_type("GotoHomePosition")
        request.ProfileToken = token
        ptz.GotoHomePosition(request)
        print("[OK] Comando enviado: ir a HOME.")
    except Exception as error:
        print(f"[ERROR] No se pudo ir a HOME: {error}")


cap = cv2.VideoCapture(URL)
if not cap.isOpened():
    print("[ERROR] No se pudo abrir RTSP")
    cap.release()
    sys.exit(1)

print(
    "w=arriba s=abajo a=izquierda d=derecha "
    "+=zoom in -=zoom out "
    "h=guardar HOME g=ir a HOME q/ESC=salir"
)
print("Presioná las teclas con la ventana de video seleccionada.")

# Al iniciar no se envía ningún comando de movimiento.
try:
    while True:
        ok, frame = cap.read()
        if ok:
            view = cv2.resize(frame, (W, H))
            cv2.imshow("PINV01-27 - PTZ Control", view)

        k = cv2.waitKey(1) & 0xFF

        if k == ord("w"):
            move(y=SPEED)
        elif k == ord("s"):
            move(y=-SPEED)
        elif k == ord("a"):
            move(x=-SPEED)
        elif k == ord("d"):
            move(x=SPEED)
        elif k in (ord("+"), ord("=")):
            move(zoom=SPEED)
        elif k == ord("-"):
            move(zoom=-SPEED)
        elif k in (ord("h"), ord("H")):
            set_home()
        elif k in (ord("g"), ord("G")):
            goto_home()
        elif k in (ord("q"), ord("Q"), 27):
            break
except KeyboardInterrupt:
    pass
finally:
    try:
        stop()
    except Exception:
        pass
    cap.release()
    cv2.destroyAllWindows()
