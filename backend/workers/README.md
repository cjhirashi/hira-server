# backend/workers/

Workers Celery para tareas asíncronas en segundo plano.

## Colas previstas

| Cola | Propósito |
|------|-----------|
| `polling` | Lectura periódica de puntos de campo |
| `alarms` | Evaluación del motor de alarmas |
| `history` | Escritura de históricos en TimescaleDB |
| `logic` | Ejecución de scripts de lógica Python |
| `notifications` | Envío de notificaciones (email, webhook) |

## Broker

Redis (`REDIS_URL` en `.env`). Celery usa Redis tanto como broker de mensajes como backend de resultados.

## Contenido actual

Vacío en Sprint 0. Los workers se implementan a partir de Sprint 3+.
