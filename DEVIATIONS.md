# DEVIATIONS.md — Hira

Registro de desviaciones respecto al diseño especificado. Solo Claude Code escribe aquí; Cowork resuelve.

---

## DEV-001 — Celery worker no incluido en docker-compose.yml de Sprint 2

**Tarea afectada:** T-33 (validación Sprint 2)  
**Tipo:** Alcance  
**Descripción:** El `docker-compose.yml` del Walking Skeleton no incluye un servicio `celery-worker`. Las tareas (`workers/bacnet_poller`, `workers/mqtt_listener`, `workers/simulator_runner`) se encolan correctamente en Redis, pero ningún worker las consume. En validación T-33 esto impidió:
- Verificar que el simulador MQTT realmente publique mensajes a Mosquitto
- Verificar que el simulador Modbus sirva registros
- Verificar polling BACnet automático

El `celery_task_id` se almacena correctamente en BD y el encolado en Redis funciona — solo falta el consumidor.

**Alternativa propuesta:** Agregar servicio `celery-worker` al `docker-compose.yml`:
```yaml
celery-worker:
  build: ./backend
  command: celery -A workers.celery_app worker -Q protocols --loglevel=info
  depends_on: [redis, postgres]
  env_file: .env
```

**Resuelto:** Sprint 2. Se añadieron dos servicios: `celery-worker` (queue `simulators`) y `celery-poller` (queue `protocols`). La separación en dos containers con IPs distintos elimina el conflicto de puerto 47808 entre simuladores y pollers. Commit: `c3b76b6`.

---

## DEV-002 — BAC0 22.9.21 no tiene atributo `lite` en el contenedor Docker

**Tarea afectada:** T-23 (bacnet_adapter), T-33 (validación)  
**Tipo:** Técnica  
**Descripción:** Al llamar `BAC0.lite()` desde el contenedor Docker, se obtiene `AttributeError: module 'BAC0' has no attribute 'lite'`. La versión `BAC0==22.9.21` instalada en el container puede diferir de la API esperada, o el módulo requiere privilegios de red (socket raw) que Docker restringe por defecto.

En validación T-33 el Operador pudo intentar la escritura (RBAC correcto, recibió 503 en vez de 403), pero el adaptador BACnet no es funcional en este entorno.

**Alternativa propuesta:**
1. Verificar API real de BAC0 22.9.21 — podría ser `BAC0.connect()` o similar
2. Añadir `--cap-add=NET_ADMIN` al contenedor backend en docker-compose para sockets raw
3. O usar BAC0 en modo `--ip` que no requiere privilegios adicionales

**Resuelto:** Sprint 2. Migrado a `BAC0==2024.1.12` (bacpypes3, Python 3.12 compatible). API actualizada: `who_is()` y `read()` son `async def`; escritura via `_write()` async; desconexión via `await bacnet._disconnect()`. Todas las operaciones BAC0 corren en `asyncio.to_thread() + asyncio.run()` para aislar del loop starlette/anyio. T-33.1, T-33.2, T-33.4, T-33.5 pasados. Commit: `c3b76b6`.
