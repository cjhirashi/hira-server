"""Servicio de documentación — genera docs desde scripts AST e inventario del proyecto."""
from __future__ import annotations

import psycopg2
from contextlib import contextmanager
from datetime import datetime, timezone

from core.config import settings
from core.logger import get_logger
from services.ast_parser import generate_mermaid_flowchart

logger = get_logger(__name__)


@contextmanager
def _get_conn():
    sync_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
    conn = psycopg2.connect(sync_url)
    try:
        yield conn
    finally:
        conn.close()


# ── helpers ───────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row_to_dict(row, with_content: bool = True) -> dict:
    keys = ["id", "title", "type", "source_type", "source_id",
            "generated_at", "updated_at"]
    if with_content:
        keys.append("content_markdown")
    return dict(zip(keys, row[:len(keys)]))


# ── public API ────────────────────────────────────────────────────────────────

def get_all_documents() -> list[dict]:
    """Lista documentos sin content_markdown."""
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, title, type, source_type, source_id, generated_at, updated_at "
                "FROM documents ORDER BY updated_at DESC"
            )
            return [_row_to_dict(r, with_content=False) for r in cur.fetchall()]


def get_document(doc_id: int) -> dict:
    """Retorna documento completo con content_markdown. Lanza KeyError si no existe."""
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, title, type, source_type, source_id, generated_at, updated_at, content_markdown "
                "FROM documents WHERE id = %s",
                (doc_id,),
            )
            row = cur.fetchone()
    if row is None:
        raise KeyError(f"document {doc_id} not found")
    return _row_to_dict(row, with_content=True)


def create_manual_doc(title: str, content: str) -> dict:
    """Crea un documento manual. Retorna el documento creado."""
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO documents (title, type, content_markdown) "
                "VALUES (%s, 'manual', %s) RETURNING id",
                (title, content),
            )
            doc_id = cur.fetchone()[0]
        conn.commit()
    return get_document(doc_id)


def update_manual_doc(doc_id: int, title: str, content: str) -> dict:
    """Actualiza documento manual. Lanza ValueError si es auto-generado."""
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT type FROM documents WHERE id = %s", (doc_id,))
            row = cur.fetchone()
            if row is None:
                raise KeyError(f"document {doc_id} not found")
            if row[0] != "manual":
                raise ValueError("Solo se pueden actualizar documentos manuales")
            cur.execute(
                "UPDATE documents SET title = %s, content_markdown = %s, updated_at = NOW() "
                "WHERE id = %s",
                (title, content, doc_id),
            )
        conn.commit()
    return get_document(doc_id)


def delete_manual_doc(doc_id: int) -> None:
    """Elimina documento manual. Lanza ValueError si es auto-generado."""
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT type FROM documents WHERE id = %s", (doc_id,))
            row = cur.fetchone()
            if row is None:
                raise KeyError(f"document {doc_id} not found")
            if row[0] != "manual":
                raise ValueError("Solo se pueden eliminar documentos manuales")
            cur.execute("DELETE FROM documents WHERE id = %s", (doc_id,))
        conn.commit()


def generate_script_doc(script_id: int, source_type: str) -> dict:
    """
    Genera/regenera documentación de un script (logic o test).
    source_type: 'script_logic' | 'script_test'
    """
    with _get_conn() as conn:
        with conn.cursor() as cur:
            if source_type == "script_logic":
                cur.execute(
                    "SELECT name, description, code, created_at FROM logic_scripts WHERE id = %s",
                    (script_id,),
                )
            else:
                cur.execute(
                    "SELECT name, description, code, created_at FROM test_scripts WHERE id = %s",
                    (script_id,),
                )
            row = cur.fetchone()
            if row is None:
                raise KeyError(f"script {script_id} not found")
            name, description, code, created_at = row

        mermaid = generate_mermaid_flowchart(code or "", name)
        tipo_label = "Lógica Continua" if source_type == "script_logic" else "Prueba Funcional"
        desc_text = description or "Sin descripción"
        created_str = created_at.strftime("%Y-%m-%d %H:%M UTC") if created_at else "—"

        content = (
            f"# {name}\n\n"
            f"**Tipo:** Script de {tipo_label}  \n"
            f"**Creado:** {created_str}  \n"
            f"**Descripción:** {desc_text}\n\n"
            f"## Diagrama de Flujo\n\n"
            f"```mermaid\n{mermaid}\n```\n\n"
            f"## Código Fuente\n\n"
            f"```python\n{code or ''}\n```\n"
        )

        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO documents (title, type, source_type, source_id, content_markdown)
                VALUES (%s, 'auto_script', %s, %s, %s)
                ON CONFLICT (source_type, source_id)
                    WHERE source_id IS NOT NULL
                DO UPDATE SET
                    title = EXCLUDED.title,
                    content_markdown = EXCLUDED.content_markdown,
                    updated_at = NOW()
                RETURNING id
                """,
                (name, source_type, script_id, content),
            )
            doc_id = cur.fetchone()[0]
        conn.commit()

    logger.info("Documento generado", extra={"script_id": script_id, "source_type": source_type, "doc_id": doc_id})
    return get_document(doc_id)


def preview_mermaid(script_id: int, source_type: str) -> str:
    """Retorna solo el string Mermaid sin guardar en DB."""
    with _get_conn() as conn:
        with conn.cursor() as cur:
            table = "logic_scripts" if source_type == "script_logic" else "test_scripts"
            cur.execute(f"SELECT name, code FROM {table} WHERE id = %s", (script_id,))
            row = cur.fetchone()
    if row is None:
        raise KeyError(f"script {script_id} not found")
    name, code = row
    return generate_mermaid_flowchart(code or "", name)


def generate_inventory() -> dict:
    """Genera/regenera el inventario del proyecto (áreas/dispositivos/puntos)."""
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM areas")
            total_areas = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM devices")
            total_devices = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM points")
            total_points = cur.fetchone()[0]

            # Protocol summary
            cur.execute(
                "SELECT protocol, COUNT(*) as devices, "
                "(SELECT COUNT(*) FROM points p WHERE p.device_id IN "
                "(SELECT id FROM devices d2 WHERE d2.protocol = d.protocol)) as pts "
                "FROM devices d GROUP BY protocol ORDER BY protocol",
            )
            protocols = cur.fetchall()

            # Detail: areas → devices → points
            cur.execute(
                """
                SELECT a.name as area_name,
                       d.name as dev_name, d.protocol, d.address,
                       p.name as pt_name, p.object_type, p.unit, p.address as pt_addr
                FROM areas a
                LEFT JOIN devices d ON d.area_id = a.id
                LEFT JOIN points p ON p.device_id = d.id
                ORDER BY a.name, d.name, p.name
                """
            )
            rows = cur.fetchall()

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # Protocol table
    proto_table = "| Protocolo | Dispositivos | Puntos |\n|---|---|---|\n"
    for proto, dev_count, pt_count in protocols:
        proto_table += f"| {proto} | {dev_count} | {pt_count} |\n"

    # Detail grouped by area → device
    detail = ""
    current_area = None
    current_dev = None
    for area_name, dev_name, protocol, dev_addr, pt_name, obj_type, unit, pt_addr in rows:
        if area_name != current_area:
            current_area = area_name
            current_dev = None
            detail += f"\n### Área: {area_name or 'Sin área'}\n"
        if dev_name and dev_name != current_dev:
            current_dev = dev_name
            detail += f"\n#### {dev_name} ({protocol} · {dev_addr or '—'})\n\n"
            detail += "| Punto | Tipo | Unidad | Dirección |\n|---|---|---|---|\n"
        if pt_name:
            detail += f"| {pt_name} | {obj_type or '—'} | {unit or '—'} | {pt_addr or '—'} |\n"

    content = (
        f"# Inventario del Proyecto\n\n"
        f"**Generado:** {now_str}  \n"
        f"**Total áreas:** {total_areas} | **Total dispositivos:** {total_devices} | **Total puntos:** {total_points}\n\n"
        f"## Resumen por Protocolo\n\n{proto_table}\n"
        f"## Inventario Detallado\n{detail}\n"
    )

    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM documents WHERE type = 'auto_inventory' LIMIT 1")
            row = cur.fetchone()
            if row:
                doc_id = row[0]
                cur.execute(
                    "UPDATE documents SET content_markdown = %s, updated_at = NOW() WHERE id = %s",
                    (content, doc_id),
                )
            else:
                cur.execute(
                    "INSERT INTO documents (title, type, content_markdown) "
                    "VALUES ('Inventario del Proyecto', 'auto_inventory', %s) RETURNING id",
                    (content,),
                )
                doc_id = cur.fetchone()[0]
        conn.commit()

    logger.info("Inventario generado", extra={"doc_id": doc_id, "total_points": total_points})
    return get_document(doc_id)
