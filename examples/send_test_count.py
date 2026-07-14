#!/usr/bin/env python3
"""Envía un JSON de conteo sintético al Host MCU."""
from __future__ import annotations

import argparse
import json
import time

import serial


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', default='/dev/mcu')
    parser.add_argument('--baudrate', type=int, default=115200)
    parser.add_argument('--repeat', type=int, default=1)
    parser.add_argument('--delay', type=float, default=2.0)
    args = parser.parse_args()

    payload = {
        'stream_key': 'carbikebustruck',
        'car_to_sl': 1, 'bike_to_sl': 0, 'heavy_to_sl': 1, 'total_to_sl': 2,
        'car_from_sl': 0, 'bike_from_sl': 1, 'heavy_from_sl': 0, 'total_from_sl': 1,
    }
    message = json.dumps(payload, separators=(',', ':')) + '\n'

    with serial.Serial(args.port, args.baudrate, timeout=1) as ser:
        for index in range(args.repeat):
            ser.write(message.encode('utf-8'))
            ser.flush()
            print(f'[{index + 1}/{args.repeat}] Enviado: {message.strip()}')
            if index + 1 < args.repeat:
                time.sleep(args.delay)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
