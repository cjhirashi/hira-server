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

---

## DEV-003 — T-77.3 pide `alarm_condition` en POST /points (no implementado)

**Tarea afectada:** T-77.3 (validación Sprint 7)  
**Tipo:** Alcance  
**Descripción:** El criterio T-77.3 pide `POST /api/v1/points` con campo `alarm_condition` inline. En la implementación de Sprint 7, `POST /points` crea el punto y `POST /alarm-definitions` crea la definición de alarma — son dos endpoints independientes, coherentes con el diseño de Sprint 5. El campo `alarm_condition` no existe en `PointCreate` ni en `openapi.yaml`.

**Alternativa propuesta:** Se puede validar T-77.3 creando primero el punto y luego la alarm-definition en un segundo request. La creación inline de alarma en el mismo endpoint requeriría cambio de diseño en openapi.yaml.

**Pendiente:** Decisión de Cowork — ¿agregar `alarm_definition_inline` opcional a `POST /points` en Sprint 8, o validar T-77.3 con dos requests separados?

---

## DEV-004 — T-77.2 espera 409 en DELETE device con puntos; implementado con `?force=true`

**Tarea afectada:** T-77.2 (validación Sprint 7)  
**Tipo:** Alcance  
**Descripción:** El criterio dice "DELETE con puntos activos → 409". Se implementó así: sin `?force=true` retorna 409 con mensaje explicativo; con `?force=true` elimina en cascade. La UI del Configurador usa `?force=true` para el flujo normal de eliminación (con confirmación de usuario).

**Resuelto:** Implementado directamente — behavior matches T-77.2 criterion (409 sin force). La UI añade `?force=true` tras confirmación explícita del usuario.

---

## DEV-005 — T-93.4/T-93.5/T-93.6 no validables sin API key real de Anthropic/OpenAI

**Tarea afectada:** T-93.4, T-93.5, T-93.6 (validación Sprint 9)
**Tipo:** Alcance
**Descripción:** Los criterios T-93.4 ("¿Cuántos puntos hay?"), T-93.5 (tool call `get_point_value`) y T-93.6 (borrador de script generado por LLM) requieren invocar un LLM externo (Anthropic o OpenAI) con una API key válida. En el entorno de desarrollo de Claude Code no hay `ANTHROPIC_API_KEY` disponible. La infraestructura del agente fue validada directamente (tools ejecutan consultas SQL correctas, context injection funciona, `build_agent`/`invoke_agent` no levantan errores de importación). Solo falta el LLM real.

**Alternativa propuesta:** Cowork puede validar estos tres criterios con su propia API key ingresando en Configuración > IA, guardando la key y enviando las preguntas desde `/ai`.

**Pendiente:** Validación manual por Cowork con API key real.

---

## DEV-006 — T-152/T-153 (Hub bootstrap) no implementados en este repo

**Tarea afectada:** T-152, T-153 (Sprint 15)
**Tipo:** Alcance
**Descripción:** Las tareas T-152 y T-153 especifican implementar Hira Hub (FastAPI + PostgreSQL) con routers de licencias. Se aclaró en sesión que Hub es un producto independiente que vive en su propio repositorio, no en `hira-server`. No se crea carpeta `hub/` en este repo.

**Resuelto:** T-154 implementado — `backend/services/license_service.py` es el cliente de Hira Server que *consume* la API de Hub. T-152/T-153 se implementarán en el repo separado de Hub.
