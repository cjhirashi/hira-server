# backend/

Backend de Hira: API REST con FastAPI, lógica de negocio, modelos de datos y workers Celery.

## Punto de entrada

`main.py` — inicializa la aplicación FastAPI, registra middlewares y monta los routers.

## Cómo arranca

```bash
# Desarrollo (hot-reload, vía docker-compose.dev.yml)
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Producción
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 2
```

## Estructura interna

| Carpeta | Propósito |
|---------|-----------|
| `core/` | Módulos transversales: config, logger, middleware, ports |
| `adapters/` | Implementaciones concretas de los ports (PostgreSQL, SQLite, protocolos) |
| `models/` | ORM models SQLAlchemy |
| `schemas/` | Pydantic schemas (request / response) |
| `routers/` | Endpoints FastAPI |
| `services/` | Lógica de negocio (solo importa de `core/ports/`) |
| `workers/` | Celery workers |
| `websocket/` | Gestión de conexiones WebSocket |
| `alembic/` | Migraciones de base de datos |

## Dependencias externas

`requirements.txt` — todas las dependencias Python con versiones fijas.
