from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ProtocolPort(Protocol):
    """Interfaz abstracta para adaptadores de protocolo de campo
    (BACnet, Modbus, MQTT, simuladores).

    Los servicios solo dependen de este Protocol — nunca de BAC0,
    pymodbus, paho-mqtt ni ninguna librería de protocolo concreta.
    """

    async def connect(self) -> None:
        """Establece la conexión con el dispositivo o broker."""
        ...

    async def disconnect(self) -> None:
        """Cierra la conexión limpiamente."""
        ...

    async def read_point(self, point_id: str) -> Any:
        """Lee el valor actual de un punto por su identificador."""
        ...

    async def write_point(self, point_id: str, value: Any) -> None:
        """Escribe un valor en un punto."""
        ...

    async def scan(self) -> list[dict[str, Any]]:
        """Descubre los puntos disponibles en el dispositivo/broker."""
        ...

    async def health_check(self) -> bool:
        """Verifica que el protocolo está conectado y operativo."""
        ...
