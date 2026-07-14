import os
import json
import serial
import serial.tools.list_ports
import time
from ultralytics import YOLO
import torch
import cv2
import numpy as np
import matplotlib.path as mlpPath
import signal
import sys

ser = None  # Variable global para poder cerrarla desde cualquier parte
startup_frame_saved = False  # Para guardar solo una vez el primer frame con ROI (no modificar)

# =========================================================
# CONFIGURACIÓN
# =========================================================

USE_FIXED_PORT = True          # True = usar alias fijo como /dev/mcu
FIXED_PORT = os.getenv("PINV_MCU_PORT", "/dev/mcu")
STREAM_KEY = os.getenv("PINV_STREAM_KEY", "carbikebustruck")  # Identificador del flujo

USE_ROI = False                 # True = activa ROI, False = cuenta en toda la imagen

# Conteo por cruce de línea horizontal
# LINE_POSITION_RATIO = 2/3 ubica la línea en el primer tercio desde abajo.
# Se cuentan ambos sentidos de cruce:
# - Arriba hacia abajo: to_sl
# - Abajo hacia arriba: from_sl
LINE_POSITION_RATIO = 2 / 3
COUNT_DIRECTION = "both"

INTERVAL = 900                   # segundos
MODEL_PATH = os.getenv("PINV_MODEL_PATH", "yolo26n.pt")
_video_source = os.getenv("PINV_VIDEO_SOURCE", "0")
VIDEO_PATH = int(_video_source) if _video_source.isdigit() else _video_source
SHOW_GUI = False               # True = muestra ventana, False = headless para servicio
SAVE_STARTUP_ROI_FRAME = True   # Guarda una sola imagen inicial con ROI
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DIAGNOSTIC_DIR = os.path.join(SCRIPT_DIR, "logs_node")
STARTUP_FRAME_PATH = os.path.join(DIAGNOSTIC_DIR, "startup_with_line.jpg")

# IDs COCO en YOLO:
# 2 = car
# 3 = motorcycle
# 5 = bus
# 7 = truck
CLASS_MAP = {
    2: "cars",
    3: "motorcycles",
    5: "buses",
    7: "trucks"
}

ZONE = np.array([
    [205, 185],
    [185, 585],
    [1052, 594],
    [1015, 181],
    [219, 176]
], dtype=np.int32)

TRACKER_CONFIG = {
    'tracker': "bytetrack.yaml",
    'show': False,
    'save': False,
    'save_txt': False,
    'imgsz': 640,
    'conf': 0.4,
    'iou': 0.5,
    'agnostic_nms': True,
    'device': '0',
    'stream': True
}

CLASS_NAMES = ["cars", "trucks", "buses", "motorcycles"]
DIRECTION_NAMES = ["to_sl", "from_sl"]

# =========================================================
# FUNCIONES SERIAL
# =========================================================

def find_port():
    """Busca puerto automáticamente si no se usa alias fijo."""
    ports = serial.tools.list_ports.comports()

    print("[debug] Puertos detectados:")
    for port in ports:
        print(f"  {port.device} -> {port.description}")

    for port in ports:
        if "Nano" in port.description:
            return port.device

    return None


def open_serial():
    global ser

    if USE_FIXED_PORT:
        port = FIXED_PORT
    else:
        port = find_port()

    if not port:
        print("[debug] No se encontró ningún puerto válido.")
        sys.exit(1)

    print(f"[debug] Conectando a: {port}")
    ser = serial.Serial(port, baudrate=115200, timeout=1)
    print(f"[debug] Conectado correctamente a: {port}")


def close_serial():
    global ser
    if ser and ser.is_open:
        print("\n[debug] Cerrando el puerto serial...")
        ser.close()
        print("[debug] Puerto cerrado.")


def signal_handler(sig, frame):
    print("\n[debug] Señal de cierre recibida.")
    close_serial()
    if SHOW_GUI:
        cv2.destroyAllWindows()
    sys.exit(0)

# =========================================================
# FUNCIONES AUXILIARES
# =========================================================

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def get_class_name(det):
    """Devuelve nombre de clase según CLASS_MAP."""
    class_id = int(det.cls[0].cpu().numpy())
    return CLASS_MAP.get(class_id, None)


def get_bbox(det):
    if len(det) == 0:
        return None
    return det.xyxy[0].cpu().numpy().astype(int)


def get_center(bbox):
    if bbox is None:
        return None, None
    xc = (bbox[0] + bbox[2]) // 2
    yc = (bbox[1] + bbox[3]) // 2
    return xc, yc


def is_valid_detection(xc, yc):
    """Valida si el centro está dentro de la ROI o acepta todo si ROI desactivada."""
    if not USE_ROI:
        return True
    return mlpPath.Path(ZONE).contains_point((xc, yc))


def get_track_id(det):
    if det.id is None:
        return None
    return int(det.id[0].cpu().numpy())


def new_counter_dict():
    return {name: 0 for name in CLASS_NAMES}


def new_set_dict():
    return {name: set() for name in CLASS_NAMES}


def new_direction_set_dict():
    return {direction: new_set_dict() for direction in DIRECTION_NAMES}


def build_direction_counts(direction_unique_ids):
    car_count = len(direction_unique_ids["cars"])
    bike_count = len(direction_unique_ids["motorcycles"])
    heavy_count = len(direction_unique_ids["trucks"]) + len(direction_unique_ids["buses"])
    total_count = car_count + bike_count + heavy_count

    return {
        "car": car_count,
        "bike": bike_count,
        "heavy": heavy_count,
        "total": total_count
    }


def draw_roi(frame):
    """Dibuja la ROI sobre el frame si está activada."""
    if USE_ROI:
        cv2.polylines(frame, pts=[ZONE], isClosed=True, color=(255, 0, 0), thickness=2)


def get_line_y(frame):
    """Calcula la posición vertical de la línea de conteo."""
    h = frame.shape[0]
    return int(h * LINE_POSITION_RATIO)


def draw_counting_line(frame, line_y):
    """Dibuja la línea horizontal de conteo."""
    h, w = frame.shape[:2]
    cv2.line(frame, (0, line_y), (w, line_y), (0, 0, 255), 3)
    cv2.putText(
        frame,
        "Counting line",
        (15, max(25, line_y - 12)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (0, 0, 255),
        2,
        cv2.LINE_AA
    )


def draw_overlay(frame, current_counts, interval_counts):
    """
    Dibuja los conteos en la esquina superior derecha.
    Cambios visuales:
    - Letras aproximadamente el doble de grandes.
    - Fondo negro sólido para mejorar contraste.
    - Posición alineada a la derecha.
    """
    h, w = frame.shape[:2]

    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 1.30   # Antes era 0.65; ahora es el doble.
    thickness = 3
    line_gap = 18
    padding_x = 18
    padding_y = 18
    margin = 15

    to_sl_counts = build_direction_counts(interval_counts["to_sl"])
    from_sl_counts = build_direction_counts(interval_counts["from_sl"])
    current_heavy = current_counts["trucks"] + current_counts["buses"]

    lines = [
        f"ROI: {'ON' if USE_ROI else 'OFF'} | Line: BOTH directions",
        f"Frame -> car:{current_counts['cars']} bike:{current_counts['motorcycles']} heavy:{current_heavy}",
        f"To SL -> car:{to_sl_counts['car']} bike:{to_sl_counts['bike']} heavy:{to_sl_counts['heavy']} total:{to_sl_counts['total']}",
        f"From SL -> car:{from_sl_counts['car']} bike:{from_sl_counts['bike']} heavy:{from_sl_counts['heavy']} total:{from_sl_counts['total']}"
    ]

    # Medir el tamaño máximo del texto para crear el fondo negro.
    text_sizes = []
    max_text_w = 0
    total_text_h = 0

    for txt in lines:
        (tw, th), baseline = cv2.getTextSize(txt, font, font_scale, thickness)
        text_sizes.append((tw, th, baseline))
        max_text_w = max(max_text_w, tw)
        total_text_h += th + baseline

    total_text_h += line_gap * (len(lines) - 1)

    box_w = max_text_w + 2 * padding_x
    box_h = total_text_h + 2 * padding_y

    x1 = max(margin, w - box_w - margin)
    y1 = margin
    x2 = min(w - margin, x1 + box_w)
    y2 = min(h - margin, y1 + box_h)

    # Fondo negro.
    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 0), -1)

    # Borde opcional para distinguir el panel.
    cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 255, 255), 2)

    # Escribir texto dentro del panel.
    y = y1 + padding_y
    for i, txt in enumerate(lines):
        tw, th, baseline = text_sizes[i]
        y += th
        x = x1 + padding_x

        # Sombra/borde para mayor legibilidad.
        cv2.putText(
            frame,
            txt,
            (x, y),
            font,
            font_scale,
            (255, 255, 255),
            thickness + 2,
            cv2.LINE_AA
        )
        cv2.putText(
            frame,
            txt,
            (x, y),
            font,
            font_scale,
            (0, 255, 0),
            thickness,
            cv2.LINE_AA
        )

        y += baseline + line_gap


def build_serial_message(interval_unique_ids):
    """
    Construye el mensaje que se envía por UART al MCU.

    Formato JSON line-delimited:
    {"stream_key":"carsbikebustruck","car_to_sl":1,"bike_to_sl":0,"heavy_to_sl":0,"total_to_sl":1,"car_from_sl":0,"bike_from_sl":1,"heavy_from_sl":0,"total_from_sl":1}\n
    El salto de línea final permite que el Arduino/ESP32 lea con readStringUntil('\n')
    o mediante serialEvent().
    """
    to_sl_counts = build_direction_counts(interval_unique_ids["to_sl"])
    from_sl_counts = build_direction_counts(interval_unique_ids["from_sl"])

    payload = {
        "stream_key": STREAM_KEY,
        "car_to_sl": to_sl_counts["car"],
        "bike_to_sl": to_sl_counts["bike"],
        "heavy_to_sl": to_sl_counts["heavy"],
        "total_to_sl": to_sl_counts["total"],
        "car_from_sl": from_sl_counts["car"],
        "bike_from_sl": from_sl_counts["bike"],
        "heavy_from_sl": from_sl_counts["heavy"],
        "total_from_sl": from_sl_counts["total"],
    }
    return json.dumps(payload, separators=(",", ":")) + "\n"


def save_startup_frame_with_roi(frame):
    """
    Guarda una única imagen del frame completo con el ROI dibujado.
    La carpeta de salida se crea junto al script.
    Funciona sin sesión gráfica.
    """
    try:
        ensure_dir(DIAGNOSTIC_DIR)

        frame_vis = frame.copy()
        draw_roi(frame_vis)
        line_y = get_line_y(frame_vis)
        draw_counting_line(frame_vis, line_y)

        ok = cv2.imwrite(STARTUP_FRAME_PATH, frame_vis)
        if ok:
            print(f"[debug] Imagen inicial con línea guardada en: {STARTUP_FRAME_PATH}")
        else:
            print(f"[debug] No se pudo guardar la imagen inicial en: {STARTUP_FRAME_PATH}")
    except Exception as e:
        print(f"[debug] Error guardando imagen inicial con línea: {e}")

# =========================================================
# MAIN
# =========================================================

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

try:
    print(f"[debug] SHOW_GUI = {SHOW_GUI}")
    print(f"[debug] SAVE_STARTUP_ROI_FRAME = {SAVE_STARTUP_ROI_FRAME}")

    open_serial()

    print("")
    print("Disponibilidad de CUDA con torch:", torch.cuda.is_available())
    print("Disponibilidad de CUDA con cv2:", cv2.cuda.getCudaEnabledDeviceCount() > 0)
    print("")

    model = YOLO(MODEL_PATH)

    # IDs únicos que cruzaron la línea durante el intervalo, separados por sentido
    interval_unique_ids = new_direction_set_dict()

    # Última posición vertical conocida por track_id.
    # Formato: {track_id: yc_anterior}
    previous_y_by_id = {}

    last_sent = time.time()

    for result in model.track(source=VIDEO_PATH, **TRACKER_CONFIG):
        frame = result.orig_img

        # Dibujar ROI sobre el frame, si está activada
        draw_roi(frame)

        # Calcular y dibujar línea de conteo
        line_y = get_line_y(frame)
        draw_counting_line(frame, line_y)

        # Guardar una sola vez el primer frame con línea/ROI
        if SAVE_STARTUP_ROI_FRAME and not startup_frame_saved:
            save_startup_frame_with_roi(frame)
            startup_frame_saved = True

        # Conteos visibles del frame actual
        current_counts = new_counter_dict()

        for det in result.boxes:
            class_name = get_class_name(det)
            if class_name is None:
                continue

            bbox = get_bbox(det)
            if bbox is None:
                continue

            xc, yc = get_center(bbox)
            if xc is None or yc is None:
                continue

            if not is_valid_detection(xc, yc):
                continue

            track_id = get_track_id(det)

            # Conteo visual: vehículos detectados actualmente en el frame/ROI.
            # Este valor NO es el que se envía por serial.
            current_counts[class_name] += 1

            # Conteo real por cruce de línea: ambos sentidos.
            crossed_down = False
            crossed_up = False
            if track_id is not None:
                previous_y = previous_y_by_id.get(track_id)

                if previous_y is not None:
                    # En coordenadas de imagen, y crece hacia abajo.
                    # previous_y < line_y y yc >= line_y significa cruce descendente.
                    # previous_y > line_y y yc <= line_y significa cruce ascendente.
                    crossed_down = previous_y < line_y and yc >= line_y
                    crossed_up = previous_y > line_y and yc <= line_y

                if crossed_down and track_id not in interval_unique_ids["to_sl"][class_name]:
                    interval_unique_ids["to_sl"][class_name].add(track_id)
                    print(f"[debug] Cruce TO_SL detectado -> {class_name} ID:{track_id}")

                if crossed_up and track_id not in interval_unique_ids["from_sl"][class_name]:
                    interval_unique_ids["from_sl"][class_name].add(track_id)
                    print(f"[debug] Cruce FROM_SL detectado -> {class_name} ID:{track_id}")

                previous_y_by_id[track_id] = yc

            # Dibujos
            cv2.rectangle(frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]), (0, 255, 0), 2)
            cv2.circle(frame, (xc, yc), 5, (0, 0, 255), 2)

            label = class_name
            if track_id is not None:
                label += f" ID:{track_id}"

            cv2.putText(
                frame,
                label,
                (bbox[0], max(20, bbox[1] - 10)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 255),
                2,
                cv2.LINE_AA
            )

        interval_counts = interval_unique_ids

        print(
            f"Frame -> cars:{current_counts['cars']} "
            f"trucks:{current_counts['trucks']} "
            f"buses:{current_counts['buses']} "
            f"motorcycles:{current_counts['motorcycles']}"
        )
        to_sl_counts = build_direction_counts(interval_counts["to_sl"])
        from_sl_counts = build_direction_counts(interval_counts["from_sl"])
        print(
            f"Crossed interval TO_SL -> car:{to_sl_counts['car']} "
            f"bike:{to_sl_counts['bike']} "
            f"heavy:{to_sl_counts['heavy']} "
            f"total:{to_sl_counts['total']}"
        )
        print(
            f"Crossed interval FROM_SL -> car:{from_sl_counts['car']} "
            f"bike:{from_sl_counts['bike']} "
            f"heavy:{from_sl_counts['heavy']} "
            f"total:{from_sl_counts['total']}"
        )
        print("")

        draw_overlay(frame, current_counts, interval_counts)

        # Envío por intervalo
        if time.time() - last_sent > INTERVAL:
            if ser and ser.is_open:
                mensaje = build_serial_message(interval_unique_ids)
                ser.write(mensaje.encode())
                print(f"[debug] Enviado por serial: {mensaje.strip()}")

                # Reiniciar acumuladores de la ventana
                interval_unique_ids = new_direction_set_dict()

            last_sent = time.time()

        if SHOW_GUI:
            resized = cv2.resize(frame, (960, 540))
            cv2.imshow("Tracking", resized)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

except Exception as e:
    print(f"[debug] Error: {e}")

finally:
    close_serial()
    if SHOW_GUI:
        cv2.destroyAllWindows()
