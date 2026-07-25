"""
Router WebSocket — endpoint GET /ws.

Autentica el JWT via query param ?token=, acepta la conexión y mantiene
el loop de recepción de mensajes del cliente hasta que desconecta.
"""
import json

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from core.logger import get_logger
from core.security import verify_token
from websocket.manager import manager

logger = get_logger(__name__)

router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(default=""),
) -> None:
    payload = verify_token(token) if token else None
    if payload is None:
        await websocket.accept()
        await websocket.send_text(
            json.dumps({"event": "error", "data": {"code": 4001, "message": "Unauthorized"}})
        )
        await websocket.close(code=4001)
        return

    client_id = await manager.connect(websocket)
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
                event = msg.get("event", "")
                logger.debug("Mensaje WS recibido", extra={"client_id": client_id, "event": event})
                # Sprint 3: subscribe/unsubscribe son no-ops (broadcast a todos)
                # Sprint 4 implementará filtrado por suscripción
            except json.JSONDecodeError:
                logger.warning("Mensaje WS inválido", extra={"client_id": client_id})
    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(client_id)
