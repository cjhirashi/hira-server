"""
Router para consulta del log de uso del Agente IA.

GET /ai-usage  → últimas N invocaciones + totales acumulados
"""
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select

from core.logger import get_logger
from core.rbac import require_permission

logger = get_logger(__name__)

router = APIRouter(prefix="/ai-usage", tags=["AI Usage"])


@router.get("/")
async def list_usage(
    limit: int = Query(10, ge=1, le=100),
    _: dict = Depends(require_permission("logic:read")),
) -> Any:
    """Últimas N invocaciones del Agente IA con totales acumulados."""
    from adapters.factory import get_db_adapter
    from models.ai_usage import AIUsageLog

    adapter = get_db_adapter()
    async with adapter.get_session() as session:
        logs = (
            await session.scalars(
                select(AIUsageLog).order_by(AIUsageLog.timestamp.desc()).limit(limit)
            )
        ).all()

        totals_row = (
            await session.execute(
                select(
                    func.count(AIUsageLog.id).label("total_requests"),
                    func.coalesce(
                        func.sum(AIUsageLog.tokens_input + AIUsageLog.tokens_output), 0
                    ).label("total_tokens"),
                )
            )
        ).one()

    total_requests = totals_row.total_requests or 0
    total_tokens = int(totals_row.total_tokens or 0)

    return {
        "logs": [
            {
                "id": log.id,
                "timestamp": log.timestamp.isoformat(),
                "agent_type": log.agent_type,
                "model": log.model,
                "tokens_input": log.tokens_input,
                "tokens_output": log.tokens_output,
                "latency_ms": log.latency_ms,
                "tool_calls_count": log.tool_calls_count,
                "query_preview": log.query_preview,
            }
            for log in logs
        ],
        "totals": {
            "requests": total_requests,
            "tokens": total_tokens,
            "estimated_cost_usd": round(total_tokens * 0.00000015, 4),
        },
    }
