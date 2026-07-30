# backend/workers/

Workers Celery para tareas en background: polling de dispositivos, listeners de protocolo y simuladores.

## Colas

| Cola | Propósito |
|------|-----------|
| `protocols` | Polling BACnet, polling Modbus, listener MQTT |
| `simulators` | Simuladores de dispositivos |
| `normal` | Evaluación del motor de alarmas (Celery Beat cada 10s), monitor del sistema (cada 60s) |
| `high` | Ejecución de test scripts |
| `logic` | Ejecución de scripts de lógica Python |

## Broker

Redis (`REDIS_URL` en `.env`). Celery usa Redis como broker y backend de resultados.

## Archivos

| Archivo | Descripción |
|---------|-------------|
| `celery_app.py` | Instancia Celery compartida — configura broker, backend y rutas de tareas |
| `bacnet_poller.py` | Tarea periódica (cola `protocols`): lee todos los puntos BACnet activos y publica valores en Redis |
| `modbus_poller.py` | Tarea periódica (cola `protocols`, Beat 10s): lee puntos de dispositivos Modbus TCP/RTU activos |
| `mqtt_listener.py` | Tarea persistente (`max_retries=None`, cola `protocols`): mantiene la suscripción MQTT activa |
| `simulator_runner.py` | Wrappers síncronos que lanzan los simuladores vía `asyncio.run()` (cola `simulators`) |
| `alarm_worker.py` | Tarea `evaluate_alarms` (cola `normal`, Beat 10s) — evalúa condiciones contra valores en Redis |
| `monitor_worker.py` | Tarea `monitor_system` (cola `normal`, Beat 60s) — estado general del sistema |
| `logic_worker.py` | Tarea `run_logic_script(script_id)` (cola `logic`) — ejecuta script Python en sandbox RestrictedPython |
| `test_worker.py` | Tarea de ejecución de test scripts (cola `high`) |

## Cómo funciona

1. `celery_app.py` declara la instancia `celery_app` importada por todos.
2. `bacnet_poller.poll_all_devices()` consulta BD → por punto: `SET point:{id}:value` + `PUBLISH point:{id}:updates`.
3. `modbus_poller.poll_all_modbus_devices()` itera dispositivos con `protocol='modbus'` → usa `ModbusAdapter` para leer cada punto vía TCP o RTU → publica en Redis.
4. `mqtt_listener.start_listener()` conecta `MQTTAdapter` y corre loop infinito.
5. `simulator_runner` lanza el simulador correspondiente y Celery gestiona su ciclo de vida.
6. `alarm_worker.evaluate_alarms()` — disparado por Celery Beat cada 10s: lee `distinct(point_id)` con definiciones habilitadas, obtiene el valor actual de Redis, llama `alarm_engine.evaluate()`. Corre en cola `normal`.

## logic_worker.py — ciclo de ejecución

1. `POST /logic/scripts/{id}/start` → router llama `run_logic_script.apply_async(args=[id], queue="normal")`
2. El worker carga el script desde PostgreSQL y crea una instancia `HiraAPI`
3. En cada ciclo: `compile_restricted(code)` → `exec(byte_code, sandbox_globals)` → guarda `ScriptExecution` en BD
4. Si el script levanta excepción → guarda en `error_message`, **continúa el ciclo** (no mata el worker)
5. `POST /logic/scripts/{id}/stop` → `celery_app.control.revoke(task_id, terminate=True)` → worker detecta `self.is_aborted()` → sale limpiamente → marca status='stopped'

**Sandbox RestrictedPython:**
- `compile_restricted()` — rechaza construcciones peligrosas en compilación
- `safe_globals` — entorno con builtins restringidos
- `_print_` = `PrintCollector` — captura `print()` sin acceso a stdout real
- `hira` — instancia `HiraAPI` inyectada; único punto de acceso al sistema

## Celery Beat

Tareas programadas en `celery_app.beat_schedule`. Corren en el contenedor `hira-celery-beat` (una sola instancia activa — no escalar).

| Tarea | Intervalo | Cola |
|-------|-----------|------|
| `alarm_worker.evaluate_alarms` | 10s | `normal` |
| `monitor_worker.monitor_system` | 60s | `normal` |
| `modbus_poller.poll_all_modbus_devices` | 10s | `protocols` |
