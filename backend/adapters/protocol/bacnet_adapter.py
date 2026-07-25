"""
Adaptador BACnet — implementa ProtocolPort usando BAC0.

BAC0 es síncrono internamente; todas las operaciones BACnet se ejecutan
en un ThreadPoolExecutor para no bloquear el event loop de asyncio.

Un asyncio.Lock por device_id garantiza que lecturas y escrituras
concurrentes al mismo controlador se serialicen (evita colisiones BACnet).
"""
import asyncio
from datetime import datetime, timezone
from typing import Any

from core.logger import get_logger

logger = get_logger(__name__)


class BACnetAdapter:
    """Adaptador BACnet/IP usando BAC0 como biblioteca de campo."""

    def __init__(self) -> None:
        self._bacnet: Any = None
        self._locks: dict[str, asyncio.Lock] = {}
        self._executor = None

    def _get_lock(self, device_id: str) -> asyncio.Lock:
        if device_id not in self._locks:
            self._locks[device_id] = asyncio.Lock()
        return self._locks[device_id]

    async def connect(self, config: dict[str, Any] | None = None) -> None:
        """Inicializa la instancia BAC0. Operación síncrona en thread pool."""
        import BAC0

        loop = asyncio.get_event_loop()

        def _init():
            ip = (config or {}).get("ip", None)
            return BAC0.lite(ip=ip) if ip else BAC0.lite()

        self._bacnet = await loop.run_in_executor(self._executor, _init)
        logger.info("BACnet conectado", extra={"config": config})

    async def disconnect(self) -> None:
        if self._bacnet is not None:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(self._executor, self._bacnet.disconnect)
            self._bacnet = None
            logger.info("BACnet desconectado")

    async def scan(self) -> list[dict[str, Any]]:
        """
        Who-Is broadcast. Retorna lista de dispositivos con
        instance, ip, name y vendor.
        """
        if self._bacnet is None:
            raise RuntimeError("BACnet no inicializado — llamar connect() primero")

        loop = asyncio.get_event_loop()

        def _whois():
            self._bacnet.whois()
            import time
            time.sleep(3)
            devices = []
            for dev in self._bacnet.discoveredDevices or []:
                try:
                    devices.append({
                        "instance": dev[1],
                        "ip": dev[0].split(":")[0],
                        "name": str(dev[2]) if len(dev) > 2 else "Unknown",
                        "vendor": str(dev[3]) if len(dev) > 3 else "Unknown",
                        "protocol": "bacnet",
                    })
                except Exception:
                    pass
            return devices

        discovered = await loop.run_in_executor(self._executor, _whois)
        logger.info("BACnet scan completado", extra={"found": len(discovered)})
        return discovered

    async def read_point(self, device_id: str, point_address: str) -> dict[str, Any]:
        """
        Lee un punto BACnet. point_address formato: "IP objectType instance"
        e.g. "192.168.1.100 analogInput 1"

        Retorna {"value": float|bool|str, "quality": "good|bad", "timestamp": ISO8601}
        """
        if self._bacnet is None:
            return {"value": None, "quality": "bad", "timestamp": _now()}

        lock = self._get_lock(device_id)
        loop = asyncio.get_event_loop()

        async with lock:
            def _read():
                return self._bacnet.read(f"{point_address} presentValue")

            try:
                value = await loop.run_in_executor(self._executor, _read)
                return {"value": float(value) if value is not None else None,
                        "quality": "good" if value is not None else "uncertain",
                        "timestamp": _now()}
            except Exception as exc:
                logger.warning("BACnet read error",
                               extra={"device_id": device_id, "point": point_address, "error": str(exc)})
                return {"value": None, "quality": "bad", "timestamp": _now()}

    async def write_point(self, device_id: str, point_address: str, value: Any) -> bool:
        """
        Escribe un valor BACnet. point_address formato: "IP objectType instance"
        Retorna True si confirmado, False si falló.
        """
        if self._bacnet is None:
            raise RuntimeError("BACnet no inicializado")

        lock = self._get_lock(device_id)
        loop = asyncio.get_event_loop()

        async with lock:
            def _write():
                self._bacnet.write(f"{point_address} presentValue {value} - 8")

            try:
                await loop.run_in_executor(self._executor, _write)
                logger.info("BACnet write OK",
                            extra={"device_id": device_id, "point": point_address, "value": value})
                return True
            except Exception as exc:
                logger.error("BACnet write error",
                             extra={"device_id": device_id, "point": point_address, "error": str(exc)})
                return False

    async def health_check(self) -> bool:
        return self._bacnet is not None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")
