# backend/adapters/

Implementaciones concretas de los ports definidos en `core/ports/`.

## Cómo funciona

`factory.py` lee `HIRA_DEPLOY_MODE` y devuelve la instancia correcta:

| Modo | Adaptador DB |
|------|-------------|
| `server` | `PostgreSQLAdapter` (TimescaleDB) |
| `studio` | `SQLiteAdapter` (archivo local) |

Los servicios llaman a `get_db_adapter()` de `factory.py` — nunca instancian los adaptadores directamente.

## Archivos

| Archivo | Propósito |
|---------|-----------|
| `factory.py` | Selector de adaptador según `HIRA_DEPLOY_MODE` |
| `db/postgresql_adapter.py` | `DatabasePort` sobre SQLAlchemy async + asyncpg |
| `db/sqlite_adapter.py` | `DatabasePort` sobre SQLAlchemy async + aiosqlite |
| `protocol/` | Adaptadores de protocolos de campo (BACnet, Modbus, MQTT) — Sprint 2+ |

## Cómo agregar un adaptador nuevo

1. Crear el archivo en la subcarpeta correspondiente (p.ej. `adapters/protocol/bacnet_adapter.py`)
2. Implementar todos los métodos del `Protocol` correspondiente
3. Registrar en `factory.py`
4. Añadir la dependencia a `requirements.txt`
