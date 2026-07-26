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
from routers.mimics import router as mimics_router
from routers.ws import router as ws_router
from websocket.redis_subscriber import start_subscriber, stop_subscriber

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


async def _seed_demo_mimic() -> None:
    """Crea el mimic Demo HVAC si no existe ningún mimic."""
    from adapters.factory import get_db_adapter
    from models.mimics import Mimic
    from sqlalchemy import select

    adapter = get_db_adapter()
    async with adapter.get_session() as session:
        count = await session.scalar(select(Mimic).limit(1))
        if count is not None:
            return

        demo = Mimic(
            name="Demo HVAC",
            schema_version="1.0",
            canvas_json={"width": 1200, "height": 800, "background": "#0d0d1a"},
            elements_json=[
                {
                    "id": "fan-01", "type": "Fan",
                    "position": {"x": 300, "y": 250}, "size": {"width": 80, "height": 80},
                    "label": "Ventilador AHU-01",
                    "bindings": {
                        "running": {"point_id": 3, "true_when": "value > 0"},
                        "speed_pct": {"point_id": 3},
                    },
                    "style": {"color_normal": "#00ff88", "color_fault": "#ff4444", "color_off": "#888888"},
                },
                {
                    "id": "sensor-01", "type": "Sensor", "sensor_type": "temperature",
                    "position": {"x": 550, "y": 250}, "size": {"width": 80, "height": 80},
                    "label": "Temperatura Suministro",
                    "bindings": {"value": {"point_id": 3}},
                    "display": {"unit": "°C", "decimals": 1, "min": 0, "max": 50},
                },
                {
                    "id": "setpoint-01", "type": "Setpoint",
                    "position": {"x": 550, "y": 420}, "size": {"width": 80, "height": 80},
                    "label": "Setpoint Temperatura",
                    "bindings": {"value": {"point_id": 4}, "writable": True},
                    "display": {"unit": "°C", "decimals": 1, "min": 16, "max": 28},
                },
                {
                    "id": "damper-01", "type": "Damper",
                    "position": {"x": 150, "y": 250}, "size": {"width": 60, "height": 80},
                    "label": "Compuerta Entrada",
                    "bindings": {"open_pct": {"point_id": 3}},
                    "style": {"color_normal": "#00b4d8", "color_fault": "#ff4444", "color_off": "#888888"},
                },
                {
                    "id": "valve-01", "type": "Valve",
                    "position": {"x": 750, "y": 250}, "size": {"width": 60, "height": 60},
                    "label": "Válvula Agua Fría",
                    "bindings": {"open_pct": {"point_id": 3}},
                    "style": {"color_normal": "#00b4d8", "color_fault": "#ff4444"},
                },
                {
                    "id": "chiller-01", "type": "Chiller",
                    "position": {"x": 900, "y": 200}, "size": {"width": 120, "height": 100},
                    "label": "Chiller-01",
                    "bindings": {
                        "running": {"point_id": 3, "true_when": "value > 0"},
                        "load_pct": {"point_id": 3},
                    },
                    "style": {"color_running": "#00b4d8", "color_fault": "#ff4444", "color_off": "#888888"},
                },
            ],
            connections_json=[
                {"id": "conn-01", "from": "damper-01", "to": "fan-01", "style": "duct"},
                {"id": "conn-02", "from": "fan-01", "to": "sensor-01", "style": "duct"},
                {"id": "conn-03", "from": "valve-01", "to": "chiller-01", "style": "pipe"},
            ],
        )
        session.add(demo)
    logger.info("Mimic Demo HVAC creado")


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
    await _seed_demo_mimic()
    start_subscriber()
    yield
    stop_subscriber()
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
app.include_router(auth_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(devices_router, prefix="/api/v1")
app.include_router(points_router, prefix="/api/v1")
app.include_router(simulators_router, prefix="/api/v1")
app.include_router(mimics_router, prefix="/api/v1")
app.include_router(ws_router)
