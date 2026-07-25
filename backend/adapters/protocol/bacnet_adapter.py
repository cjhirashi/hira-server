"""
Adaptador BACnet — implementa ProtocolPort usando BAC0 2024.x (bacpypes3).

Diseño: sin estado de conexión persistente.

read_point() y write_point() crean una instancia BAC0.lite() temporal dentro
de asyncio.to_thread() + asyncio.run(). Esto los hace seguros desde cualquier
contexto (FastAPI con starlette/anyio y Celery con asyncio.run propio),
porque cada operación corre en su propio hilo con loop aislado.

scan() sigue el mismo patrón.

connect() / disconnect() son no-ops que satisfacen el contrato ProtocolPort
para compatibilidad con el patrón genérico de los routers y el poller.

Separación de puerto 47808 en docker-compose:
  celery-worker (172.19.0.x) → queue "simulators" → BAC0 como servidor
  celery-poller (172.19.0.y) → queue "protocols"  → BAC0 como cliente (lector)
  Cada operación de lectura/escritura crea su propia instancia temporal.
"""
import asyncio
from datetime import datetime, timezone
from typing import Any

from core.logger import get_logger

logger = get_logger(__name__)


class BACnetAdapter:
    """Adaptador BACnet/IP sin estado — todas las operaciones son auto-contenidas."""

    async def connect(self, config: dict[str, Any] | None = None) -> None:
        """No-op: el adaptador no mantiene conexión persistente."""

    async def disconnect(self) -> None:
        """No-op: el adaptador no mantiene conexión persistente."""

    async def scan(self) -> list[dict[str, Any]]:
        """Who-Is broadcast. Cada llamada crea una instancia BAC0 temporal."""
        def _run() -> list[dict[str, Any]]:
            async def _coro() -> list[dict[str, Any]]:
                import BAC0
                bacnet = BAC0.lite()
                await asyncio.sleep(1)
                try:
                    iams = await bacnet.who_is(timeout=3)
                    devices = []
                    for iam in (iams or []):
                        try:
                            addr = str(getattr(iam, "pduSource", ""))
                            instance = int(getattr(iam, "iAmDeviceIdentifier", (None, 0))[1])
                            devices.append({
                                "instance": instance,
                                "ip": addr.split(":")[0] if addr else "unknown",
                                "name": "Unknown",
                                "vendor": str(getattr(iam, "vendorID", "Unknown")),
                                "protocol": "bacnet",
                            })
                        except Exception:
                            pass
                    return devices
                finally:
                    await bacnet._disconnect()
            return asyncio.run(_coro())

        discovered = await asyncio.to_thread(_run)
        logger.info("BACnet scan completado", extra={"found": len(discovered)})
        return discovered

    async def read_point(self, device_id: str, point_address: str) -> dict[str, Any]:
        """
        Lee un punto BACnet.
        point_address formato: "IP objectType instance"  e.g. "192.168.1.10 analogInput 1"
        BAC0 2024.x: read() es async def — debe ejecutarse en asyncio.run() propio.
        """
        addr = point_address
        dev = device_id

        def _run() -> dict[str, Any]:
            async def _coro() -> dict[str, Any]:
                import BAC0
                bacnet = BAC0.lite()
                await asyncio.sleep(0.5)
                try:
                    value = await bacnet.read(f"{addr} presentValue")
                    return {
                        "value": float(value) if value is not None else None,
                        "quality": "good" if value is not None else "uncertain",
                        "timestamp": _now(),
                    }
                except Exception as exc:
                    logger.warning("BACnet read error",
                                   extra={"device_id": dev, "point": addr, "error": str(exc)})
                    return {"value": None, "quality": "bad", "timestamp": _now()}
                finally:
                    await bacnet._disconnect()
            return asyncio.run(_coro())

        return await asyncio.to_thread(_run)

    async def write_point(self, device_id: str, point_address: str, value: Any) -> bool:
        """
        Escribe un valor BACnet.
        BAC0 2024.x: _write() es la implementación async de write().
        """
        addr = point_address
        val = value
        dev = device_id

        def _run() -> bool:
            async def _coro() -> bool:
                import BAC0
                bacnet = BAC0.lite()
                await asyncio.sleep(0.5)
                try:
                    await bacnet._write(f"{addr} presentValue {val} - 8")
                    logger.info("BACnet write OK",
                                extra={"device_id": dev, "point": addr, "value": val})
                    return True
                except Exception as exc:
                    logger.error("BACnet write error",
                                 extra={"device_id": dev, "point": addr, "error": str(exc)})
                    return False
                finally:
                    await bacnet._disconnect()
            return asyncio.run(_coro())

        return await asyncio.to_thread(_run)

    async def health_check(self) -> bool:
        return True


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")
