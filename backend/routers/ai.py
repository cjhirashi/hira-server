"""
Router del Agente del Integrador.

Endpoints:
  GET  /ai/config          → configuración actual (sin API key)
  PUT  /ai/config          → guardar config + API key cifrada
  DELETE /ai/config/api-key → borrar API key
  POST /ai/chat            → chat con el agente LangChain
"""
import asyncio
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core.logger import get_logger
from core.rbac import require_permission

router = APIRouter(prefix="/ai", tags=["AI"])
logger = get_logger(__name__)


class AIConfigUpdate(BaseModel):
    provider: str
    model: str
    api_key: str


class AIChatRequest(BaseModel):
    message: str
    session_id: str | None = None


@router.get("/config")
async def get_ai_config(
    _: dict[str, Any] = Depends(require_permission("ai:read")),
) -> Any:
    from services.ai_config_service import get_config
    return get_config()


@router.put("/config")
async def update_ai_config(
    body: AIConfigUpdate,
    _: dict[str, Any] = Depends(require_permission("ai:write")),
) -> Any:
    from services.ai_config_service import get_config, save_config

    valid_providers = {"claude", "openai"}
    if body.provider not in valid_providers:
        raise HTTPException(status_code=422, detail=f"Provider inválido. Usa: {valid_providers}")
    if not body.model.strip():
        raise HTTPException(status_code=422, detail="El modelo no puede estar vacío")
    if not body.api_key.strip():
        raise HTTPException(status_code=422, detail="La API key no puede estar vacía")

    try:
        save_config(body.provider, body.model, body.api_key)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    logger.info("Configuración IA actualizada", extra={"provider": body.provider, "model": body.model})
    return get_config()


@router.delete("/config/api-key", status_code=204)
async def delete_ai_api_key(
    _: dict[str, Any] = Depends(require_permission("ai:write")),
) -> None:
    from services.ai_config_service import delete_api_key
    delete_api_key()
    logger.info("API key IA eliminada")


@router.post("/chat")
async def ai_chat(
    body: AIChatRequest,
    _: dict[str, Any] = Depends(require_permission("ai:write")),
) -> Any:
    from services.ai_config_service import get_config, get_decrypted_key
    from services.ai_agent import build_agent, invoke_agent

    config = get_config()
    if not config["has_api_key"]:
        raise HTTPException(
            status_code=422,
            detail="API key no configurada. Ve a Configuración > IA para agregar tu API key.",
        )

    api_key = get_decrypted_key()
    if not api_key:
        raise HTTPException(status_code=422, detail="Error al descifrar la API key.")

    try:
        agent_state = build_agent(api_key, config["provider"], config["model"])
    except Exception as exc:
        logger.error("Error al construir agente", extra={"error": str(exc)})
        raise HTTPException(status_code=500, detail=f"Error al inicializar el agente: {exc}")

    try:
        result = await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(
                None, lambda: invoke_agent(agent_state, body.message)
            ),
            timeout=30.0,
        )
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail="El agente no respondió en 30 segundos. Intenta con una pregunta más simple.",
        )
    except Exception as exc:
        logger.error("Error en invocación del agente", extra={"error": str(exc)})
        raise HTTPException(status_code=500, detail=f"Error del agente: {exc}")

    return {"reply": result.get("output", ""), "tool_calls": result.get("tool_calls_log") or None}
