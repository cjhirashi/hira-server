# backend/models/

ORM models SQLAlchemy. Representan las tablas de la base de datos.

## Tablas y relaciones

```
users ──< user_roles >── roles ──< permissions
users ──< alarms (acknowledged_by)
users ──< logic_scripts (created_by)
users ──< engineering_sessions (integrator_user_id)

areas ──< devices ──< points ──< alarm_definitions ──< alarms
areas ──< points (directo, para puntos sin dispositivo asociado a un área)
                  └──< point_history  (hypertable TimescaleDB)

logic_scripts ──< script_executions

mimics
notifications
engineering_sessions
```

## Archivos

| Archivo | Tabla | Descripción |
|---------|-------|-------------|
| `base.py` | — | `DeclarativeBase` compartida por todos los modelos |
| `users.py` | `users` | Usuarios del sistema |
| `roles.py` | `roles` | Roles fijos: Admin, Operador, Visor |
| `permissions.py` | `permissions` | Permisos por rol, módulo y área |
| `user_roles.py` | `user_roles` | Relación N:M usuarios ↔ roles |
| `areas.py` | `areas` | Áreas del proyecto (Sprint 7 — Configurador) |
| `devices.py` | `devices` | Dispositivos de campo (BACnet, Modbus, MQTT, simuladores) |
| `points.py` | `points` | Puntos de datos dentro de cada dispositivo |
| `alarm_definitions.py` | `alarm_definitions` | Definiciones de condiciones de alarma |
| `alarms.py` | `alarms` | Instancias de alarmas disparadas |
| `point_history.py` | `point_history` | Históricos de valores (hypertable TimescaleDB) |
| `logic_scripts.py` | `logic_scripts` | Scripts de lógica Python |
| `script_executions.py` | `script_executions` | Ejecuciones de scripts con log y resultado |
| `mimics.py` | `mimics` | Sinópticos SVG con su canvas JSON |
| `notifications.py` | `notifications` | Notificaciones del sistema |
| `engineering_sessions.py` | `engineering_sessions` | Sesiones de comisionamiento desde Studio |

## Notas

- `point_history` es una hypertable de TimescaleDB particionada por `time`. La conversión se hace en la migración `0001_init_schema.py`.
- Todos los modelos se exportan desde `__init__.py` para que Alembic los detecte al autogenerar migraciones.
