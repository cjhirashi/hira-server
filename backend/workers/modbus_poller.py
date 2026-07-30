"""
Worker Celery — polling Modbus periódico (TCP y RTU).

Por cada dispositivo Modbus activo lee todos sus puntos con log_enabled=True,
almacena el valor en Redis (`point:{id}:value`) y publica en pub/sub
(`point:{id}:updates`) para retransmisión WebSocket.
"""
import json
from datetime import datetime, timezone

from workers.celery_app import celery_app
from core.logger import get_logger

logger = get_logger(__name__)

_POINT_TTL = 60  # segundos TTL en Redis


@celery_app.task(
    bind=True,
    max_retries=None,
    name="workers.modbus_poller.poll_all_modbus_devices",
    queue="protocols",
)
def poll_all_modbus_devices(self) -> dict:
    """Tarea periódica: itera todos los dispositivos Modbus activos y sondea sus puntos."""
    import psycopg2
    import redis as redis_sync
    from core.config import settings

    results: dict = {"polled": 0, "errors": 0}

    # Conexión síncrona (Celery prefork — mismo patrón que bacnet_poller en modo sync)
    db_url = settings.sync_database_url
    r = redis_sync.from_url(settings.redis_url, decode_responses=True, socket_connect_timeout=5)

    try:
        conn = psycopg2.connect(db_url.replace("postgresql+psycopg2://", "postgresql://"))
        conn.autocommit = False

        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, address, modbus_unit_id, modbus_transport, modbus_baudrate "
                "FROM devices WHERE protocol = 'modbus' AND status != 'offline'"
            )
            devices = cur.fetchall()

        for row in devices:
            dev_id, dev_name, address, unit_id, transport, baudrate = row
            try:
                _poll_device_sync(conn, r, dev_id, dev_name, address, unit_id, transport, baudrate, db_url)
                results["polled"] += 1
            except Exception as exc:
                logger.error(
                    "Modbus poll device error",
                    extra={"device_id": dev_id, "error": str(exc)},
                )
                results["errors"] += 1

        conn.close()
    except Exception as exc:
        logger.error("Modbus poller DB error", extra={"error": str(exc)})
    finally:
        r.close()

    return results


def _poll_device_sync(conn, r, dev_id, dev_name, address, unit_id, transport, baudrate, db_url) -> None:
    from adapters.protocol.modbus_adapter import ModbusAdapter
    from services.history_writer import history_writer as hw

    # Construir Device-like object mínimo para el adapter
    class _FakeDevice:
        id = dev_id
        modbus_unit_id = unit_id or 1
        modbus_transport = transport or "tcp"
        modbus_baudrate = baudrate or 9600

    _FakeDevice.address = address

    adapter = ModbusAdapter(_FakeDevice())
    if not adapter.connect():
        logger.warning("Modbus device no disponible", extra={"device_id": dev_id})
        return

    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, address, unit, modbus_register_type, modbus_data_type, "
                "history_interval_seconds, log_enabled "
                "FROM points WHERE device_id = %s AND log_enabled = TRUE",
                (dev_id,),
            )
            points = cur.fetchall()

        for p_row in points:
            p_id, p_name, p_addr, p_unit, reg_type, data_type, hist_interval, _ = p_row
            try:
                class _FakePoint:
                    id = p_id
                    name = p_name
                    address = p_addr
                    unit = p_unit
                    modbus_register_type = reg_type
                    modbus_data_type = data_type
                    history_interval_seconds = hist_interval

                value = adapter.read_point(_FakePoint())
                ts_str = datetime.now(timezone.utc).isoformat()

                entry = json.dumps({
                    "id": p_id,
                    "name": p_name,
                    "value": value,
                    "unit": p_unit,
                    "quality": "good" if value is not None else "bad",
                    "timestamp": ts_str,
                })

                r.setex(f"point:{p_id}:value", _POINT_TTL, entry)
                r.publish(f"point:{p_id}:updates", entry)

                if value is not None:
                    # history_writer síncrono usando psycopg2 directo
                    last_key = f"point:{p_id}:last_recorded"
                    last_raw = r.get(last_key)
                    now_ts = datetime.now(timezone.utc)
                    should_record = True
                    if last_raw:
                        try:
                            last_dt = datetime.fromisoformat(last_raw)
                            elapsed = (now_ts - last_dt).total_seconds()
                            should_record = elapsed >= hist_interval
                        except ValueError:
                            pass
                    if should_record:
                        with conn.cursor() as cur2:
                            cur2.execute(
                                "INSERT INTO point_history (point_id, value, quality, timestamp) "
                                "VALUES (%s, %s, 'good', NOW())",
                                (p_id, float(value)),
                            )
                        conn.commit()
                        r.set(last_key, now_ts.isoformat())

            except Exception as exc:
                logger.error(
                    "Modbus point read error",
                    extra={"point_id": p_id, "error": str(exc)},
                )
    finally:
        adapter.disconnect()
