"""Router de información del sistema."""
from fastapi import APIRouter, Depends

from core.config import settings
from core.rbac import require_permission

router = APIRouter(prefix="/system", tags=["System"])

_APP_VERSION = "0.10"


@router.get("/mode")
async def get_system_mode():
    """Modo de despliegue actual — público, sin autenticación."""
    return {
        "mode": settings.deploy_mode,
        "db_type": "sqlite" if settings.deploy_mode == "studio" else "postgresql",
        "version": _APP_VERSION,
    }


@router.get("/health/detailed")
async def get_health_detailed(
    _: dict = Depends(require_permission("system:read")),
):
    """Métricas detalladas por componente. Requiere Admin o Operador."""
    from services.health_service import get_detailed_health
    return await get_detailed_health()
