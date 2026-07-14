#!/usr/bin/env python3
"""Verifica PyTorch CUDA y una inferencia mínima de Ultralytics."""
from __future__ import annotations

import argparse
import platform
import sys
from pathlib import Path

import numpy as np


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', default='yolo26n.pt')
    parser.add_argument('--output-dir', default='runs/verification')
    args = parser.parse_args()

    print('Python:', sys.version.replace('\n', ' '))
    print('Arquitectura:', platform.machine())
    print('Sistema:', platform.platform())

    try:
        import torch
    except Exception as exc:
        print(f'[ERROR] No se pudo importar torch: {exc}')
        return 2

    print('Torch:', torch.__version__)
    print('Torch CUDA:', torch.version.cuda)
    print('CUDA disponible:', torch.cuda.is_available())
    if not torch.cuda.is_available():
        print('[ERROR] PyTorch no tiene CUDA. Revise el wheel instalado.')
        return 3

    print('GPU:', torch.cuda.get_device_name(0))

    try:
        import cv2
        import ultralytics
        from ultralytics import YOLO
    except Exception as exc:
        print(f'[ERROR] No se pudo importar Ultralytics/OpenCV: {exc}')
        return 4

    print('Ultralytics:', ultralytics.__version__)
    print('OpenCV:', cv2.__version__)
    print('Dispositivos CUDA en OpenCV:', cv2.cuda.getCudaEnabledDeviceCount())

    image = np.zeros((640, 640, 3), dtype=np.uint8)
    cv2.rectangle(image, (160, 220), (480, 430), (255, 255, 255), -1)
    cv2.putText(image, 'PINV01-27 CUDA TEST', (95, 100), cv2.FONT_HERSHEY_SIMPLEX,
                1.0, (255, 255, 255), 2, cv2.LINE_AA)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    model = YOLO(args.model)
    results = model.predict(source=image, device=0, imgsz=640, verbose=False)
    output_path = output_dir / 'verification_result.jpg'
    if not cv2.imwrite(str(output_path), results[0].plot()):
        return 5

    print('[OK] Inferencia ejecutada en CUDA.')
    print('[OK] Resultado:', output_path.resolve())
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
