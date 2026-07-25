# backend/websocket/

Infraestructura de tiempo real: gestión de conexiones WebSocket y suscripción a Redis pub/sub.

## Archivos

| Archivo | Descripción |
|---|---|
| `manager.py` | `ConnectionManager` — registro de clientes WebSocket activos con asyncio.Lock |
| `redis_subscriber.py` | Tarea asyncio que suscribe canales Redis y retransmite eventos a todos los clientes WS |

## Cómo funciona

1. **Al arrancar el backend** (`main.py` lifespan), se llama `start_subscriber()` que crea una tarea asyncio indefinida escuchando los canales Redis `point:*:updates` y `alarm:updates`.
2. **Cuando un cliente se conecta** a `GET /ws?token=<jwt>`, `manager.connect()` acepta la conexión, asigna un `client_id` UUID y envía `connection:ack`.
3. **Cuando un poller publica** en `point:{id}:updates`, el subscriber recibe el mensaje y llama `manager.broadcast()` para enviarlo a todos los clientes como evento `point:update`.
4. **Al desconectar** un cliente (normal o por error), `manager.disconnect()` lo elimina del registro.
5. **Al apagar el backend**, `stop_subscriber()` cancela la tarea asyncio limpiamente.

## Dependencias

- `fastapi.WebSocket` — transporte WebSocket
- `redis.asyncio` — suscripción pub/sub a canales Redis
- `core.config` — URL de Redis (`settings.redis_url`)
- `core.logger` — logging estructurado JSON
