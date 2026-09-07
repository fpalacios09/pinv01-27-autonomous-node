#!/usr/bin/env python3
"""Contador genérico por cruce de línea para validar Ultralytics en Jetson."""

import os
import sys
import cv2
import time
from ultralytics import YOLO


# =========================================================
# CONFIGURACIÓN
# =========================================================

def startup_countdown(seconds=5):
    print("Iniciando", end="", flush=True)

    for _ in range(seconds):
        time.sleep(1)
        print(".", end="", flush=True)

    print("\n")

# =========================================================

startup_countdown(5)

model = YOLO(MODEL_PATH)

MODEL_PATH = "yolo11n.pt"

# Cámara local:
# VIDEO_SOURCE = 0

# Archivo de video:
# VIDEO_SOURCE = "video.mp4"

# Cámara RTSP:
# VIDEO_SOURCE = "rtsp://usuario:password@IP:554/Stream"

VIDEO_SOURCE = ""

SHOW_GUI = True

CONF = 0.4
IOU = 0.5
LINE_POSITION_RATIO = 2 / 3

# Clases COCO de vehículos
CLASS_MAP = {
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck"
}


# =========================================================
# VALIDACIONES
# =========================================================

# Verificar pesos YOLO
if not os.path.isfile(MODEL_PATH):
    print(
        "\nError: No se encontraron los pesos pre-entrenados de YOLO para la prueba."
    )
    print(
        "Descargue los pesos pre-trained correspondientes al dataset COCO "
        "y vuelva a ejecutar el programa."
    )
    print(f"Ruta esperada: {MODEL_PATH}\n")
    sys.exit(1)


# Verificar que VIDEO_SOURCE no esté vacío
if VIDEO_SOURCE is None or (
    isinstance(VIDEO_SOURCE, str) and not VIDEO_SOURCE.strip()
):
    print(
        "\nError: La ruta o fuente de video es inválida o inexistente."
    )
    print(
        "Ingrese una ruta de video, cámara o stream RTSP válida "
        "y vuelva a ejecutar el programa.\n"
    )
    sys.exit(1)


# Convertir "0" -> 0 si se escribió la cámara como texto
if isinstance(VIDEO_SOURCE, str) and VIDEO_SOURCE.isdigit():
    VIDEO_SOURCE = int(VIDEO_SOURCE)


# Verificar que la fuente pueda abrirse y entregar un frame
cap = cv2.VideoCapture(VIDEO_SOURCE)

if not cap.isOpened():
    print(
        "\nError: La ruta o fuente de video es inválida o inexistente."
    )
    print(
        "Ingrese una ruta de video, cámara o stream RTSP válida "
        "y vuelva a ejecutar el programa.\n"
    )
    cap.release()
    sys.exit(1)

ok, frame_test = cap.read()
cap.release()

if not ok or frame_test is None:
    print(
        "\nError: No se pudo obtener imagen desde la fuente de video."
    )
    print(
        "Ingrese una ruta de video, cámara o stream RTSP válida "
        "y vuelva a ejecutar el programa.\n"
    )
    sys.exit(1)


# =========================================================
# MODELO
# =========================================================

model = YOLO(MODEL_PATH)

counts = {
    "car": 0,
    "motorcycle": 0,
    "bus": 0,
    "truck": 0
}

# Guarda la posición Y anterior de cada track
previous_y = {}

# Evita contar dos veces el mismo vehículo
counted_ids = set()


# =========================================================
# TRACKING
# =========================================================

results = model.track(
    source=VIDEO_SOURCE,
    tracker="bytetrack.yaml",
    classes=list(CLASS_MAP.keys()),
    conf=CONF,
    iou=IOU,
    imgsz=640,
    persist=True,
    stream=True,
    verbose=False
)


for result in results:

    frame = result.orig_img
    height, width = frame.shape[:2]

    line_y = int(height * LINE_POSITION_RATIO)

    # -----------------------------------------------------
    # Procesar detecciones
    # -----------------------------------------------------

    if result.boxes is not None:

        for box in result.boxes:

            if box.id is None:
                continue

            track_id = int(box.id[0])
            class_id = int(box.cls[0])

            if class_id not in CLASS_MAP:
                continue

            class_name = CLASS_MAP[class_id]

            x1, y1, x2, y2 = map(int, box.xyxy[0])

            xc = (x1 + x2) // 2
            yc = (y1 + y2) // 2

            # -------------------------------------------------
            # Detectar cruce de línea
            # -------------------------------------------------

            if track_id in previous_y:

                old_y = previous_y[track_id]

                crossed_down = old_y < line_y and yc >= line_y
                crossed_up = old_y > line_y and yc <= line_y

                if (
                    (crossed_down or crossed_up)
                    and track_id not in counted_ids
                ):

                    counted_ids.add(track_id)
                    counts[class_name] += 1

                    print(
                        f"{class_name} | "
                        f"car:{counts['car']} "
                        f"motorcycle:{counts['motorcycle']} "
                        f"bus:{counts['bus']} "
                        f"truck:{counts['truck']} "
                        f"TOTAL:{sum(counts.values())}"
                    )

            previous_y[track_id] = yc

            # -------------------------------------------------
            # Dibujar detección
            # -------------------------------------------------

            if SHOW_GUI:

                cv2.rectangle(
                    frame,
                    (x1, y1),
                    (x2, y2),
                    (0, 255, 0),
                    2
                )

                cv2.putText(
                    frame,
                    f"{class_name} ID:{track_id}",
                    (x1, max(20, y1 - 10)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 255, 255),
                    2
                )

    # -----------------------------------------------------
    # Ventana
    # -----------------------------------------------------

    if SHOW_GUI:

        cv2.line(
            frame,
            (0, line_y),
            (width, line_y),
            (0, 0, 255),
            3
        )

        total = sum(counts.values())

        text = (
            f"Car:{counts['car']}  "
            f"Moto:{counts['motorcycle']}  "
            f"Bus:{counts['bus']}  "
            f"Truck:{counts['truck']}  "
            f"Total:{total}"
        )

        cv2.putText(
            frame,
            text,
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 0),
            2
        )

        frame = cv2.resize(frame, (960, 540))

        cv2.imshow("YOLO Vehicle Counter", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break


if SHOW_GUI:
    cv2.destroyAllWindows()


# =========================================================
# RESULTADO FINAL
# =========================================================

print("\nConteo final:")
print(counts)
print("Total:", sum(counts.values()))