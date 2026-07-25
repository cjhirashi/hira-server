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
