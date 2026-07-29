"""Instancia Celery compartida para todos los workers de Hira."""
from celery import Celery
from core.config import settings

celery_app = Celery(
    "hira",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "workers.bacnet_poller",
        "workers.mqtt_listener",
        "workers.simulator_runner",
        "workers.alarm_worker",
        "workers.logic_worker",
        "workers.monitor_worker",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    broker_connection_retry_on_startup=True,
    task_routes={
        "workers.bacnet_poller.*": {"queue": "protocols"},
        "workers.mqtt_listener.*": {"queue": "protocols"},
        "workers.simulator_runner.*": {"queue": "simulators"},
        "workers.alarm_worker.*": {"queue": "normal"},
        "workers.logic_worker.*": {"queue": "normal"},
    },
    beat_schedule={
        "evaluate-alarms-every-10s": {
            "task": "workers.alarm_worker.evaluate_alarms",
            "schedule": 10.0,
            "options": {"queue": "normal"},
        },
        "monitor-system-every-60s": {
            "task": "workers.monitor_worker.monitor_system",
            "schedule": 60.0,
            "options": {"queue": "normal"},
        },
    },
)
