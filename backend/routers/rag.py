"""Router /rag — Búsqueda semántica RAG sobre document_chunks."""
import asyncio

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from core.rbac import require_permission
from core.logger import get_logger
import services.rag_service as rag_service

logger = get_logger(__name__)

router = APIRouter(prefix="/rag", tags=["RAG"])


class RAGSearchRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)


@router.post("/search")
async def search(
    body: RAGSearchRequest,
    user=Depends(require_permission("logic:read")),
):
    def _run():
        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session
        from core.config import settings
        engine = create_engine(settings.sync_database_url, pool_pre_ping=True)
        try:
            with Session(engine) as session:
                return rag_service.semantic_search(body.query, body.top_k, session)
        finally:
            engine.dispose()

    try:
        return await asyncio.to_thread(_run)
    except RuntimeError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
