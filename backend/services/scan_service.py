"""
Servicio de escaneo automático de dispositivos en red.

Tres protocolos soportados:
- BACnet: Who-Is broadcast via BAC0
- Modbus TCP: scan de rango IP + verificación de conectividad
- MQTT: suscripción wildcard '#' durante N segundos

Cada función retorna una lista de ScanCandidate dicts.
"""
import socket
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from core.logger import get_logger

logger = get_logger(__name__)


def _parse_ip_range(ip_range: str) -> list[str]:
    """
    Parsea ip_range en formato "192.168.1.1-254" o "192.168.1.1-192.168.1.254".
    Retorna lista de IPs.
    """
    if "-" not in ip_range:
        raise ValueError(f"Formato de rango IP inválido: '{ip_range}'. Use 'A.B.C.D-E' o 'A.B.C.D-A.B.C.E'")

    parts = ip_range.split("-", 1)
    start_ip = parts[0].strip()
    end_part = parts[1].strip()

    octets = start_ip.split(".")
    if len(octets) != 4:
        raise ValueError(f"IP de inicio inválida: '{start_ip}'")

    # Si end_part es sólo el último octeto
    if "." not in end_part:
        try:
            end_octet = int(end_part)
            start_octet = int(octets[3])
        except ValueError:
            raise ValueError(f"Rango inválido: '{ip_range}'")
        if not (0 <= start_octet <= 255 and 0 <= end_octet <= 255):
            raise ValueError(f"Octetos fuera de rango en '{ip_range}'")
        prefix = ".".join(octets[:3])
        return [f"{prefix}.{i}" for i in range(start_octet, end_octet + 1)]

    # Si end_part es IP completa
    end_octets = end_part.split(".")
    if len(end_octets) != 4:
        raise ValueError(f"IP de fin inválida: '{end_part}'")
    try:
        start_int = sum(int(o) << (8 * (3 - i)) for i, o in enumerate(octets))
        end_int = sum(int(o) << (8 * (3 - i)) for i, o in enumerate(end_octets))
    except ValueError:
        raise ValueError(f"Rango IP inválido: '{ip_range}'")
    if start_int > end_int:
        raise ValueError(f"IP de inicio mayor que IP de fin en '{ip_range}'")

    ips = []
    for n in range(start_int, end_int + 1):
        ips.append(f"{(n>>24)&255}.{(n>>16)&255}.{(n>>8)&255}.{n&255}")
    return ips


def scan_bacnet(timeout_seconds: int = 5) -> list[dict]:
    """
    Ejecuta Who-Is broadcast en la red local via BAC0.
    Retorna lista de ScanCandidate dicts.
    Si BAC0 falla → retorna [] y loguea el error.
    """
    candidates: list[dict] = []
    try:
        import BAC0
        network = BAC0.lite()
        time.sleep(timeout_seconds)
        for device in network.discoveredDevices or []:
            try:
                addr = str(device[1]) if isinstance(device, tuple) else str(device)
                dev_id = device[0] if isinstance(device, tuple) else None
                candidates.append({
                    "protocol": "bacnet",
                    "address": addr,
                    "name": None,
                    "metadata": {"device_id": dev_id},
                })
            except Exception:
                pass
        try:
            network.disconnect()
        except Exception:
            pass
    except Exception as exc:
        logger.error("scan_bacnet error", extra={"error": str(exc)})
    return candidates


def _check_modbus_host(ip: str, port: int, timeout: float) -> dict | None:
    """Intenta TCP connect a ip:port. Si conecta, verifica unit IDs 1-10."""
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            pass
    except (socket.timeout, ConnectionRefusedError, OSError):
        return None

    # Confirmar que es Modbus intentando leer registros en unit IDs comunes
    responding_units: list[int] = []
    try:
        from pymodbus.client import ModbusTcpClient
        client = ModbusTcpClient(host=ip, port=port)
        if client.connect():
            for uid in range(1, 11):
                try:
                    rr = client.read_holding_registers(0, count=1, slave=uid)
                    if not rr.isError():
                        responding_units.append(uid)
                except Exception:
                    pass
            client.close()
    except Exception:
        pass

    return {
        "protocol": "modbus",
        "address": f"{ip}:{port}",
        "name": None,
        "metadata": {"unit_ids_responding": responding_units},
    }


def scan_modbus(ip_range: str, port: int = 502, timeout_per_host: float = 1.0) -> list[dict]:
    """
    Parsea ip_range → itera IPs con ThreadPoolExecutor.
    Retorna candidatos Modbus TCP que responden al puerto dado.
    """
    ips = _parse_ip_range(ip_range)
    candidates: list[dict] = []

    max_workers = min(50, len(ips))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_check_modbus_host, ip, port, timeout_per_host): ip for ip in ips}
        for future in as_completed(futures):
            try:
                result = future.result()
                if result is not None:
                    candidates.append(result)
            except Exception as exc:
                logger.warning("scan_modbus host error", extra={"ip": futures[future], "error": str(exc)})

    return candidates


def scan_mqtt(duration_seconds: int = 10) -> list[dict]:
    """
    Conecta al broker MQTT configurado en settings, suscribe a '#' durante
    duration_seconds segundos, recopila topics únicos publicados.
    Retorna lista de ScanCandidate por topic.
    """
    from core.config import settings
    import paho.mqtt.client as mqtt_client

    topics_seen: dict[str, str] = {}  # topic → last payload preview

    def on_message(client, userdata, message):
        topic = message.topic
        try:
            payload_preview = message.payload.decode("utf-8", errors="replace")[:100]
        except Exception:
            payload_preview = "<binary>"
        topics_seen[topic] = payload_preview

    client = mqtt_client.Client(mqtt_client.CallbackAPIVersion.VERSION2)
    client.username_pw_set(settings.mqtt_user, settings.mqtt_password)
    client.on_message = on_message

    candidates: list[dict] = []
    try:
        client.connect(settings.mqtt_broker_host, settings.mqtt_broker_port, keepalive=60)
        client.subscribe("#", qos=0)
        client.loop_start()
        time.sleep(duration_seconds)
        client.loop_stop()
        client.disconnect()

        for topic, payload_preview in topics_seen.items():
            candidates.append({
                "protocol": "mqtt",
                "address": None,
                "name": None,
                "metadata": {"topic": topic, "last_payload_preview": payload_preview},
            })
    except Exception as exc:
        logger.error("scan_mqtt error", extra={"error": str(exc)})

    return candidates
