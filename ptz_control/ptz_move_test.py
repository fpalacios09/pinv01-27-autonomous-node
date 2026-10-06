#!/usr/bin/env python3
import os,sys,time
from onvif import ONVIFCamera

def req(n):
    v=os.getenv(n)
    if not v: print(f"[ERROR] Falta {n}"); sys.exit(1)
    return v
IP=req("PTZ_IP"); PORT=int(os.getenv("PTZ_PORT","80")); USER=req("PTZ_USER"); PASSWORD=req("PTZ_PASSWORD")
SPEED=float(os.getenv("PTZ_MOVE_SPEED","0.20")); MOVE_TIME=float(os.getenv("PTZ_MOVE_TIME","0.20"))
camera=ONVIFCamera(IP,PORT,USER,PASSWORD); media=camera.create_media_service(); ptz=camera.create_ptz_service(); profiles=media.GetProfiles(); token=profiles[0].token
def stop():
    r=ptz.create_type("Stop"); r.ProfileToken=token; r.PanTilt=True; r.Zoom=True; ptz.Stop(r)
def move(x=0,y=0,zoom=0):
    r=ptz.create_type("ContinuousMove"); r.ProfileToken=token; vel={}
    if x or y: vel["PanTilt"]={"x":x,"y":y}
    if zoom: vel["Zoom"]={"x":zoom}
    r.Velocity=vel; ptz.ContinuousMove(r); time.sleep(MOVE_TIME); stop()
print(f"[INFO] Movimiento de prueba: derecha, {MOVE_TIME:.2f} s")
try:
    move(x=SPEED); print("[OK] Movimiento finalizado.")
finally:
    try: stop()
    except Exception: pass
