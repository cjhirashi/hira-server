"""Router /docs — Módulo de Documentación."""
import asyncio

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel

from core.rbac import require_permission
from core.logger import get_logger
import services.doc_service as doc_service
import services.rag_service as rag_service

logger = get_logger(__name__)

router = APIRouter(prefix="/docs", tags=["Documentation"])


class DocumentCreate(BaseModel):
    title: str
    content_markdown: str


# ── Stats ──────────────────────────────────────────────────────────────────────

@router.get("/stats")
async def get_docs_stats(user=Depends(require_permission("logic:read"))):
    """Resumen rápido: total de documentos e indexados (con chunks)."""
    def _run():
        from sqlalchemy import create_engine, text
        from core.config import settings
        engine = create_engine(settings.sync_database_url, pool_pre_ping=True)
        try:
            with engine.connect() as conn:
                total = conn.execute(text("SELECT COUNT(*) FROM documents")).scalar() or 0
                indexed = conn.execute(
                    text(
                        "SELECT COUNT(DISTINCT document_id) FROM document_chunks"
                    )
                ).scalar() or 0
        finally:
            engine.dispose()
        return {"total": total, "indexed": indexed}

    return await asyncio.to_thread(_run)


# ── CRUD ──────────────────────────────────────────────────────────────────────

@router.get("")
async def list_documents(user=Depends(require_permission("logic:read"))):
    return await asyncio.to_thread(doc_service.get_all_documents)


@router.post("", status_code=201)
async def create_document(
    body: DocumentCreate,
    user=Depends(require_permission("logic:write")),
):
    return await asyncio.to_thread(doc_service.create_manual_doc, body.title, body.content_markdown)


@router.get("/{doc_id}")
async def get_document(doc_id: int, user=Depends(require_permission("logic:read"))):
    try:
        return await asyncio.to_thread(doc_service.get_document, doc_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Documento no encontrado")


@router.put("/{doc_id}")
async def update_document(
    doc_id: int,
    body: DocumentCreate,
    user=Depends(require_permission("logic:write")),
):
    try:
        return await asyncio.to_thread(doc_service.update_manual_doc, doc_id, body.title, body.content_markdown)
    except KeyError:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/{doc_id}", status_code=204)
async def delete_document(doc_id: int, user=Depends(require_permission("logic:write"))):
    try:
        await asyncio.to_thread(doc_service.delete_manual_doc, doc_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return Response(status_code=204)


# ── Generación ────────────────────────────────────────────────────────────────

@router.post("/generate/script/{script_id}")
async def generate_script_doc(
    script_id: int,
    source_type: str = Query("script_logic", enum=["script_logic", "script_test"]),
    user=Depends(require_permission("logic:write")),
):
    try:
        return await asyncio.to_thread(doc_service.generate_script_doc, script_id, source_type)
    except KeyError:
        raise HTTPException(status_code=404, detail="Script no encontrado")


@router.post("/generate/inventory")
async def generate_inventory_doc(user=Depends(require_permission("logic:write"))):
    return await asyncio.to_thread(doc_service.generate_inventory)


@router.get("/generate/preview/{script_id}")
async def preview_mermaid(
    script_id: int,
    source_type: str = Query("script_logic", enum=["script_logic", "script_test"]),
    user=Depends(require_permission("logic:read")),
):
    try:
        mermaid = await asyncio.to_thread(doc_service.preview_mermaid, script_id, source_type)
        return {"mermaid": mermaid}
    except KeyError:
        raise HTTPException(status_code=404, detail="Script no encontrado")


# ── RAG / Indexación ──────────────────────────────────────────────────────────

@router.post("/index/all")
async def index_all_documents(
    force: bool = Query(False),
    user=Depends(require_permission("logic:write")),
):
    def _run():
        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session
        from core.config import settings
        engine = create_engine(settings.sync_database_url, pool_pre_ping=True)
        with Session(engine) as session:
            return rag_service.index_all_documents(force, session)
        engine.dispose()

    try:
        return await asyncio.to_thread(_run)
    except RuntimeError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.post("/{doc_id}/index")
async def index_document(
    doc_id: int,
    user=Depends(require_permission("logic:write")),
):
    def _run():
        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session
        from core.config import settings
        engine = create_engine(settings.sync_database_url, pool_pre_ping=True)
        with Session(engine) as session:
            return rag_service.index_document(doc_id, session)
        engine.dispose()

    try:
        return await asyncio.to_thread(_run)
    except ValueError:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    except RuntimeError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/{doc_id}/chunks")
async def get_document_chunks(
    doc_id: int,
    user=Depends(require_permission("logic:read")),
):
    def _run():
        from sqlalchemy import create_engine, text
        from core.config import settings
        engine = create_engine(settings.sync_database_url, pool_pre_ping=True)
        try:
            with engine.connect() as conn:
                doc = conn.execute(
                    text("SELECT id FROM documents WHERE id = :id"),
                    {"id": doc_id},
                ).fetchone()
                if doc is None:
                    raise KeyError(doc_id)
                rows = conn.execute(
                    text(
                        "SELECT id, document_id, chunk_index, content "
                        "FROM document_chunks WHERE document_id = :doc_id "
                        "ORDER BY chunk_index"
                    ),
                    {"doc_id": doc_id},
                ).fetchall()
        finally:
            engine.dispose()
        return [
            {"id": r[0], "document_id": r[1], "chunk_index": r[2], "content": r[3]}
            for r in rows
        ]

    try:
        return await asyncio.to_thread(_run)
    except KeyError:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
