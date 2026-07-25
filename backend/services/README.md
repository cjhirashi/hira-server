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

## Contenido actual

Vacío en Sprint 0. Los servicios se crean a partir de Sprint 1 (Auth + RBAC).
