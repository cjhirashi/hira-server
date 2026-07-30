from core.logger import get_logger

logger = get_logger(__name__)


def get_db_adapter():
    """Retorna la instancia de DatabasePort correcta según HIRA_DEPLOY_MODE.

    - server → PostgreSQLAdapter (producción / campo)
    - studio → SQLiteAdapter (modo offline)
    """
    from core.config import settings

    mode = settings.hira_deploy_mode

    if mode == "server":
        from adapters.db.postgresql_adapter import PostgreSQLAdapter
        logger.info("Factory: usando PostgreSQLAdapter", extra={"mode": mode})
        return PostgreSQLAdapter(database_url=settings.database_url)

    if mode == "studio":
        from adapters.db.sqlite_adapter import SQLiteAdapter
        logger.info("Factory: usando SQLiteAdapter", extra={"mode": mode})
        return SQLiteAdapter()

    raise ValueError(
        f"HIRA_DEPLOY_MODE='{mode}' no reconocido. Valores válidos: 'server', 'studio'"
    )


def get_protocol_adapter(protocol: str):
    """Retorna la instancia de ProtocolPort correcta para el protocolo indicado.

    - bacnet → BACnetAdapter (BAC0)
    - mqtt   → MQTTAdapter (paho-mqtt)
    - modbus → reservado Sprint 2 (usar simulador por ahora)
    """
    p = protocol.lower()

    if p == "bacnet":
        from adapters.protocol.bacnet_adapter import BACnetAdapter
        logger.info("Factory: usando BACnetAdapter")
        return BACnetAdapter()

    if p == "mqtt":
        from adapters.protocol.mqtt_adapter import MQTTAdapter
        logger.info("Factory: usando MQTTAdapter")
        return MQTTAdapter()

    if p == "modbus":
        from adapters.protocol.modbus_adapter import ModbusAdapter
        logger.info("Factory: usando ModbusAdapter")
        return ModbusAdapter

    raise ValueError(
        f"Protocolo '{protocol}' no reconocido. Valores válidos: 'bacnet', 'mqtt', 'modbus'"
    )
