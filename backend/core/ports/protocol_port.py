from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ProtocolPort(Protocol):
    """Interfaz abstracta para adaptadores de protocolo de campo
    (BACnet, Modbus, MQTT, simuladores).

    Los servicios solo dependen de este Protocol — nunca de BAC0,
    pymodbus, paho-mqtt ni ninguna librería de protocolo concreta.
    """

    async def connect(self, config: dict[str, Any] | None = None) -> None:
        """Establece la conexión con el dispositivo o broker."""
        ...

    async def disconnect(self) -> None:
        """Cierra la conexión limpiamente."""
        ...

    async def scan(self) -> list[dict[str, Any]]:
        """
        Descubre dispositivos en la red.
        Retorna lista de dicts: [{instance, ip, name, vendor, ...}]
        """
        ...

    async def read_point(self, device_id: str, point_address: str) -> dict[str, Any]:
        """
        Lee el valor actual de un punto.
        Retorna: {"value": Any, "quality": "good|bad|uncertain", "timestamp": str ISO8601}
        Si el dispositivo no responde → quality="bad", value=None.
        """
        ...

    async def write_point(self, device_id: str, point_address: str, value: Any) -> bool:
        """
        Escribe un valor en un punto.
        Retorna True si la escritura fue confirmada, False si no.
        Lanza excepción si el dispositivo está offline.
        """
        ...

    async def health_check(self) -> bool:
        """Verifica que el protocolo está conectado y operativo."""
        ...
