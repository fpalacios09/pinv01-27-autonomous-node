import serial
import signal
import sys
import subprocess
import time
import os
import psutil
import shutil
import tarfile


print(".\n.\n.\n=================================")
print("PINV0127 AUTONOMOUS NODE STARTED")
print("=================================.\n.\n.\n")


# =========================
# CONFIGURACIÓN GENERAL
# =========================
SERIAL_PORT = os.getenv("PINV_UPDATE_SERIAL_PORT", "/dev/adapter")  # UART de hashes
MCU_PORT = os.getenv("PINV_MCU_PORT", "/dev/mcu")  # Host MCU
BAUDRATE = 115200

# Descarga de actualizaciones:
# - primero se intenta P2P mediante Kubo;
# - si no finaliza en 20 segundos, se usan gateways HTTPS;
# - cualquier archivo se acepta únicamente si su CID coincide.
IPFS_DOWNLOAD_TIMEOUT = 20
IPFS_START_TIMEOUT = 60
IPFS_NETWORK_WAIT_AT_START = 60
IPFS_NETWORK_WAIT_BEFORE_DOWNLOAD = 10
IPFS_MIN_TCP_PEERS = 1

HTTPS_CONNECT_TIMEOUT = 10
HTTPS_DOWNLOAD_TIMEOUT = 65
HTTPS_PROCESS_TIMEOUT = 75

# Si otro proceso mantiene repo.lock mientras termina o arranca,
# node.py espera y reintenta sin borrar el bloqueo manualmente.
IPFS_LOCK_WAIT_TIMEOUT = 30
IPFS_START_MAX_ATTEMPTS = 3
IPFS_START_RETRY_DELAY = 2

# Se usan rutas absolutas para evitar diferencias de PATH dentro de Conda.
IPFS_BIN = os.getenv("PINV_IPFS_BIN", "/usr/local/bin/ipfs")
IPFS_REPO = os.path.expanduser("~/.ipfs")
CURL_BIN = os.getenv("PINV_CURL_BIN", "/usr/bin/curl")

# Se prueban en orden. En cuanto uno entrega un archivo cuyo CID coincide,
# no se consulta ninguno de los siguientes.
IPFS_HTTPS_GATEWAYS = (
    "https://ipfs.io/ipfs",
    "https://dweb.link/ipfs",
    "https://gateway.pinata.cloud/ipfs",
    "https://4everland.io/ipfs",
    "https://ipfs.filebase.io/ipfs",
    "https://latam.orbitor.dev/ipfs",
    "https://ipfs.orbitor.dev/ipfs",
)

DESKTOP_UPDATES_DIR = os.path.expanduser(os.getenv("PINV_UPDATES_DIR", "~/Desktop/updates_ipfs"))
IPFS_DAEMON_LOG = os.path.join(DESKTOP_UPDATES_DIR, "ipfs_daemon.log")

# Arduino Nano ESP32 vía DFU
DFU_DEVICE = "0x2341:0x0070"
DFU_UTIL = "/usr/bin/dfu-util"

# Nombre esperado dentro de la carpeta python
PYTHON_SCRIPT_NAME = "script.py"

ser = None
ipfs_daemon_process = None
ipfs_daemon_log = None
ipfs_daemon_owned = False
my_pid = None
current_python_process = None
current_python_pgid = None
current_python_stdout_log = None
current_python_stderr_log = None


# =========================
# UTILIDADES GENERALES
# =========================
def ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def normalize_bool_file(file_path):
    """
    Lee un archivo de texto que debe contener solamente 'true' o 'false'.
    Devuelve True/False o None si no es válido.
    """
    if not os.path.isfile(file_path):
        print(f"[debug] No existe el archivo: {file_path}")
        return None

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read().strip().lower()

        if content == "true":
            return True
        elif content == "false":
            return False
        else:
            print(f"[debug] Contenido inválido en {file_path}: '{content}'")
            return None
    except Exception as e:
        print(f"[debug] Error leyendo {file_path}: {e}")
        return None


def safe_remove(path):
    """
    Elimina archivo o carpeta si existe.
    """
    try:
        if os.path.isdir(path):
            shutil.rmtree(path)
        elif os.path.isfile(path):
            os.remove(path)
    except Exception as e:
        print(f"[debug] No se pudo eliminar {path}: {e}")


def find_first_ino(root_dir):
    """
    Busca recursivamente el primer archivo .ino dentro de root_dir.
    Devuelve la ruta absoluta o None.
    """
    for base, _, files in os.walk(root_dir):
        for file in files:
            if file.endswith(".ino"):
                return os.path.join(base, file)
    return None


def find_first_ino_bin(root_dir):
    """
    Busca recursivamente el primer archivo .ino.bin dentro de root_dir.
    Devuelve la ruta absoluta o None.
    """
    for base, _, files in os.walk(root_dir):
        for file in files:
            if file.endswith(".ino.bin"):
                return os.path.join(base, file)
    return None


# =========================
# MANEJO DE PROCESOS
# =========================
def describe_process(proc):
    """
    Devuelve una descripción legible del proceso.
    """
    try:
        return f"PID={proc.pid}, CMD={proc.cmdline()}"
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        return f"PID={getattr(proc, 'pid', '?')}"


def close_tracked_python_logs():
    """
    Cierra los archivos de log del script Python actualmente rastreado.
    """
    global current_python_stdout_log, current_python_stderr_log

    for handle_name in ('current_python_stdout_log', 'current_python_stderr_log'):
        handle = globals().get(handle_name)
        if handle:
            try:
                handle.flush()
                handle.close()
            except Exception:
                pass
            globals()[handle_name] = None


def refresh_current_python_tracking():
    """
    Limpia el rastreo si el proceso principal ya terminó.
    """
    global current_python_process, current_python_pgid

    if current_python_process is None:
        return

    try:
        if current_python_process.poll() is not None:
            current_python_process = None
            current_python_pgid = None
            close_tracked_python_logs()
    except Exception:
        current_python_process = None
        current_python_pgid = None
        close_tracked_python_logs()


def list_processes_in_group(pgid):
    """
    Lista procesos pertenecientes a un PGID específico.
    """
    members = []
    if pgid is None:
        return members

    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.pid == my_pid:
                continue
            if os.getpgid(proc.pid) == pgid:
                members.append(proc)
        except (ProcessLookupError, PermissionError, psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    return members


def stop_tracked_python_process():
    """
    Detiene únicamente el árbol de procesos del script Python lanzado por node.py.
    No toca otros Python del sistema.
    """
    global current_python_process, current_python_pgid

    refresh_current_python_tracking()

    root_proc = None
    if current_python_process is not None:
        try:
            root_proc = psutil.Process(current_python_process.pid)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            root_proc = None

    group_members = list_processes_in_group(current_python_pgid)

    if root_proc is None and not group_members:
        print('[debug] No hay script Python hijo en ejecución para detener.')
        current_python_process = None
        current_python_pgid = None
        close_tracked_python_logs()
        return True

    if root_proc is not None:
        try:
            descendants = root_proc.children(recursive=True)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            descendants = []
    else:
        descendants = []

    targets = []
    seen = set()
    for proc in descendants + ([root_proc] if root_proc is not None else []) + group_members:
        if proc is None:
            continue
        try:
            if proc.pid == my_pid or proc.pid in seen:
                continue
            seen.add(proc.pid)
            targets.append(proc)
        except Exception:
            pass

    if not targets:
        print('[debug] No se encontraron procesos hijos activos para detener.')
        current_python_process = None
        current_python_pgid = None
        close_tracked_python_logs()
        return True

    print(f'[debug] Deteniendo script Python hijo y su árbol ({len(targets)} proceso(s)).')
    for proc in targets:
        print(f'[debug]   objetivo -> {describe_process(proc)}')

    if current_python_pgid is not None:
        try:
            print(f'[debug] Enviando SIGTERM al grupo PGID={current_python_pgid}')
            os.killpg(current_python_pgid, signal.SIGTERM)
        except Exception as e:
            print(f'[debug] No se pudo enviar SIGTERM al grupo {current_python_pgid}: {e}')

    for proc in reversed(targets):
        try:
            if proc.is_running():
                proc.terminate()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    gone, alive = psutil.wait_procs(targets, timeout=5)

    if alive:
        if current_python_pgid is not None:
            try:
                print(f'[debug] Enviando SIGKILL al grupo PGID={current_python_pgid}')
                os.killpg(current_python_pgid, signal.SIGKILL)
            except Exception as e:
                print(f'[debug] No se pudo enviar SIGKILL al grupo {current_python_pgid}: {e}')

        for proc in alive:
            try:
                if proc.is_running() and proc.pid != my_pid:
                    print(f'[debug] Forzando kill a {describe_process(proc)}')
                    proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass

        gone2, alive = psutil.wait_procs(alive, timeout=3)

    survivors = []
    for proc in alive:
        try:
            if proc.is_running() and proc.pid != my_pid:
                survivors.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    if current_python_pgid is not None:
        extra_survivors = list_processes_in_group(current_python_pgid)
        known = {p.pid for p in survivors}
        for proc in extra_survivors:
            if proc.pid not in known and proc.pid != my_pid:
                survivors.append(proc)

    if survivors:
        print('[error] No se pudo detener completamente el árbol del script hijo:')
        for proc in survivors:
            print(f'[error]   {describe_process(proc)}')
        return False

    print('[debug] Script Python hijo detenido correctamente.')
    current_python_process = None
    current_python_pgid = None
    close_tracked_python_logs()
    return True


def stop_running_code(exclude_pid=None):
    """
    Compatibilidad con el nombre anterior: ahora solo detiene
    el script hijo lanzado por node.py y sus descendientes.
    """
    return stop_tracked_python_process()


def run_code_in_background(file_path):
    """
    Ejecuta un script Python en segundo plano y guarda su referencia
    para poder detener exactamente ese árbol de procesos más adelante.
    """
    global current_python_process, current_python_pgid
    global current_python_stdout_log, current_python_stderr_log

    if not os.path.isfile(file_path):
        print(f"[error] El archivo '{file_path}' no existe.")
        return None

    working_dir = os.path.dirname(file_path)
    print(f"[debug] Ejecutando en segundo plano: {file_path}")
    print(f"[debug] Directorio de trabajo: {working_dir}")

    try:
        close_tracked_python_logs()

        log_out = open(os.path.join(working_dir, 'python_stdout.log'), 'a')
        log_err = open(os.path.join(working_dir, 'python_stderr.log'), 'a')

        process = subprocess.Popen(
            ['python3', file_path],
            stdout=log_out,
            stderr=log_err,
            cwd=working_dir,
            start_new_session=True
        )

        current_python_process = process
        current_python_stdout_log = log_out
        current_python_stderr_log = log_err

        try:
            current_python_pgid = os.getpgid(process.pid)
        except Exception:
            current_python_pgid = None

        print(f'[debug] Nuevo script Python lanzado con PID={process.pid}, PGID={current_python_pgid}')
        return process
    except Exception as e:
        print(f"[error] No se pudo ejecutar '{file_path}': {e}")
        current_python_process = None
        current_python_pgid = None
        close_tracked_python_logs()
        return None


# =========================
# IPFS
# =========================
def get_ipfs_env():
    """
    Devuelve un entorno explícito para que todas las llamadas usen
    el mismo repositorio de Kubo, incluso dentro de un entorno Conda.
    """
    env = os.environ.copy()
    env["IPFS_PATH"] = IPFS_REPO
    return env


def close_ipfs_daemon_log():
    """
    Cierra de forma segura el archivo de log del daemon.
    """
    global ipfs_daemon_log

    if ipfs_daemon_log:
        try:
            ipfs_daemon_log.flush()
            ipfs_daemon_log.close()
        except Exception:
            pass
        ipfs_daemon_log = None


def read_ipfs_log_tail(max_lines=30):
    """
    Devuelve las últimas líneas del log del daemon para diagnóstico.
    """
    try:
        if ipfs_daemon_log:
            ipfs_daemon_log.flush()

        if not os.path.isfile(IPFS_DAEMON_LOG):
            return ""

        with open(IPFS_DAEMON_LOG, "r", encoding="utf-8", errors="replace") as f:
            lines = f.read().splitlines()

        return "\n".join(lines[-max_lines:])
    except Exception:
        return ""


def ipfs_api_is_ready():
    """
    Comprueba si existe un daemon IPFS realmente en línea.

    No se usa ``ipfs id`` porque ese comando puede devolver la identidad
    local incluso sin daemon, produciendo un falso positivo. En cambio,
    ``ipfs swarm peers`` requiere conectarse a la API del daemon.
    """
    try:
        result = subprocess.run(
            [IPFS_BIN, "swarm", "peers"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            universal_newlines=True,
            timeout=5,
            env=get_ipfs_env()
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False


def wait_for_ipfs_network(timeout_seconds=30, minimum_tcp_peers=1):
    """
    Espera hasta que Kubo tenga al menos la cantidad indicada de peers TCP.

    La Jetson está configurada para usar TCP porque QUIC/WebTransport/WebRTC
    presentaron problemas al salir mediante el router 4G.
    """
    print(
        f"[debug] Esperando conexión IPFS con la red "
        f"(mínimo {minimum_tcp_peers} peer(s) TCP)..."
    )

    deadline = time.monotonic() + timeout_seconds
    last_status = None

    while time.monotonic() < deadline:
        try:
            result = subprocess.run(
                [IPFS_BIN, "swarm", "peers"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                timeout=5,
                env=get_ipfs_env()
            )

            if result.returncode == 0:
                peers = [
                    line.strip()
                    for line in result.stdout.splitlines()
                    if line.strip()
                ]
                tcp_peers = [peer for peer in peers if "/tcp/" in peer]

                status = (len(peers), len(tcp_peers))
                if status != last_status:
                    print(
                        f"[debug] Peers IPFS conectados: {len(peers)} "
                        f"(TCP: {len(tcp_peers)})"
                    )
                    last_status = status

                if len(tcp_peers) >= minimum_tcp_peers:
                    print("[debug] IPFS conectado mediante TCP y listo.")
                    return True
            else:
                error = result.stderr.strip()
                if error:
                    print(f"[debug] IPFS todavía no está listo: {error}")

        except subprocess.TimeoutExpired:
            print("[debug] Timeout al consultar peers IPFS.")
        except Exception as e:
            print(f"[debug] Error consultando peers IPFS: {e}")

        time.sleep(2)

    print(
        f"[error] IPFS no consiguió {minimum_tcp_peers} peer(s) TCP "
        f"en {timeout_seconds} segundos."
    )
    return False


def start_ipfs_daemon(attempt=1, max_attempts=IPFS_START_MAX_ATTEMPTS):
    """
    Inicia Kubo sin usar PIPE para stdout/stderr.

    Si encuentra repo.lock ocupado, no elimina el archivo de bloqueo:
    primero espera por si existe otro daemon que todavía está arrancando o
    terminando y, si la API no aparece, vuelve a intentar de forma limitada.
    """
    global ipfs_daemon_process, ipfs_daemon_log, ipfs_daemon_owned

    print(
        f"[debug] Iniciando daemon de IPFS "
        f"(intento {attempt}/{max_attempts})..."
    )

    if not os.path.isfile(IPFS_BIN):
        raise FileNotFoundError(f"No se encontró el binario IPFS en: {IPFS_BIN}")

    ensure_dir(DESKTOP_UPDATES_DIR)
    ensure_dir(IPFS_REPO)

    # Si un daemon ya está completamente en línea, se reutiliza.
    if ipfs_api_is_ready():
        print("[debug] Ya existe un daemon IPFS en línea para este repositorio.")
        ipfs_daemon_process = None
        ipfs_daemon_owned = False
        close_ipfs_daemon_log()
        return True

    close_ipfs_daemon_log()

    ipfs_daemon_log = open(
        IPFS_DAEMON_LOG,
        "w",
        encoding="utf-8",
        errors="replace",
        buffering=1
    )

    try:
        ipfs_daemon_process = subprocess.Popen(
            [IPFS_BIN, "daemon"],
            stdout=ipfs_daemon_log,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            env=get_ipfs_env()
        )
    except Exception as e:
        close_ipfs_daemon_log()
        ipfs_daemon_process = None
        ipfs_daemon_owned = False
        print(f"[error] No se pudo lanzar el daemon IPFS: {e}")
        return False

    ipfs_daemon_owned = True
    deadline = time.monotonic() + IPFS_START_TIMEOUT

    while time.monotonic() < deadline:
        # La API puede estar lista antes de que se escriba todo el log.
        if ipfs_api_is_ready():
            print(".\n.\n.\n[debug] Daemon IPFS arrancó correctamente.\n.\n.\n.")
            print(f"[debug] Log del daemon: {IPFS_DAEMON_LOG}")
            return True

        if ipfs_daemon_process.poll() is not None:
            details = read_ipfs_log_tail()
            lock_error = (
                "someone else has the lock" in details.lower()
                or "repo.lock" in details.lower()
            )

            close_ipfs_daemon_log()
            ipfs_daemon_process = None
            ipfs_daemon_owned = False

            if lock_error:
                print(
                    "[warning] El repositorio IPFS está bloqueado temporalmente. "
                    "Puede existir otro daemon que todavía está arrancando o cerrándose."
                )
                if details:
                    print(f"[debug] Detalle del bloqueo:\n{details}")

                lock_deadline = time.monotonic() + IPFS_LOCK_WAIT_TIMEOUT

                while time.monotonic() < lock_deadline:
                    if ipfs_api_is_ready():
                        print(
                            "[debug] Se detectó un daemon IPFS en línea. "
                            "Se utilizará ese daemon."
                        )
                        return True

                    remaining = int(lock_deadline - time.monotonic())
                    print(
                        f"[debug] Esperando liberación/inicio del repositorio IPFS "
                        f"({max(remaining, 0)} s restantes)..."
                    )
                    time.sleep(2)

                if attempt < max_attempts:
                    print(
                        f"[debug] La API no apareció. Reintentando iniciar Kubo "
                        f"en {IPFS_START_RETRY_DELAY} segundos..."
                    )
                    time.sleep(IPFS_START_RETRY_DELAY)
                    return start_ipfs_daemon(
                        attempt=attempt + 1,
                        max_attempts=max_attempts
                    )

                print(
                    "[error] No fue posible iniciar ni detectar el daemon IPFS "
                    "después de varios intentos."
                )
                print(
                    "[error] No se eliminó repo.lock automáticamente para evitar "
                    "corromper un repositorio que pudiera estar en uso."
                )
                return False

            message = "[error] El daemon IPFS terminó prematuramente."
            if details:
                message += f"\n[error] Últimas líneas del log:\n{details}"
            print(message)
            return False

        time.sleep(1)

    details = read_ipfs_log_tail()
    print(
        f"[error] El daemon IPFS no respondió dentro de "
        f"{IPFS_START_TIMEOUT} segundos."
    )
    if details:
        print(f"[error] Últimas líneas del log:\n{details}")

    stop_ipfs_daemon()

    if attempt < max_attempts:
        print(
            f"[debug] Reintentando iniciar Kubo en "
            f"{IPFS_START_RETRY_DELAY} segundos..."
        )
        time.sleep(IPFS_START_RETRY_DELAY)
        return start_ipfs_daemon(
            attempt=attempt + 1,
            max_attempts=max_attempts
        )

    return False

def stop_ipfs_daemon():
    """
    Apaga de forma ordenada únicamente el daemon iniciado por node.py.
    """
    global ipfs_daemon_process, ipfs_daemon_owned

    if not ipfs_daemon_owned:
        close_ipfs_daemon_log()
        return

    print(".\n.\n.\n[debug] Deteniendo daemon IPFS...")

    try:
        subprocess.run(
            [IPFS_BIN, "shutdown"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            timeout=10,
            env=get_ipfs_env()
        )
    except Exception as e:
        print(f"[debug] No se pudo apagar mediante 'ipfs shutdown': {e}")

    if ipfs_daemon_process is not None:
        try:
            ipfs_daemon_process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            print("[debug] El daemon no cerró a tiempo; enviando SIGTERM.")
            ipfs_daemon_process.terminate()

            try:
                ipfs_daemon_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                print("[debug] El daemon no respondió; enviando SIGKILL.")
                ipfs_daemon_process.kill()
                ipfs_daemon_process.wait()

    ipfs_daemon_process = None
    ipfs_daemon_owned = False
    close_ipfs_daemon_log()

    print(".\n.\n.\n[debug] Daemon IPFS detenido.\n.\n.\n.")


def stop_ipfs_daemon2():
    """
    Compatibilidad con el nombre anterior.
    """
    stop_ipfs_daemon()


def is_valid_ipfs_hash(hash_value):
    """
    Validación simple, similar a la lógica actual.
    """
    if hash_value == "-":
        return False
    return len(hash_value) >= 46


def calculate_file_cid(file_path, expected_cid):
    """
    Calcula el CID del archivo sin añadirlo al repositorio.

    Para los CIDv0 que comienzan con Qm se reproduce el formato empleado
    por ``ipfs add`` con DAG-PB y raw leaves desactivado. Para CIDv1 se
    prueban las dos configuraciones habituales de raw leaves.

    Devuelve el CID calculado que coincida o None.
    """
    if not os.path.isfile(file_path) or os.path.getsize(file_path) <= 0:
        print(f"[error] El archivo no existe o está vacío: {file_path}")
        return None

    if expected_cid.startswith("Qm"):
        strategies = [
            ("0", "false"),
        ]
    else:
        strategies = [
            ("1", "false"),
            ("1", "true"),
        ]

    calculated_values = []

    for cid_version, raw_leaves in strategies:
        try:
            result = subprocess.run(
                [
                    IPFS_BIN,
                    "add",
                    "--only-hash",
                    f"--cid-version={cid_version}",
                    f"--raw-leaves={raw_leaves}",
                    "-Q",
                    file_path,
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                timeout=60,
                env=get_ipfs_env()
            )
        except subprocess.TimeoutExpired:
            print("[error] Timeout calculando el CID del archivo descargado.")
            continue
        except Exception as e:
            print(f"[error] No se pudo calcular el CID: {e}")
            continue

        if result.returncode != 0:
            error = result.stderr.strip()
            print(f"[debug] No se pudo calcular el CID: {error}")
            continue

        calculated_cid = result.stdout.strip()
        if calculated_cid:
            calculated_values.append(calculated_cid)

        if calculated_cid == expected_cid:
            print(f"[debug] CID esperado:  {expected_cid}")
            print(f"[debug] CID calculado: {calculated_cid}")
            return calculated_cid

    print(f"[error] CID esperado: {expected_cid}")

    if calculated_values:
        for calculated_cid in calculated_values:
            print(f"[error] CID calculado: {calculated_cid}")
    else:
        print("[error] No se obtuvo ningún CID calculado.")

    return None


def verify_downloaded_file(file_path, expected_cid):
    """
    Comprueba que:
    1. exista un archivo regular y no vacío;
    2. sus bytes produzcan exactamente el CID esperado;
    3. el contenido sea un TAR/TAR.GZ válido.
    """
    if not os.path.isfile(file_path):
        print(f"[error] La descarga no produjo un archivo regular: {file_path}")
        return False

    if os.path.getsize(file_path) <= 0:
        print(f"[error] El archivo descargado está vacío: {file_path}")
        return False

    if calculate_file_cid(file_path, expected_cid) is None:
        print("[error] El archivo descargado no corresponde al CID solicitado.")
        return False

    try:
        if not tarfile.is_tarfile(file_path):
            print("[error] El archivo coincide con el CID, pero no es un TAR válido.")
            return False

        # Abrir el archivo obliga a tarfile a comprobar su estructura.
        with tarfile.open(file_path, "r:*") as tar:
            tar.getmembers()

    except Exception as e:
        print(f"[error] El archivo TAR está dañado o no es legible: {e}")
        return False

    print("[debug] El archivo descargado es un TAR válido.")
    return True


def find_single_downloaded_file(download_dir):
    """
    Localiza el único archivo regular producido por ``ipfs get``.

    Para esta aplicación cada CID debe representar un único archivo
    comprimido, no un directorio con varios archivos.
    """
    regular_files = []

    for root, _, files in os.walk(download_dir):
        for filename in files:
            file_path = os.path.join(root, filename)

            if os.path.isfile(file_path):
                regular_files.append(file_path)

    if len(regular_files) == 1:
        return regular_files[0]

    if not regular_files:
        print("[error] IPFS no descargó ningún archivo regular.")
    else:
        print(
            f"[error] Se esperaban un solo archivo y se encontraron "
            f"{len(regular_files)}."
        )

    return None


def detect_archive_extension(file_path):
    """
    Determina si el archivo TAR está comprimido con gzip.

    Devuelve '.tar.gz' para gzip y '.tar' para TAR sin compresión.
    """
    try:
        with open(file_path, "rb") as f:
            magic = f.read(2)

        if magic == b"\x1f\x8b":
            return ".tar.gz"

    except Exception as e:
        print(f"[debug] No se pudo leer la cabecera del archivo: {e}")

    return ".tar"


def download_archive_from_gateways(hash_value, temp_dir):
    """
    Prueba gateways HTTPS en orden.

    Cada respuesta se guarda primero como archivo parcial. El archivo solo
    se devuelve si el CID calculado coincide y es un TAR válido.
    """
    if not os.path.isfile(CURL_BIN):
        print(f"[error] No se encontró curl en: {CURL_BIN}")
        print("[debug] Instalación sugerida: sudo apt install -y curl")
        return None

    partial_path = os.path.join(temp_dir, f"{hash_value}.https.part")
    total_gateways = len(IPFS_HTTPS_GATEWAYS)

    print("[debug] Iniciando respaldo mediante gateways HTTPS...")

    for index, gateway in enumerate(IPFS_HTTPS_GATEWAYS, start=1):
        safe_remove(partial_path)

        url = f"{gateway.rstrip('/')}/{hash_value}"

        print("----------------------------------------")
        print(f"[debug] Gateway {index}/{total_gateways}: {gateway}")

        command = [
            CURL_BIN,
            "--fail",
            "--location",
            "--silent",
            "--show-error",
            "--connect-timeout",
            str(HTTPS_CONNECT_TIMEOUT),
            "--max-time",
            str(HTTPS_DOWNLOAD_TIMEOUT),
            "--retry",
            "1",
            "--retry-delay",
            "2",
            "--user-agent",
            "PINV01-27-IPFS-Updater/1.0",
            url,
            "-o",
            partial_path,
        ]

        try:
            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                timeout=HTTPS_PROCESS_TIMEOUT
            )
        except subprocess.TimeoutExpired:
            print(
                f"[warning] El gateway superó "
                f"{HTTPS_PROCESS_TIMEOUT} segundos."
            )
            safe_remove(partial_path)
            continue
        except Exception as e:
            print(f"[warning] Error ejecutando curl: {e}")
            safe_remove(partial_path)
            continue

        if result.returncode != 0:
            error = result.stderr.strip()
            print(
                f"[warning] Falló el gateway con código "
                f"{result.returncode}: {error}"
            )
            safe_remove(partial_path)
            continue

        if not os.path.isfile(partial_path):
            print("[warning] El gateway finalizó sin crear el archivo.")
            continue

        file_size = os.path.getsize(partial_path)
        print(
            f"[debug] Descarga HTTPS completada: "
            f"{file_size / (1024 * 1024):.2f} MiB"
        )

        if verify_downloaded_file(partial_path, hash_value):
            print("[ok] Descarga HTTPS verificada correctamente.")
            print(f"[ok] Gateway utilizado: {gateway}")
            return partial_path

        print("[warning] Se descartó la respuesta del gateway.")
        safe_remove(partial_path)

    print("[error] Ningún gateway entregó un archivo válido.")
    return None


def finalize_downloaded_archive(source_path, hash_value, destination_dir):
    """
    Mueve el archivo verificado a su ubicación definitiva.

    El nombre final se basa en el CID y en el tipo real de compresión.
    """
    extension = detect_archive_extension(source_path)
    final_path = os.path.join(destination_dir, f"{hash_value}{extension}")

    # Elimina posibles versiones anteriores con cualquiera de las extensiones.
    safe_remove(os.path.join(destination_dir, f"{hash_value}.tar"))
    safe_remove(os.path.join(destination_dir, f"{hash_value}.tar.gz"))

    shutil.move(source_path, final_path)

    print(f"[debug] Archivo descargado correctamente en: {final_path}")
    return final_path


def download_ipfs_archive(hash_value, destination_dir):
    """
    Recupera una actualización usando un flujo tolerante a fallos:

    1. Comprueba brevemente la red P2P.
    2. Intenta ``ipfs get`` durante IPFS_DOWNLOAD_TIMEOUT segundos.
    3. Si P2P falla, prueba varios gateways HTTPS.
    4. Verifica el CID del archivo recibido.
    5. Comprueba que sea un TAR válido.
    6. Solo entonces lo mueve a la ubicación definitiva.

    Devuelve la ruta final o None.
    """
    ensure_dir(destination_dir)

    temp_dir = os.path.join(destination_dir, f"tmp_{hash_value}")
    safe_remove(temp_dir)
    ensure_dir(temp_dir)

    print(f"[debug] Descargando actualización para CID: {hash_value}")

    downloaded_source = None
    p2p_ready = wait_for_ipfs_network(
        timeout_seconds=IPFS_NETWORK_WAIT_BEFORE_DOWNLOAD,
        minimum_tcp_peers=IPFS_MIN_TCP_PEERS
    )

    if p2p_ready:
        print(
            f"[debug] Intentando descarga P2P durante un máximo de "
            f"{IPFS_DOWNLOAD_TIMEOUT} segundos..."
        )

        try:
            result = subprocess.run(
                [IPFS_BIN, "get", hash_value, "-o", temp_dir],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                timeout=IPFS_DOWNLOAD_TIMEOUT,
                env=get_ipfs_env()
            )

            if result.returncode == 0:
                p2p_file = find_single_downloaded_file(temp_dir)

                if (
                    p2p_file is not None
                    and verify_downloaded_file(p2p_file, hash_value)
                ):
                    print("[ok] Descarga P2P verificada correctamente.")
                    downloaded_source = p2p_file
                else:
                    print("[warning] Se descartó la descarga P2P.")
            else:
                error = result.stderr.strip()
                print(f"[warning] Falló ipfs get: {error}")

        except subprocess.TimeoutExpired:
            print(
                f"[warning] ipfs get superó "
                f"{IPFS_DOWNLOAD_TIMEOUT} segundos."
            )
        except Exception as e:
            print(f"[warning] Excepción durante ipfs get: {e}")

    else:
        print(
            "[warning] No se detectaron peers TCP a tiempo. "
            "Se omite P2P y se continúa mediante HTTPS."
        )

    if downloaded_source is None:
        # Limpia cualquier salida incompleta producida por ipfs get.
        safe_remove(temp_dir)
        ensure_dir(temp_dir)

        downloaded_source = download_archive_from_gateways(
            hash_value,
            temp_dir
        )

    if downloaded_source is None:
        safe_remove(temp_dir)
        print("[error] No se pudo recuperar y verificar la actualización.")
        return None

    try:
        final_path = finalize_downloaded_archive(
            downloaded_source,
            hash_value,
            destination_dir
        )
    except Exception as e:
        print(f"[error] No se pudo guardar el archivo descargado: {e}")
        safe_remove(temp_dir)
        return None

    safe_remove(temp_dir)
    return final_path

def safe_extract_tar(tar, destination):
    """Extrae un TAR sin permitir rutas externas ni enlaces simbólicos/duros."""
    destination_real = os.path.realpath(destination)

    for member in tar.getmembers():
        target_real = os.path.realpath(os.path.join(destination, member.name))
        try:
            inside_destination = os.path.commonpath([destination_real, target_real]) == destination_real
        except ValueError:
            inside_destination = False

        if not inside_destination:
            raise ValueError(f"Ruta insegura dentro del TAR: {member.name}")
        if member.issym() or member.islnk():
            raise ValueError(f"Enlace no permitido dentro del TAR: {member.name}")

    tar.extractall(path=destination)


def extract_archive(archive_path, extract_base_dir):
    """
    Descomprime archivos .tar o .tar.gz en una carpeta con el mismo nombre base.
    Ejemplos:
      update001.tar    -> update001/
      update002.tar.gz -> update002/
    """
    try:
        archive_name = os.path.basename(archive_path)

        if archive_name.endswith(".tar.gz"):
            base_name = archive_name[:-7]
            mode = "r:gz"
        elif archive_name.endswith(".tar"):
            base_name = archive_name[:-4]
            mode = "r:"
        else:
            print(f"[debug] Formato de archivo no soportado: {archive_name}")
            return None

        extract_dir = os.path.join(extract_base_dir, base_name)

        safe_remove(extract_dir)
        ensure_dir(extract_dir)

        print(f"[debug] Descomprimiendo archivo en: {extract_dir}")
        with tarfile.open(archive_path, mode) as tar:
            safe_extract_tar(tar, extract_dir)

        print("[debug] Descompresión completada.")
        return extract_dir

    except Exception as e:
        print(f"[debug] Error al descomprimir {archive_path}: {e}")
        return None


def resolve_update_root(extract_dir):
    """
    Algunas veces el .tar o .tar.gz puede contener directamente:
      arduino/
      python/
    y otras veces una carpeta raíz extra.

    Esta función intenta encontrar el directorio real que contiene
    ambas carpetas o, al menos, una de ellas.
    """
    direct_arduino = os.path.join(extract_dir, "arduino")
    direct_python = os.path.join(extract_dir, "python")

    if os.path.isdir(direct_arduino) or os.path.isdir(direct_python):
        return extract_dir

    try:
        entries = [os.path.join(extract_dir, x) for x in os.listdir(extract_dir)]
        dirs = [x for x in entries if os.path.isdir(x)]

        for d in dirs:
            if os.path.isdir(os.path.join(d, "arduino")) or os.path.isdir(os.path.join(d, "python")):
                return d
    except Exception as e:
        print(f"[debug] Error resolviendo raíz de actualización: {e}")

    return extract_dir


# =========================
# ARDUINO
# =========================
def upload_arduino_bin(arduino_dir):
    """
    Busca un archivo .ino.bin dentro de la carpeta arduino/ y lo sube
    al Arduino Nano ESP32 mediante DFU.
    """
    if not os.path.isdir(arduino_dir):
        print(f"[debug] Carpeta arduino no encontrada: {arduino_dir}")
        return False

    bin_path = find_first_ino_bin(arduino_dir)
    if not bin_path:
        print("[debug] No se encontró ningún archivo .ino.bin dentro de la carpeta arduino.")
        return False

    print(f"[debug] Firmware Arduino detectado: {bin_path}")
    print("[debug] Deteniendo procesos python en ejecución antes de subir firmware...")
    stop_running_code(exclude_pid=my_pid)

    if not os.path.isfile(DFU_UTIL):
        print(f"[error] No se encontró dfu-util en: {DFU_UTIL}")
        return False

    print("[debug] Verificando dispositivo DFU...")
    list_result = subprocess.run(
        [DFU_UTIL, "--list"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True
    )

    if list_result.stdout:
        print(list_result.stdout)
    if list_result.stderr:
        print(list_result.stderr)

    dfu_output = f"{list_result.stdout}\n{list_result.stderr}"

    if list_result.returncode != 0:
        print("[error] No se pudo ejecutar dfu-util --list.")
        return False

    if "Cannot open DFU device" in dfu_output:
        print("[error] El Nano ESP32 fue reconocido, pero el usuario actual no puede abrirlo.")
        print("[debug] Verificá la regla udev y probá nuevamente sin sudo: dfu-util --list")
        return False

    if "Found DFU:" not in dfu_output:
        print("[error] No se detectó ningún dispositivo accesible en modo DFU.")
        print("[debug] Poné el Nano ESP32 en DFU con doble pulsación rápida de RESET.")
        return False

    if "2341:0070" not in dfu_output:
        print("[error] Se detectó un dispositivo DFU, pero no es el Nano ESP32 esperado 2341:0070.")
        return False

    upload_cmd = [
        DFU_UTIL,
        "--device", DFU_DEVICE,
        "-D", bin_path,
        "-R"
    ]

    print(f"[debug] Subiendo firmware por DFU usando {DFU_UTIL} ...")
    upload_result = subprocess.run(
        upload_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True
    )

    if upload_result.stdout:
        print(upload_result.stdout)
    if upload_result.stderr:
        print(upload_result.stderr)

    if upload_result.returncode != 0:
        print("[error] Falló la carga del firmware Arduino por DFU.")
        return False

    print("[debug] Carga Arduino completada correctamente.")
    time.sleep(5)
    return True


# =========================
# PROCESAMIENTO DEL UPDATE
# =========================
def process_python_update(python_dir):
    """
    Procesa la carpeta python:
    - lee readme.txt
    - si dice true, ejecuta script.py directamente
    """
    readme_path = os.path.join(python_dir, "readme.txt")
    status = normalize_bool_file(readme_path)

    if status is None:
        print("[debug] readme.txt de python inválido o ausente. Se ignora.")
        return

    if status is False:
        print("[debug] python/readme.txt = false -> no hay actualización Python.")
        return

    print("[debug] python/readme.txt = true -> hay actualización Python.")

    script_path = os.path.join(python_dir, PYTHON_SCRIPT_NAME)

    if not os.path.isfile(script_path):
        print(f"[debug] No se encontró {PYTHON_SCRIPT_NAME} dentro de la carpeta python.")
        return

    stop_running_code(exclude_pid=my_pid)
    run_code_in_background(script_path)


def process_arduino_update(arduino_dir):
    """
    Procesa la carpeta arduino:
    - lee readme.txt
    - si dice true, busca el .ino.bin y lo sube por DFU
    """
    readme_path = os.path.join(arduino_dir, "readme.txt")
    status = normalize_bool_file(readme_path)

    if status is None:
        print("[debug] readme.txt de arduino inválido o ausente. Se ignora.")
        return

    if status is False:
        print("[debug] arduino/readme.txt = false -> no hay actualización Arduino.")
        return

    print("[debug] arduino/readme.txt = true -> hay actualización Arduino.")
    upload_arduino_bin(arduino_dir)


def process_downloaded_update(hash_value):
    """
    Descarga, descomprime y procesa las carpetas arduino/ y python/.
    """
    ensure_dir(DESKTOP_UPDATES_DIR)

    archive_path = download_ipfs_archive(hash_value, DESKTOP_UPDATES_DIR)
    if not archive_path:
        print("[debug] No se pudo descargar el archivo comprimido.")
        return

    extract_dir = extract_archive(archive_path, DESKTOP_UPDATES_DIR)
    if not extract_dir:
        print("[debug] No se pudo descomprimir el archivo descargado.")
        return

    update_root = resolve_update_root(extract_dir)
    print(f"[debug] Raíz de actualización detectada en: {update_root}")

    arduino_dir = os.path.join(update_root, "arduino")
    python_dir = os.path.join(update_root, "python")

    if os.path.isdir(python_dir):
        process_python_update(python_dir)
    else:
        print("[debug] No existe carpeta python en la actualización.")

    if os.path.isdir(arduino_dir):
        process_arduino_update(arduino_dir)
    else:
        print("[debug] No existe carpeta arduino en la actualización.")


# =========================
# SERIAL
# =========================
def find_ports():
    """
    Devuelve el dispositivo serial fijo definido por udev.
    """
    return SERIAL_PORT


def close_serial():
    global ser
    if ser and ser.is_open:
        print("\n[debug] Cerrando el puerto serial...")
        ser.close()
        print("\n[debug] Puerto serial cerrado correctamente")


def signal_handler(sig, frame):
    print("\n[debug] Señal de cierre recibida (Ctrl+C o similar).")
    stop_tracked_python_process()
    close_serial()
    stop_ipfs_daemon()
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


# =========================
# MAIN
# =========================
try:
    my_pid = os.getpid()

    ensure_dir(DESKTOP_UPDATES_DIR)

    if not start_ipfs_daemon():
        print("[error] No fue posible iniciar el daemon IPFS.")
        sys.exit(1)

    # Se espera al inicio para aumentar la probabilidad de que la primera
    # actualización encuentre proveedores inmediatamente. Si no hay peers,
    # el nodo continúa escuchando el puerto serial y volverá a comprobar
    # la red antes de cada descarga.
    if not wait_for_ipfs_network(
        timeout_seconds=IPFS_NETWORK_WAIT_AT_START,
        minimum_tcp_peers=IPFS_MIN_TCP_PEERS
    ):
        print(
            "[warning] El daemon está activo, pero todavía no tiene peers TCP. "
            "Se continuará esperando comandos y se reintentará antes de descargar."
        )

    port = find_ports()

    if not os.path.exists(port):
        print(f"[error] No existe el dispositivo '{port}'. Verificá tu regla udev y reconectá el adaptador.")
        stop_ipfs_daemon()
        sys.exit(1)

    print(f"[debug] Conectando al puerto: {port}")
    ser = serial.Serial(port, baudrate=BAUDRATE, timeout=1)
    print(f"[debug] Conectado al puerto: {port}")

    while True:
        line = ser.readline().decode('utf-8', errors='ignore').strip()

        if line:
            print(f"[debug] Recibido: {line}")

        if line.startswith("hash "):
            hash_value = line[5:].strip()

            if hash_value == "-":
                print("[debug] Hash ignorado: '-'")

            elif is_valid_ipfs_hash(hash_value):
                print(f"[HASH RECIBIDO] {hash_value}")
                print("[debug] Hash válido.")
                print("[debug] Recuperando archivo comprimido desde IPFS...")
                process_downloaded_update(hash_value)

            else:
                print(f"[debug] Hash inválido (longitud {len(hash_value)}): {hash_value}")

except Exception as e:
    print(f"[debug] Error: {e}")

finally:
    stop_tracked_python_process()
    close_serial()
    stop_ipfs_daemon2()
    print("=================================")
    print("PINV0127 AUTONOMOUS NODE FINISHED")
    print("=================================\n.\n.\n.")
