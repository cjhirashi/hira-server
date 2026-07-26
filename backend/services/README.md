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

## alarm_engine.py

`AlarmEngine` evalúa si un valor de punto cumple una condición definida en `AlarmDefinition`.

**Ciclo de vida de una alarma:**
1. Valor supera umbral → crea `AlarmEvent(status="active")` en PostgreSQL → publica en `alarm:updates` Redis
2. Valor ya no supera umbral → `AlarmEvent.status = "resolved"` → publica en `alarm:updates` Redis
3. Usuario reconoce → router `/alarms/{id}/acknowledge` → `status = "acknowledged"`

**Caché:** Las definiciones habilitadas por `point_id` se cachean en memoria (TTL 60s) para no consultar la BD en cada ciclo de evaluación (cada 10s). Se invalida llamando `alarm_engine.invalidate_cache(point_id)` al crear/modificar una definición.

**Condiciones soportadas:** `gt` (>), `lt` (<), `eq` (==), `between` (threshold ≤ value ≤ threshold_high)
