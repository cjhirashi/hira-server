"""Router de Análisis — gráficas, comparación y reportes PDF de ejecuciones e históricos."""
import asyncio
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse

from core.logger import get_logger
from core.rbac import require_permission
from services import analysis_service

logger = get_logger(__name__)

router = APIRouter(prefix="/analysis", tags=["Analysis"])


@router.get("/executions/{exec_id}/chart")
async def get_execution_chart(
    exec_id: int,
    point_name: str | None = Query(None, description="Filtrar por nombre de punto"),
    _: dict = Depends(require_permission("tests:read")),
):
    try:
        data = await asyncio.to_thread(analysis_service.get_execution_chart_data, exec_id, point_name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return data


@router.get("/executions/compare")
async def compare_executions(
    ids: str = Query(..., description="IDs separados por coma, máx 5. Ej: 1,2,3"),
    _: dict = Depends(require_permission("tests:read")),
):
    try:
        id_list = [int(x.strip()) for x in ids.split(",")][:5]
    except ValueError:
        raise HTTPException(status_code=400, detail="IDs deben ser enteros separados por coma")

    try:
        data = await asyncio.to_thread(analysis_service.get_execution_compare_data, id_list)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return data


@router.get("/scripts/{script_id}/trend")
async def get_script_trend(
    script_id: int,
    _: dict = Depends(require_permission("tests:read")),
):
    data = await asyncio.to_thread(analysis_service.get_script_trend, script_id)
    return data


@router.get("/executions/{exec_id}/report")
async def download_execution_report(
    exec_id: int,
    _: dict = Depends(require_permission("tests:read")),
):
    try:
        pdf_bytes = await asyncio.to_thread(analysis_service.generate_execution_pdf, exec_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Error generando PDF de ejecución", extra={"exec_id": exec_id, "error": str(e)})
        raise HTTPException(status_code=500, detail="Error generando el reporte PDF")

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="report_{exec_id}.pdf"'},
    )


@router.get("/history/{point_id}/report")
async def download_history_report(
    point_id: int,
    start: datetime = Query(..., description="Inicio del rango (ISO8601)"),
    end: datetime = Query(..., description="Fin del rango (ISO8601)"),
    bucket: str = Query("1hour", description="Agregación: raw, 1min, 5min, 1hour, 1day"),
    _: dict = Depends(require_permission("historicals:read")),
):
    valid_buckets = {"raw", "1min", "5min", "1hour", "1day"}
    if bucket not in valid_buckets:
        raise HTTPException(status_code=400, detail=f"bucket debe ser uno de: {', '.join(valid_buckets)}")

    try:
        pdf_bytes = await asyncio.to_thread(
            analysis_service.generate_history_pdf, point_id, start, end, bucket
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Error generando PDF de histórico", extra={"point_id": point_id, "error": str(e)})
        raise HTTPException(status_code=500, detail="Error generando el reporte PDF")

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="history_{point_id}.pdf"'},
    )
