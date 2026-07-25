from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, text

from core.config import settings
from core.logger import get_logger
from core.middleware import CorrelationIdMiddleware
from core.redis import close_redis
from core.security import hash_password
from routers.auth import router as auth_router
from routers.devices import router as devices_router
from routers.monitor import router as monitor_router
from routers.points import router as points_router
from routers.simulators import router as simulators_router
from routers.users import router as users_router

logger = get_logger(__name__)

_VERSION = "0.2.0"


async def _seed_admin() -> None:
    """Crea el usuario Admin inicial si no existe. Solo se ejecuta en startup."""
    if not settings.admin_password:
        logger.warning("ADMIN_PASSWORD no configurada — usuario admin no creado")
        return

    from adapters.factory import get_db_adapter
    from models.users import User
    from models.user_roles import UserRole

    adapter = get_db_adapter()
    async with adapter.get_session() as session:
        existing = await session.scalar(select(User).where(User.email == settings.admin_email))
        if existing:
            logger.info("Usuario admin ya existe", extra={"email": settings.admin_email})
            return

        admin = User(
            email=settings.admin_email,
            full_name=settings.admin_full_name,
            password_hash=hash_password(settings.admin_password),
            is_active=True,
        )
        session.add(admin)
        await session.flush()

        admin_role = UserRole(user_id=admin.id, role_id=1)
        session.add(admin_role)

    logger.info("Usuario admin creado", extra={"email": settings.admin_email})


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info(
        "Hira backend arrancando",
        extra={
            "version": _VERSION,
            "deploy_mode": settings.hira_deploy_mode,
            "environment": settings.environment,
        },
    )
    await _seed_admin()
    yield
    await close_redis()
    logger.info("Hira backend apagándose")


app = FastAPI(
    title="Hira API",
    version=_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── Middlewares ────────────────────────────────────────────────────────────
app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Trace-ID"],
)

# ── Routers ────────────────────────────────────────────────────────────────
app.include_router(monitor_router)
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(devices_router, prefix="/api/v1")
app.include_router(points_router, prefix="/api/v1")
app.include_router(simulators_router, prefix="/api/v1")
