# backend/workers/

Workers Celery para tareas en background: polling de dispositivos, listeners de protocolo y simuladores.

## Colas

| Cola | Propósito |
|------|-----------|
| `protocols` | Polling BACnet, listener MQTT, simuladores |
| `normal` | Evaluación del motor de alarmas (Celery Beat cada 10s) |
| `history` | Escritura de históricos en TimescaleDB (Sprint futuro) |
| `logic` | Ejecución de scripts de lógica Python (Sprint futuro) |

## Broker

Redis (`REDIS_URL` en `.env`). Celery usa Redis como broker y backend de resultados.

## Archivos

| Archivo | Descripción |
|---------|-------------|
| `celery_app.py` | Instancia Celery compartida — configura broker, backend y rutas de tareas |
| `bacnet_poller.py` | Tarea periódica: lee todos los puntos BACnet activos y publica valores en Redis |
| `mqtt_listener.py` | Tarea persistente (`max_retries=None`): mantiene la suscripción MQTT activa |
| `simulator_runner.py` | Wrappers síncronos que lanzan los simuladores vía `asyncio.run()` |
| `alarm_worker.py` | Tarea `evaluate_alarms` disparada por Celery Beat cada 10s — evalúa condiciones contra valores en Redis |

## Cómo funciona

1. `celery_app.py` declara la instancia `celery_app` importada por todos.
2. `bacnet_poller.poll_all_devices()` consulta BD → por punto: `SET point:{id}:value` + `PUBLISH point:{id}:updates`.
3. `mqtt_listener.start_listener()` conecta `MQTTAdapter` y corre loop infinito.
4. `simulator_runner` lanza el simulador correspondiente y Celery gestiona su ciclo de vida.
5. `alarm_worker.evaluate_alarms()` — disparado por Celery Beat cada 10s: lee `distinct(point_id)` con definiciones habilitadas, obtiene el valor actual de Redis, llama `alarm_engine.evaluate()`. Corre en contenedor `celery-alarm` (cola `normal`).

## Celery Beat
El schedule de 10s para `evaluate_alarms` está configurado en `celery_app.beat_schedule`. Corre en contenedor separado `hira-celery-beat` (solo una instancia activa — no escalar).
