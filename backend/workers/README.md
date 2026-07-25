# backend/workers/

Workers Celery para tareas en background: polling de dispositivos, listeners de protocolo y simuladores.

## Colas

| Cola | Propósito |
|------|-----------|
| `protocols` | Polling BACnet, listener MQTT, simuladores |
| `alarms` | Evaluación del motor de alarmas (Sprint futuro) |
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

## Cómo funciona

1. `celery_app.py` declara la instancia `celery_app` importada por todos.
2. `bacnet_poller.poll_all_devices()` consulta BD → por punto: `SET point:{id}:value` + `PUBLISH point:{id}:updates`.
3. `mqtt_listener.start_listener()` conecta `MQTTAdapter` y corre loop infinito.
4. `simulator_runner` lanza el simulador correspondiente y Celery gestiona su ciclo de vida.
