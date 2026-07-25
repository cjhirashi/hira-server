from typing import Any, AsyncIterator, Protocol, runtime_checkable


@runtime_checkable
class DatabasePort(Protocol):
    """Interfaz abstracta para el acceso a la base de datos.

    Los servicios solo dependen de este Protocol — nunca de SQLAlchemy,
    asyncpg, aiosqlite ni ninguna otra librería de infraestructura.
    """

    async def get_session(self) -> AsyncIterator[Any]:
        """Retorna un async context manager que provee una sesión de DB."""
        ...

    async def execute(self, query: str, params: dict[str, Any] | None = None) -> Any:
        """Ejecuta una query raw con parámetros nombrados."""
        ...

    async def create_tables(self) -> None:
        """Crea todas las tablas si no existen (usado en tests y modo studio)."""
        ...

    async def health_check(self) -> bool:
        """Verifica que la base de datos es accesible. Retorna True si OK."""
        ...
