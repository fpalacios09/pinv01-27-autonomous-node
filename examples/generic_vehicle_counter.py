#!/usr/bin/env python3
"""Contador genérico por cruce de línea para validar Ultralytics en Jetson."""
from __future__ import annotations

import argparse
from collections import defaultdict

import cv2
import torch
from ultralytics import YOLO

VEHICLE_CLASSES = {2: 'car', 3: 'motorcycle', 5: 'bus', 7: 'truck'}


def parse_source(value: str):
    return int(value) if value.isdigit() else value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', default='0', help='Webcam, video o URL RTSP')
    parser.add_argument('--model', default='yolo26n.pt')
    parser.add_argument('--line-ratio', type=float, default=2 / 3)
    parser.add_argument('--conf', type=float, default=0.4)
    parser.add_argument('--show', action='store_true')
    args = parser.parse_args()

    if not 0 < args.line_ratio < 1:
        parser.error('--line-ratio debe estar entre 0 y 1')
    if not torch.cuda.is_available():
        raise RuntimeError('PyTorch no detecta CUDA.')

    model = YOLO(args.model)
    previous_y: dict[int, int] = {}
    counted = {'to': defaultdict(set), 'from': defaultdict(set)}

    stream = model.track(source=parse_source(args.source), tracker='bytetrack.yaml',
                         stream=True, persist=True, device=0, conf=args.conf,
                         imgsz=640, verbose=False)

    for result in stream:
        frame = result.orig_img
        height, width = frame.shape[:2]
        line_y = int(height * args.line_ratio)
        cv2.line(frame, (0, line_y), (width, line_y), (0, 0, 255), 2)

        if result.boxes is not None:
            for box in result.boxes:
                class_id = int(box.cls[0].item())
                if class_id not in VEHICLE_CLASSES or box.id is None:
                    continue
                track_id = int(box.id[0].item())
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                center_y = (y1 + y2) // 2
                previous = previous_y.get(track_id)
                name = VEHICLE_CLASSES[class_id]
                if previous is not None:
                    if previous < line_y <= center_y:
                        counted['to'][name].add(track_id)
                    elif previous > line_y >= center_y:
                        counted['from'][name].add(track_id)
                previous_y[track_id] = center_y
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

        print('TO:', {k: len(v) for k, v in counted['to'].items()},
              '| FROM:', {k: len(v) for k, v in counted['from'].items()})

        if args.show:
            cv2.imshow('PINV01-27 generic counter', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    if args.show:
        cv2.destroyAllWindows()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
