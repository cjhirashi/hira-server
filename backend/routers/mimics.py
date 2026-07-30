from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from adapters.factory import get_db_adapter
from core.logger import get_logger
from core.rbac import require_permission
from models.mimics import Mimic
from schemas.mimics import MimicCreate, MimicResponse, MimicUpdate

router = APIRouter(prefix="/mimics", tags=["Mimics"])
logger = get_logger(__name__)


def _to_response(m: Mimic) -> MimicResponse:
    return MimicResponse(
        id=m.id,
        name=m.name,
        description=getattr(m, "description", None),
        schema_version=m.schema_version,
        canvas=m.canvas_json,
        elements=m.elements_json or [],
        connections=m.connections_json or [],
        updated_at=m.updated_at,
    )


@router.get("", response_model=list[MimicResponse])
async def list_mimics(
    _: dict[str, Any] = Depends(require_permission("devices:read")),
) -> Any:
    adapter = get_db_adapter()
    async with adapter.get_session() as session:
        mimics = (await session.execute(select(Mimic).order_by(Mimic.id))).scalars().all()
    return [_to_response(m) for m in mimics]


@router.get("/{mimic_id}", response_model=MimicResponse)
async def get_mimic(
    mimic_id: int,
    _: dict[str, Any] = Depends(require_permission("devices:read")),
) -> Any:
    adapter = get_db_adapter()
    async with adapter.get_session() as session:
        mimic = await session.get(Mimic, mimic_id)
    if mimic is None:
        raise HTTPException(status_code=404, detail="Mimic no encontrado")
    return _to_response(mimic)


@router.post("", response_model=MimicResponse, status_code=201)
async def create_mimic(
    body: MimicCreate,
    _: dict[str, Any] = Depends(require_permission("devices:write")),
) -> Any:
    adapter = get_db_adapter()
    async with adapter.get_session() as session:
        mimic = Mimic(
            name=body.name,
            schema_version="1.0",
            canvas_json=body.canvas,
            elements_json=body.elements,
            connections_json=body.connections,
        )
        if hasattr(mimic, "description"):
            mimic.description = body.description
        session.add(mimic)
        await session.flush()
        mimic_id = mimic.id

    async with adapter.get_session() as session:
        mimic = await session.get(Mimic, mimic_id)

    logger.info("Mimic creado", extra={"mimic_id": mimic_id, "mimic_name": body.name})
    return _to_response(mimic)


@router.put("/{mimic_id}", response_model=MimicResponse)
async def update_mimic(
    mimic_id: int,
    body: MimicUpdate,
    _: dict[str, Any] = Depends(require_permission("devices:write")),
) -> Any:
    adapter = get_db_adapter()
    async with adapter.get_session() as session:
        mimic = await session.get(Mimic, mimic_id)
        if mimic is None:
            raise HTTPException(status_code=404, detail="Mimic no encontrado")
        if body.name is not None:
            mimic.name = body.name
        if body.canvas is not None:
            mimic.canvas_json = body.canvas
        if body.elements is not None:
            mimic.elements_json = body.elements
        if body.connections is not None:
            mimic.connections_json = body.connections
        await session.flush()

    async with adapter.get_session() as session:
        mimic = await session.get(Mimic, mimic_id)

    logger.info("Mimic actualizado", extra={"mimic_id": mimic_id})
    return _to_response(mimic)


@router.delete("/{mimic_id}", status_code=204)
async def delete_mimic(
    mimic_id: int,
    _: dict[str, Any] = Depends(require_permission("devices:admin")),
) -> None:
    adapter = get_db_adapter()
    async with adapter.get_session() as session:
        mimic = await session.get(Mimic, mimic_id)
        if mimic is None:
            raise HTTPException(status_code=404, detail="Mimic no encontrado")
        await session.delete(mimic)
    logger.info("Mimic eliminado", extra={"mimic_id": mimic_id})
