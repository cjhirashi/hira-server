# adapters/protocol/

## Propósito
Implementaciones concretas del `ProtocolPort` (`core/ports/protocol_port.py`) para cada protocolo industrial. Aíslan la lógica de comunicación del resto del sistema: `services/` nunca importa de aquí directamente.

## Archivos

| Archivo | Protocolo | Descripción |
|---|---|---|
| `bacnet_adapter.py` | BACnet/IP | Usa BAC0 (síncrono) bridgeado a asyncio vía `run_in_executor` |
| `mqtt_adapter.py` | MQTT | Usa paho-mqtt con suscripción wildcard `#`; callbacks bridgeados a asyncio |

## Cómo funciona

**BACnet:**
1. `connect()` → `BAC0.lite()` en executor (bloquea hasta que la red BACnet responde).
2. `scan()` → Who-Is broadcast, espera 3s, retorna lista de `{instance, ip, name, vendor}`.
3. `read_point(device_id, point_address)` → lee `presentValue`; en error retorna `quality: "bad"`.
4. `write_point(device_id, point_address, value)` → escribe con prioridad 8; usa `asyncio.Lock` por `device_id` para serializar escrituras concurrentes.

**MQTT:**
1. `connect()` → `client.connect()` + `loop_start()` + subscribe `#`.
2. `on_message` callback → `asyncio.run_coroutine_threadsafe(_store_in_redis(...))`.
3. `read_point(topic)` → lee `mqtt:topic:{topic}` de Redis (TTL 300s).
4. `write_point(topic, value)` → `client.publish()` con payload JSON, QoS 1.

## Dependencias

- `core/ports/protocol_port.py` — Protocol que estos adapters implementan
- `BAC0` — biblioteca BACnet (solo en `bacnet_adapter.py`, import lazy)
- `paho-mqtt` — cliente MQTT
- `core/redis.py` — almacén de valores MQTT recibidos
- `adapters/factory.py` — punto de entrada para obtener el adaptador correcto
