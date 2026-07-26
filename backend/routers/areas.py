from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from adapters.factory import get_db_adapter
from core.logger import get_logger
from core.rbac import require_permission
from models.areas import Area
from schemas.areas import AreaCreate, AreaResponse

router = APIRouter(prefix="/areas", tags=["Configurator"])
logger = get_logger(__name__)


def _to_response(a: Area) -> AreaResponse:
    return AreaResponse(
        id=a.id,
        name=a.name,
        description=a.description,
        created_at=a.created_at,
    )


@router.get("", response_model=list[AreaResponse])
async def list_areas(
    _: dict[str, Any] = Depends(require_permission("config:read")),
) -> Any:
    adapter = get_db_adapter()
    async with adapter.get_session() as session:
        areas = (await session.execute(select(Area).order_by(Area.name))).scalars().all()
    return [_to_response(a) for a in areas]


@router.post("", response_model=AreaResponse, status_code=201)
async def create_area(
    body: AreaCreate,
    _: dict[str, Any] = Depends(require_permission("config:write")),
) -> Any:
    adapter = get_db_adapter()
    try:
        async with adapter.get_session() as session:
            area = Area(name=body.name, description=body.description)
            session.add(area)
            await session.flush()
            area_id = area.id
        async with adapter.get_session() as session:
            area = await session.get(Area, area_id)
    except IntegrityError:
        raise HTTPException(status_code=400, detail=f"Ya existe un área con el nombre '{body.name}'")
    logger.info("Área creada", extra={"area_id": area_id, "area_name": body.name})
    return _to_response(area)


@router.get("/{area_id}", response_model=AreaResponse)
async def get_area(
    area_id: int,
    _: dict[str, Any] = Depends(require_permission("config:read")),
) -> Any:
    adapter = get_db_adapter()
    async with adapter.get_session() as session:
        area = await session.get(Area, area_id)
    if area is None:
        raise HTTPException(status_code=404, detail="Área no encontrada")
    return _to_response(area)


@router.put("/{area_id}", response_model=AreaResponse)
async def update_area(
    area_id: int,
    body: AreaCreate,
    _: dict[str, Any] = Depends(require_permission("config:write")),
) -> Any:
    adapter = get_db_adapter()
    try:
        async with adapter.get_session() as session:
            area = await session.get(Area, area_id)
            if area is None:
                raise HTTPException(status_code=404, detail="Área no encontrada")
            area.name = body.name
            area.description = body.description
            await session.flush()
        async with adapter.get_session() as session:
            area = await session.get(Area, area_id)
    except IntegrityError:
        raise HTTPException(status_code=400, detail=f"Ya existe un área con el nombre '{body.name}'")
    logger.info("Área actualizada", extra={"area_id": area_id})
    return _to_response(area)


@router.delete("/{area_id}", status_code=204)
async def delete_area(
    area_id: int,
    _: dict[str, Any] = Depends(require_permission("config:write")),
) -> None:
    adapter = get_db_adapter()
    async with adapter.get_session() as session:
        area = await session.get(Area, area_id)
        if area is None:
            raise HTTPException(status_code=404, detail="Área no encontrada")
        await session.delete(area)
    logger.info("Área eliminada", extra={"area_id": area_id})
