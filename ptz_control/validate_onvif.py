#!/usr/bin/env python3
import os, sys
from onvif import ONVIFCamera

def req(n):
    v=os.getenv(n)
    if not v:
        print(f"[ERROR] Falta {n}"); sys.exit(1)
    return v

IP=req("PTZ_IP"); PORT=int(os.getenv("PTZ_PORT","80")); USER=req("PTZ_USER"); PASSWORD=req("PTZ_PASSWORD")
print("[INFO] Conectando a la cámara...")
try:
    camera=ONVIFCamera(IP,PORT,USER,PASSWORD)
    print("[OK] Conexión ONVIF establecida.")
    info=camera.create_devicemgmt_service().GetDeviceInformation()
    print("\n[INFO] Información de la cámara:")
    print(f"Manufacturer: {info.Manufacturer}")
    print(f"Model: {info.Model}")
    print(f"Firmware: {info.FirmwareVersion}")
    print(f"Serial: {info.SerialNumber}")
    profiles=camera.create_media_service().GetProfiles()
    print(f"\n[INFO] Perfiles encontrados: {len(profiles)}")
    for i,p in enumerate(profiles):
        print(f"  [{i}] Nombre: {p.Name}")
        print(f"      Token: {p.token}")
    camera.create_ptz_service()
    print("\n[OK] Servicio PTZ disponible.")
    print("[OK] Validación finalizada correctamente.")
except Exception as e:
    print("\n[ERROR] Falló la validación ONVIF:")
    print(e); sys.exit(1)
