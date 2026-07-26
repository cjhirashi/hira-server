"""Router de información del sistema — público, sin autenticación."""
from fastapi import APIRouter
from core.config import settings

router = APIRouter(prefix="/system", tags=["System"])

_APP_VERSION = "0.10c"


@router.get("/mode")
async def get_system_mode():
    return {
        "mode": settings.deploy_mode,
        "db_type": "sqlite" if settings.deploy_mode == "studio" else "postgresql",
        "version": _APP_VERSION,
    }
