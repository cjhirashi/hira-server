# services/simulators/

## Propósito
Simuladores de dispositivos industriales para desarrollo y pruebas sin hardware real. Cada simulador corre como una corrutina asyncio lanzada desde una tarea Celery. `simulator_service.py` orquesta el ciclo de vida.

## Archivos

| Archivo | Descripción |
|---|---|
| `bacnet_sim.py` | Dispositivo BACnet virtual usando BAC0 con puntos analógicos y binarios |
| `modbus_sim.py` | Servidor Modbus TCP usando pymodbus con registros holding actualizados periódicamente |
| `mqtt_sim.py` | Publisher MQTT periódico con drift de sensor real (5% por ciclo) |
| `simulator_service.py` | Orquestador: start/stop de simuladores vía Celery + estado en BD |

## Cómo funciona

1. El router `routers/simulators.py` llama a `start_simulator(id)` o `stop_simulator(id)`.
2. `simulator_service.py` consulta la BD para obtener `protocol` y `config_json` del dispositivo.
3. Lanza la tarea Celery correspondiente (`workers/simulator_runner.py`) y guarda el `celery_task_id` en `config_json`.
4. Para detener: revoca la tarea con `celery_app.control.revoke(task_id, terminate=True)`.
5. Cada simulador actualiza el estado del dispositivo (`status="running"` / `"stopped"`) en la BD.

## Dependencias

- `adapters/factory.py` — acceso a BD (vía `get_db_adapter()`)
- `workers/celery_app.py` — instancia Celery para lanzar y revocar tareas
- `workers/simulator_runner.py` — tareas Celery que envuelven los simuladores
- `core/config.py` — settings de MQTT broker
- **Nota:** estos módulos NO importan de `adapters/protocol/` directamente — los simuladores usan las bibliotecas de protocolo de forma independiente (BAC0, pymodbus, paho)
