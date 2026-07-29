"""
Servicio de análisis — gráficas, comparación y reportes PDF de ejecuciones de prueba
e históricos de puntos.

Usa psycopg2 síncrono (patrón establecido para servicios pesados / generación de archivos).
La capa async se maneja con asyncio.to_thread() en el router.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from io import BytesIO
from typing import Any

from core.config import settings
from core.logger import get_logger

logger = get_logger(__name__)

_SYNC_URL_KEY = "analysis_engine"


def _get_conn():
    import psycopg2
    sync_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
    return psycopg2.connect(sync_url)


# ── Chart data ────────────────────────────────────────────────────────────────


def get_execution_chart_data(exec_id: int, point_name: str | None) -> list[dict]:
    """
    Retorna logs DATA de la ejecución como [{timestamp, point_name, value}].
    Si point_name dado, filtra por ese punto.
    """
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            # Verify execution exists
            cur.execute("SELECT id FROM test_executions WHERE id = %s", (exec_id,))
            if not cur.fetchone():
                raise ValueError(f"Ejecución {exec_id} no encontrada")

            if point_name:
                cur.execute(
                    "SELECT created_at, message FROM test_logs "
                    "WHERE execution_id = %s AND level = 'data' "
                    "AND message LIKE %s ORDER BY created_at ASC",
                    (exec_id, f'%"point_name": "{point_name}"%'),
                )
            else:
                cur.execute(
                    "SELECT created_at, message FROM test_logs "
                    "WHERE execution_id = %s AND level = 'data' ORDER BY created_at ASC",
                    (exec_id,),
                )
            rows = cur.fetchall()
    finally:
        conn.close()

    result = []
    for ts, msg in rows:
        try:
            data = json.loads(msg)
            result.append({
                "timestamp": ts.isoformat(),
                "point_name": data.get("point_name", ""),
                "value": float(data.get("value", 0)),
            })
        except (json.JSONDecodeError, TypeError, KeyError):
            pass
    return result


# ── Execution compare ─────────────────────────────────────────────────────────


def get_execution_compare_data(execution_ids: list[int]) -> list[dict]:
    """
    Compara N ejecuciones del mismo script usando eje de tiempo relativo (t_offset_ms).
    Lanza ValueError si los IDs pertenecen a scripts distintos.
    """
    if not execution_ids:
        return []

    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            placeholders = ",".join(["%s"] * len(execution_ids))
            cur.execute(
                f"SELECT id, script_id, started_at FROM test_executions WHERE id IN ({placeholders})",
                execution_ids,
            )
            execs = {r[0]: {"script_id": r[1], "started_at": r[2]} for r in cur.fetchall()}

            script_ids = {v["script_id"] for v in execs.values()}
            if len(script_ids) > 1:
                raise ValueError(
                    f"Los IDs pertenecen a scripts distintos: {script_ids}. "
                    "Solo se pueden comparar ejecuciones del mismo script."
                )

            result = []
            for exec_id in execution_ids:
                if exec_id not in execs:
                    continue
                started_at = execs[exec_id]["started_at"]
                cur.execute(
                    "SELECT created_at, message FROM test_logs "
                    "WHERE execution_id = %s AND level = 'data' ORDER BY created_at ASC",
                    (exec_id,),
                )
                points = []
                for ts, msg in cur.fetchall():
                    try:
                        data = json.loads(msg)
                        t_offset = int((ts - started_at).total_seconds() * 1000)
                        points.append({
                            "t_offset_ms": t_offset,
                            "point_name": data.get("point_name", ""),
                            "value": float(data.get("value", 0)),
                        })
                    except (json.JSONDecodeError, TypeError, KeyError):
                        pass
                result.append({
                    "execution_id": exec_id,
                    "started_at": started_at.isoformat(),
                    "points": points,
                })
    finally:
        conn.close()

    return result


# ── Script trend ──────────────────────────────────────────────────────────────


def get_script_trend(script_id: int) -> list[dict]:
    """Historial de ejecuciones de un script con duración y estado."""
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, started_at, ended_at, status, passed, failed "
                "FROM test_executions WHERE script_id = %s ORDER BY started_at ASC",
                (script_id,),
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    result = []
    for exec_id, started_at, ended_at, status, passed, failed in rows:
        duration_ms = None
        if started_at and ended_at:
            duration_ms = int((ended_at - started_at).total_seconds() * 1000)
        summary = None
        if passed is not None and failed is not None:
            summary = f"{passed} pasaron, {failed} fallaron"
        result.append({
            "execution_id": exec_id,
            "started_at": started_at.isoformat() if started_at else None,
            "status": status,
            "duration_ms": duration_ms,
            "result_summary": summary,
        })
    return result


# ── PDF — Execution report ─────────────────────────────────────────────────────


def generate_execution_pdf(exec_id: int) -> bytes:
    """
    Genera PDF con reportlab del reporte de una ejecución de prueba.
    Incluye encabezado, resumen, tabla de puntos medidos y log completo.
    """
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
    )

    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT e.id, e.started_at, e.ended_at, e.status, e.output, "
                "e.error_message, e.passed, e.failed, s.name "
                "FROM test_executions e JOIN test_scripts s ON s.id = e.script_id "
                "WHERE e.id = %s",
                (exec_id,),
            )
            exec_row = cur.fetchone()
            if not exec_row:
                raise ValueError(f"Ejecución {exec_id} no encontrada")

            cur.execute(
                "SELECT level, message, created_at FROM test_logs "
                "WHERE execution_id = %s ORDER BY created_at ASC",
                (exec_id,),
            )
            logs = cur.fetchall()
    finally:
        conn.close()

    (eid, started_at, ended_at, status, output, error_msg, passed, failed, script_name) = exec_row

    duration_str = "—"
    if started_at and ended_at:
        ms = int((ended_at - started_at).total_seconds() * 1000)
        duration_str = f"{ms} ms"

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("HiraTitle", parent=styles["Heading1"], fontSize=16, spaceAfter=6)
    body_style = styles["Normal"]
    mono_style = ParagraphStyle("Mono", parent=styles["Normal"], fontName="Courier", fontSize=8, leading=10)

    story: list[Any] = []

    # Header
    story.append(Paragraph(f"Reporte de Ejecución #{eid}", title_style))
    story.append(Paragraph(f"Script: <b>{script_name}</b>", body_style))
    story.append(Paragraph(f"Inicio: {started_at.strftime('%Y-%m-%d %H:%M:%S UTC') if started_at else '—'}", body_style))
    story.append(Paragraph(f"Duración: {duration_str}", body_style))
    story.append(Paragraph(f"Estado: <b>{status.upper()}</b>", body_style))
    if passed is not None:
        story.append(Paragraph(f"Assertions: {passed} pasaron / {failed} fallaron", body_style))
    if error_msg:
        story.append(Paragraph(f"Error: {error_msg}", body_style))
    story.append(Spacer(1, 0.4*cm))

    # Data points table
    data_logs = []
    for level, msg, ts in logs:
        if level == "data":
            try:
                d = json.loads(msg)
                data_logs.append((d.get("point_name", ""), d.get("action", ""), d.get("value", "")))
            except (json.JSONDecodeError, KeyError):
                pass

    if data_logs:
        # Group by point_name
        by_point: dict[str, list[float]] = {}
        for pn, action, val in data_logs:
            by_point.setdefault(pn, []).append(float(val) if isinstance(val, (int, float)) else 0.0)

        story.append(Paragraph("Puntos Medidos", styles["Heading2"]))
        tdata = [["Punto", "Registros", "Mín", "Máx", "Último"]]
        for pn, vals in by_point.items():
            tdata.append([pn, str(len(vals)), f"{min(vals):.3f}", f"{max(vals):.3f}", f"{vals[-1]:.3f}"])
        t = Table(tdata, colWidths=[6*cm, 2.5*cm, 2.5*cm, 2.5*cm, 2.5*cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0891b2")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f9ff")]),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e2e8f0")),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ]))
        story.append(t)
        story.append(Spacer(1, 0.4*cm))

    # Full log table
    story.append(Paragraph("Log Completo", styles["Heading2"]))
    log_rows = [["Timestamp", "Nivel", "Mensaje"]]
    for level, msg, ts in logs:
        if level == "data":
            continue  # skip raw DATA JSON in text log
        ts_str = ts.strftime("%H:%M:%S") if ts else ""
        log_rows.append([ts_str, level.upper(), msg[:120]])

    if len(log_rows) > 1:
        lt = Table(log_rows, colWidths=[2*cm, 1.8*cm, 12.7*cm])
        lt.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#334155")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("FONTNAME", (0, 1), (-1, -1), "Courier"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e2e8f0")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(lt)

    # Footer
    story.append(Spacer(1, 0.6*cm))
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    story.append(Paragraph(f"Generado por Hira Server · {now}", ParagraphStyle("Footer", parent=body_style, fontSize=7, textColor=colors.HexColor("#94a3b8"))))

    doc.build(story)
    return buf.getvalue()


# ── PDF — History report ───────────────────────────────────────────────────────


def generate_history_pdf(point_id: int, start: datetime, end: datetime, bucket: str) -> bytes:
    """
    Genera PDF con reportlab del histórico de un punto en el rango dado.
    """
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
    )

    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT name, unit FROM points WHERE id = %s", (point_id,))
            point_row = cur.fetchone()
            if not point_row:
                raise ValueError(f"Punto {point_id} no encontrado")
            point_name, unit = point_row

            if bucket == "raw":
                cur.execute(
                    "SELECT time, value FROM point_history WHERE point_id = %s "
                    "AND time >= %s AND time <= %s ORDER BY time ASC LIMIT 5000",
                    (point_id, start, end),
                )
            else:
                interval_map = {"1min": "1 minute", "5min": "5 minutes", "1hour": "1 hour", "1day": "1 day"}
                interval = interval_map.get(bucket, "1 hour")
                cur.execute(
                    f"SELECT time_bucket('{interval}', time) AS bucket, AVG(value) "
                    "FROM point_history WHERE point_id = %s AND time >= %s AND time <= %s "
                    "GROUP BY bucket ORDER BY bucket ASC",
                    (point_id, start, end),
                )
            rows = cur.fetchall()
    finally:
        conn.close()

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    body_style = styles["Normal"]
    title_style = ParagraphStyle("HiraTitle", parent=styles["Heading1"], fontSize=16, spaceAfter=6)

    story: list[Any] = []

    story.append(Paragraph(f"Histórico: {point_name}", title_style))
    story.append(Paragraph(f"Unidad: {unit or '—'}", body_style))
    story.append(Paragraph(f"Rango: {start.strftime('%Y-%m-%d %H:%M')} → {end.strftime('%Y-%m-%d %H:%M')} UTC", body_style))
    story.append(Paragraph(f"Agregación: {bucket}", body_style))
    story.append(Spacer(1, 0.4*cm))

    # Statistics
    if rows:
        vals = [float(r[1]) for r in rows if r[1] is not None]
        if vals:
            import statistics
            stats_data = [
                ["Mín", "Máx", "Promedio", "Desv. Estándar", "Registros"],
                [
                    f"{min(vals):.3f}",
                    f"{max(vals):.3f}",
                    f"{statistics.mean(vals):.3f}",
                    f"{statistics.stdev(vals):.3f}" if len(vals) > 1 else "—",
                    str(len(vals)),
                ],
            ]
            st = Table(stats_data, colWidths=[3.2*cm]*5)
            st.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0891b2")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e2e8f0")),
            ]))
            story.append(Paragraph("Estadísticas del Período", styles["Heading2"]))
            story.append(st)
            story.append(Spacer(1, 0.4*cm))

    # Data table (cap at 200 rows for PDF readability)
    story.append(Paragraph(f"Datos ({min(len(rows), 200)} de {len(rows)} registros)", styles["Heading2"]))
    tdata = [["Timestamp", f"Valor ({unit or '—'})"]]
    for ts, val in rows[:200]:
        tdata.append([
            ts.strftime("%Y-%m-%d %H:%M:%S") if ts else "",
            f"{float(val):.4f}" if val is not None else "—",
        ])
    dt = Table(tdata, colWidths=[8*cm, 8*cm])
    dt.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#334155")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("FONTNAME", (0, 1), (-1, -1), "Courier"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e2e8f0")),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
    ]))
    story.append(dt)

    story.append(Spacer(1, 0.6*cm))
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    story.append(Paragraph(f"Generado por Hira Server · {now}", ParagraphStyle("Footer", parent=body_style, fontSize=7, textColor=colors.HexColor("#94a3b8"))))

    doc.build(story)
    return buf.getvalue()
