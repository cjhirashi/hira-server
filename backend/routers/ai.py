"""
Router del Agente IA — Integrador y Cliente.

Sub-routers:
  /ai/integrador/config  (GET, PUT)   → Agente del Integrador (solo Admin)
  /ai/integrador/chat    (POST)       → Chat con Agente del Integrador (solo Admin)
  /ai/cliente/config     (GET, PUT)   → Agente del Cliente (Admin + Operador)
  /ai/cliente/chat       (POST)       → Chat con Agente del Cliente (Admin + Operador)

Aliases backward-compat:
  GET  /ai/config  → integrador/config
  PUT  /ai/config  → integrador/config
  POST /ai/chat    → integrador/chat
"""
import asyncio
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core.logger import get_logger
from core.rbac import require_permission

logger = get_logger(__name__)

router_integrador = APIRouter(prefix="/ai/integrador", tags=["AI Integrador"])
router_cliente    = APIRouter(prefix="/ai/cliente",    tags=["AI Cliente"])
router_compat     = APIRouter(prefix="/ai",            tags=["AI"])


class AIConfigUpdate(BaseModel):
    provider: str
    model: str
    api_key: str


class AIChatRequest(BaseModel):
    message: str
    session_id: str | None = None


def _validate_config(body: AIConfigUpdate) -> None:
    if body.provider not in {"claude", "openai"}:
        raise HTTPException(status_code=422, detail="Provider inválido. Usa: claude, openai")
    if not body.model.strip():
        raise HTTPException(status_code=422, detail="El modelo no puede estar vacío")
    if not body.api_key.strip():
        raise HTTPException(status_code=422, detail="La API key no puede estar vacía")


async def _invoke_agent(agent_type: str, message: str) -> dict[str, Any]:
    from services.ai_config_service import get_config, get_decrypted_key

    config = get_config(agent_type)
    if not config["has_api_key"]:
        raise HTTPException(
            status_code=422,
            detail=f"API key no configurada para el agente '{agent_type}'. Ve a Configuración > IA.",
        )

    api_key = get_decrypted_key(agent_type)
    if not api_key:
        raise HTTPException(status_code=422, detail="Error al descifrar la API key.")

    if agent_type == "integrador":
        from services.ai_agent import build_agent
    else:
        from services.ai_agent_cliente import build_agent

    try:
        agent = build_agent(api_key, config["provider"], config["model"])
    except Exception as exc:
        logger.error("Error al construir agente", extra={"error": str(exc), "agent_type": agent_type})
        raise HTTPException(status_code=500, detail=f"Error al inicializar el agente: {exc}")

    try:
        result = await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(
                None, lambda: agent.invoke({"input": message})
            ),
            timeout=30.0,
        )
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="El agente no respondió en 30 segundos.")
    except Exception as exc:
        logger.error("Error en invocación del agente", extra={"error": str(exc)})
        raise HTTPException(status_code=500, detail=f"Error del agente: {exc}")

    reply = result.get("output", "")
    intermediate = result.get("intermediate_steps", [])
    tool_calls = [
        {"tool": step[0].tool, "input": step[0].tool_input, "output": str(step[1])}
        for step in intermediate if hasattr(step[0], "tool")
    ] if intermediate else None

    return {"reply": reply, "tool_calls": tool_calls}


# ── Integrador ────────────────────────────────────────────────────────────────
@router_integrador.get("/config")
async def get_integrador_config(_: dict = Depends(require_permission("ai:read"))) -> Any:
    from services.ai_config_service import get_config
    return get_config("integrador")


@router_integrador.put("/config")
async def update_integrador_config(body: AIConfigUpdate, _: dict = Depends(require_permission("ai:write"))) -> Any:
    from services.ai_config_service import get_config, save_config
    _validate_config(body)
    try:
        save_config(body.provider, body.model, body.api_key, "integrador")
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return get_config("integrador")


@router_integrador.delete("/config/api-key", status_code=204)
async def delete_integrador_api_key(_: dict = Depends(require_permission("ai:write"))) -> None:
    from services.ai_config_service import delete_api_key
    delete_api_key("integrador")


@router_integrador.post("/chat")
async def integrador_chat(body: AIChatRequest, _: dict = Depends(require_permission("ai:write"))) -> Any:
    return await _invoke_agent("integrador", body.message)


# ── Cliente ───────────────────────────────────────────────────────────────────
@router_cliente.get("/config")
async def get_cliente_config(_: dict = Depends(require_permission("ai:read"))) -> Any:
    from services.ai_config_service import get_config
    return get_config("cliente")


@router_cliente.put("/config")
async def update_cliente_config(body: AIConfigUpdate, _: dict = Depends(require_permission("ai:write"))) -> Any:
    from services.ai_config_service import get_config, save_config
    _validate_config(body)
    try:
        save_config(body.provider, body.model, body.api_key, "cliente")
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return get_config("cliente")


@router_cliente.delete("/config/api-key", status_code=204)
async def delete_cliente_api_key(_: dict = Depends(require_permission("ai:write"))) -> None:
    from services.ai_config_service import delete_api_key
    delete_api_key("cliente")


@router_cliente.post("/chat")
async def cliente_chat(body: AIChatRequest, _: dict = Depends(require_permission("ai:read"))) -> Any:
    return await _invoke_agent("cliente", body.message)


# ── Backward-compat aliases ───────────────────────────────────────────────────
@router_compat.get("/config")
async def get_ai_config_compat(_: dict = Depends(require_permission("ai:read"))) -> Any:
    from services.ai_config_service import get_config
    return get_config("integrador")


@router_compat.put("/config")
async def update_ai_config_compat(body: AIConfigUpdate, _: dict = Depends(require_permission("ai:write"))) -> Any:
    from services.ai_config_service import get_config, save_config
    _validate_config(body)
    try:
        save_config(body.provider, body.model, body.api_key, "integrador")
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return get_config("integrador")


@router_compat.delete("/config/api-key", status_code=204)
async def delete_ai_api_key_compat(_: dict = Depends(require_permission("ai:write"))) -> None:
    from services.ai_config_service import delete_api_key
    delete_api_key("integrador")


@router_compat.post("/chat")
async def ai_chat_compat(body: AIChatRequest, _: dict = Depends(require_permission("ai:write"))) -> Any:
    return await _invoke_agent("integrador", body.message)


# Router principal
router = APIRouter()
router.include_router(router_integrador)
router.include_router(router_cliente)
router.include_router(router_compat)
