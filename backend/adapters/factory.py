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
