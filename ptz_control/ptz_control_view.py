#!/usr/bin/env python3
import os,sys,time
from urllib.parse import quote
from onvif import ONVIFCamera
try: import cv2
except ImportError:
    print("[ERROR] cv2 no disponible en entorno onvif; usa ./run_control.sh"); sys.exit(1)
def req(n):
    v=os.getenv(n)
    if not v: print(f"[ERROR] Falta {n}"); sys.exit(1)
    return v
IP=req("PTZ_IP"); PORT=int(os.getenv("PTZ_PORT","80")); USER=req("PTZ_USER"); PASSWORD=req("PTZ_PASSWORD"); PATH=os.getenv("PTZ_RTSP_PATH","/Stream")
SPEED=float(os.getenv("PTZ_MOVE_SPEED","0.25")); MOVE_TIME=float(os.getenv("PTZ_MOVE_TIME","0.20")); W=int(os.getenv("PTZ_DISPLAY_WIDTH","640")); H=int(os.getenv("PTZ_DISPLAY_HEIGHT","360"))
URL=f"rtsp://{quote(USER,safe='')}:{quote(PASSWORD,safe='')}@{IP}:554{PATH}"
camera=ONVIFCamera(IP,PORT,USER,PASSWORD); media=camera.create_media_service(); ptz=camera.create_ptz_service(); profiles=media.GetProfiles(); token=profiles[0].token
def stop():
    r=ptz.create_type("Stop"); r.ProfileToken=token; r.PanTilt=True; r.Zoom=True; ptz.Stop(r)
def move(x=0,y=0,zoom=0):
    r=ptz.create_type("ContinuousMove"); r.ProfileToken=token; vel={}
    if x or y: vel["PanTilt"]={"x":x,"y":y}
    if zoom: vel["Zoom"]={"x":zoom}
    r.Velocity=vel; ptz.ContinuousMove(r); time.sleep(MOVE_TIME); stop()
cap=cv2.VideoCapture(URL)
if not cap.isOpened(): print("[ERROR] No se pudo abrir RTSP"); sys.exit(1)
try:
    while True:
        ok,frame=cap.read()
        if not ok: continue
        view=cv2.resize(frame,(W,H)); cv2.imshow("PINV01-27 - PTZ Control",view); k=cv2.waitKey(1)&0xFF
        if k==ord('w'): move(y=SPEED)
        elif k==ord('s'): move(y=-SPEED)
        elif k==ord('a'): move(x=-SPEED)
        elif k==ord('d'): move(x=SPEED)
        elif k in (ord('+'),ord('=')): move(zoom=SPEED)
        elif k==ord('-'): move(zoom=-SPEED)
        elif k in (ord('q'),27): break
finally:
    try: stop()
    except Exception: pass
    cap.release(); cv2.destroyAllWindows()
