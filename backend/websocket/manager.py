"""
ConnectionManager — gestión de clientes WebSocket activos.

Mantiene un registro de conexiones activas con asyncio.Lock para
thread-safety. Permite broadcast a todos los clientes o envío individual.
"""
import asyncio
import json
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import WebSocket

from core.logger import get_logger

logger = get_logger(__name__)


class ConnectionManager:
    def __init__(self) -> None:
        self._clients: dict[str, WebSocket] = {}
        self._lock = asyncio.Lock()

    @property
    def client_count(self) -> int:
        return len(self._clients)

    async def connect(self, websocket: WebSocket) -> str:
        """Acepta la conexión y retorna el client_id asignado."""
        await websocket.accept()
        client_id = str(uuid4())
        async with self._lock:
            self._clients[client_id] = websocket

        ack = {
            "event": "connection:ack",
            "data": {
                "client_id": client_id,
                "server_time": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            },
        }
        await websocket.send_text(json.dumps(ack))
        logger.info("Cliente WS conectado", extra={"client_id": client_id, "total": self.client_count})
        return client_id

    async def disconnect(self, client_id: str) -> None:
        async with self._lock:
            self._clients.pop(client_id, None)
        logger.info("Cliente WS desconectado", extra={"client_id": client_id, "total": self.client_count})

    async def broadcast(self, message: dict) -> None:
        """Envía un mensaje JSON a todos los clientes conectados."""
        if not self._clients:
            return
        text = json.dumps(message)
        async with self._lock:
            clients = list(self._clients.items())

        dead: list[str] = []
        for client_id, ws in clients:
            try:
                await ws.send_text(text)
            except Exception:
                dead.append(client_id)

        if dead:
            async with self._lock:
                for client_id in dead:
                    self._clients.pop(client_id, None)
            logger.warning("Clientes WS removidos por error de envío", extra={"removed": dead})

    async def send_to(self, client_id: str, message: dict) -> None:
        """Envía un mensaje a un cliente específico."""
        async with self._lock:
            ws = self._clients.get(client_id)
        if ws is None:
            return
        try:
            await ws.send_text(json.dumps(message))
        except Exception as exc:
            logger.warning("Error enviando a cliente", extra={"client_id": client_id, "error": str(exc)})
            await self.disconnect(client_id)


manager = ConnectionManager()
