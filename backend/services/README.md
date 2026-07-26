# backend/services/

Lógica de negocio de Hira.

## Regla crítica

**Este módulo solo importa de `core/ports/`. Nunca de `adapters/`.**

Si ves un import de `sqlalchemy`, `asyncpg`, `psycopg2`, `BAC0`, `paho` o similar dentro de `services/`, es una violación de la arquitectura hexagonal. La implementación concreta se inyecta vía `adapters/factory.py`.

## Cómo funciona

Un servicio recibe el adaptador como dependencia (inyectado desde el router o el lifespan):

```python
from core.ports import DatabasePort

class DeviceService:
    def __init__(self, db: DatabasePort) -> None:
        self._db = db

    async def list_devices(self) -> list[dict]:
        async with self._db.get_session() as session:
            ...
```

## Archivos

| Archivo | Propósito |
|---|---|
| `alarm_engine.py` | Motor de evaluación de condiciones de alarma |
| `history_writer.py` | Escritura de históricos en TimescaleDB con control de intervalo mínimo |
| `ai_config_service.py` | Lectura y escritura de configuración del Agente IA (Fernet-encrypted API key) |
| `ai_agent.py` | Agente LangChain LCEL con 6 tools del sistema; build_agent + invoke_agent |

> **Nota:** `ai_config_service.py` y `ai_agent.py` usan psycopg2 + redis-py sincrónicos directamente, siguiendo el mismo patrón de `hira_api.py`. Esto es una excepción documentada a la regla hexagonal, necesaria porque se invocan desde contextos FastAPI async vía `run_in_executor`. Ver `DEVIATIONS.md` DEV-007.

## alarm_engine.py

`AlarmEngine` evalúa si un valor de punto cumple una condición definida en `AlarmDefinition`.

**Ciclo de vida de una alarma:**
1. Valor supera umbral → crea `AlarmEvent(status="active")` en PostgreSQL → publica en `alarm:updates` Redis
2. Valor ya no supera umbral → `AlarmEvent.status = "resolved"` → publica en `alarm:updates` Redis
3. Usuario reconoce → router `/alarms/{id}/acknowledge` → `status = "acknowledged"`

**Caché:** Las definiciones habilitadas por `point_id` se cachean en memoria (TTL 60s) para no consultar la BD en cada ciclo de evaluación (cada 10s). Se invalida llamando `alarm_engine.invalidate_cache(point_id)` al crear/modificar una definición.

**Condiciones soportadas:** `gt` (>), `lt` (<), `eq` (==), `between` (threshold ≤ value ≤ threshold_high)

## history_writer.py

`HistoryWriter` inserta registros en `point_history` (TimescaleDB) respetando el intervalo mínimo configurado por punto.

**Lógica de intervalo mínimo:**
1. Al recibir un valor, consulta `point:{id}:last_recorded` en Redis.
2. Si el tiempo transcurrido desde la última escritura es menor que `history_interval_seconds` → no-op silencioso.
3. Si el tiempo ha pasado (o nunca se registró) → inserta en `point_history` y actualiza `point:{id}:last_recorded`.

**Integración:** Se llama desde `bacnet_poller._poll_device()` después de publicar en Redis, con la sesión y el cliente Redis del worker. Los errores de inserción se loguean y no interrumpen el pipeline de polling.

**TTL Redis:** La clave `last_recorded` tiene TTL de 3600s para limpiar puntos que dejan de ser monitoreados.
