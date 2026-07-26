# backend/core/

Módulos transversales del backend. Todos los demás módulos importan de aquí — nunca al revés.

## Archivos

| Archivo | Propósito |
|---------|-----------|
| `config.py` | Configuración centralizada con `pydantic-settings`. Lee todas las variables de entorno al arrancar y falla rápido si falta alguna obligatoria |
| `logger.py` | Logger JSON estructurado. Todos los módulos hacen `from core.logger import get_logger`. Cero `print()` en producción |
| `middleware.py` | `CorrelationIdMiddleware`: lee o genera `X-Trace-ID` por request y lo almacena en un `ContextVar` para que todos los loggers lo lean automáticamente |
| `redis.py` | Cliente Redis async singleton (`get_redis`). Funciones auxiliares `get_rbac_key` y `get_refresh_key` para claves con namespace |
| `security.py` | bcrypt (`hash_password`, `verify_password`), JWT HS256 (`create_access_token`, `create_refresh_token`, `decode_token`) y dependencia FastAPI `get_current_user` |
| `rbac.py` | Carga y caché de permisos RBAC en Redis. Dependencia `require_permission("module:level")` para proteger endpoints |
| `hira_api.py` | API interna inyectada en scripts de lógica. Clase `HiraAPI` con `read()`, `write()`, `subscribe()`, `log()`. Se instancia por ciclo de ejecución del worker |
| `ports/` | Interfaces abstractas (Protocols de Python) que definen los contratos que deben cumplir los adaptadores |

## Cómo funciona

1. `main.py` importa `settings` de `config.py` al arrancar → valida env vars
2. `main.py` registra `CorrelationIdMiddleware` antes de cualquier otro middleware
3. Cada request: el middleware genera un `trace_id` y lo guarda en `trace_id_var` (ContextVar)
4. Cualquier módulo que llame a `get_logger(__name__)` y luego `logger.info(...)` emitirá JSON con ese `trace_id` incluido automáticamente

## Cómo importar el logger

```python
from core.logger import get_logger

logger = get_logger(__name__)
logger.info("Mensaje", extra={"key": "value"})
logger.error("Error inesperado", exc_info=exc)
```

Para activar DEBUG: `LOG_LEVEL=DEBUG` en `.env` o en `docker-compose.dev.yml`.

## hira_api.py — API interna para scripts de lógica

```python
from core.hira_api import HiraAPI

hira = HiraAPI(session_factory, redis_client)

valor = hira.read("nombre_punto")   # → float | None — lee de Redis
hira.write("nombre_punto", 22.5)    # → bool — escribe en Redis + publica en WebSocket
hira.log("Mensaje de debug")        # → None — captura en output del ciclo
```

**Restricciones del sandbox (RestrictedPython):**
- No se puede importar módulos externos (`import os`, `import subprocess`, etc.)
- No se puede usar `open`, `exec`, `eval` directamente
- Solo se expone la instancia `hira` y las funciones seguras de `safe_globals`

**Cómo agregar nuevos métodos:**
1. Agregar el método a `HiraAPI` en `hira_api.py`
2. No requiere cambiar el worker — `hira` se inyecta completo en el contexto de ejecución
