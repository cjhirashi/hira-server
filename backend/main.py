from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from core.logger import get_logger
from core.middleware import CorrelationIdMiddleware
from routers.monitor import router as monitor_router

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info(
        "Hira backend arrancando",
        extra={
            "version": "0.0.1-skeleton",
            "deploy_mode": settings.hira_deploy_mode,
            "environment": settings.environment,
        },
    )
    yield
    logger.info("Hira backend apagándose")


app = FastAPI(
    title="Hira API",
    version="0.0.1-skeleton",
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
