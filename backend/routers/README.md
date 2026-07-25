# backend/routers/

Endpoints FastAPI. Cada router implementa el contrato definido en `docs/openapi.yaml`.

## Convención

- Un archivo por dominio: `monitor.py`, `auth.py`, `devices.py`, etc.
- Cada router se registra en `main.py` con `app.include_router(...)`
- **El endpoint debe existir en `docs/openapi.yaml` antes de implementarlo**

## Archivos

| Archivo | Prefijo | Propósito |
|---------|---------|-----------|
| `monitor.py` | `/health` | Estado de todos los servicios (público) |
| `auth.py` | `/auth` | Login, refresh de token, logout |
| `users.py` | `/users` | CRUD de usuarios con RBAC |
| `devices.py` | `/api/v1/devices` | CRUD de dispositivos físicos + scan de red |
| `points.py` | `/api/v1/points` | Lectura y escritura de valores de puntos desde Redis / adaptadores |
| `simulators.py` | `/api/v1/simulators` | Ciclo de vida de simuladores: crear, start, stop |

## Cómo funciona

1. FastAPI enruta la petición al handler correspondiente.
2. El handler valida permisos con `require_permission(...)` de `core/rbac.py`.
3. Para operaciones de datos: usa `get_db_adapter()` → sesión SQLAlchemy.
4. Para operaciones de protocolo: usa `get_protocol_adapter(proto)` → adaptador concreto.
5. Valores en tiempo real se leen/escriben desde Redis (`core/redis.py`).

## Cómo agregar un router nuevo

1. Añadir los endpoints al contrato en `docs/openapi.yaml`
2. Crear `backend/routers/nuevo_dominio.py` con un `APIRouter`
3. Registrarlo en `main.py`: `app.include_router(nuevo_router, prefix="/api/v1")`
