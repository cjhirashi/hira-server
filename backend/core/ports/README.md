# backend/core/ports/

Interfaces abstractas (Protocols de Python) que definen los contratos de infraestructura.

## Regla de oro

**`services/` solo importa de `core/ports/`. Nunca de `adapters/` directamente.**

Si un módulo en `services/` importa `psycopg2`, `sqlalchemy`, `asyncpg`, `BAC0`, `paho` o cualquier librería de infraestructura, está violando la arquitectura hexagonal.

## Archivos

| Archivo | Propósito |
|---------|-----------|
| `database_port.py` | `DatabasePort` — contrato para acceso a la DB: `get_session()`, `execute()`, `create_tables()`, `health_check()` |
| `protocol_port.py` | `ProtocolPort` — contrato para adaptadores de campo: `connect()`, `disconnect()`, `read_point()`, `write_point()`, `scan()`, `health_check()` |

## Cómo funciona

Un `Protocol` de Python define métodos sin implementación. Las clases concretas en `adapters/` los implementan. `adapters/factory.py` selecciona cuál usar según `HIRA_DEPLOY_MODE`.

Los servicios reciben el adaptador por inyección de dependencias — nunca lo instancian directamente.

## Cómo agregar un port nuevo

1. Crear `backend/core/ports/nuevo_port.py` con un `Protocol` y sus métodos abstractos
2. Crear el adaptador concreto en `backend/adapters/`
3. Registrarlo en `adapters/factory.py`
4. Exportarlo desde `core/ports/__init__.py`
