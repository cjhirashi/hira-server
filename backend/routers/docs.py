"""Router /docs — Módulo de Documentación."""
import asyncio

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel

from core.rbac import require_permission
from core.logger import get_logger
import services.doc_service as doc_service

logger = get_logger(__name__)

router = APIRouter(prefix="/docs", tags=["Documentation"])


class DocumentCreate(BaseModel):
    title: str
    content_markdown: str


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
