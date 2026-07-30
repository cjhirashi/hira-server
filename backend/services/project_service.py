"""
Servicio de exportación e importación de proyecto Hira.

Formato .hira: JSON con configuración completa (áreas, dispositivos, puntos,
scripts de lógica, scripts de prueba y documentos manuales), comprimido con gzip.
Los documentos auto-generados (AST, inventario) y los chunks RAG se excluyen.
"""
import gzip
import json
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session

from core.logger import get_logger

logger = get_logger(__name__)

HIRA_FORMAT_VERSION = "1.0"


def export_project(session: Session) -> bytes:
    """Construye el dict del proyecto y retorna bytes gzip."""
    areas = [
        {"original_id": r.id, "name": r.name, "description": r.description or ""}
        for r in session.execute(
            text("SELECT id, name, description FROM areas ORDER BY id")
        ).fetchall()
    ]

    devices = [
        {
            "original_id": r.id,
            "name": r.name,
            "protocol": r.protocol,
            "address": r.address,
            "port": r.port,
            "config_json": r.config_json,
            "area": r.area or "",
            "area_original_id": r.area_id,
            "is_simulator": bool(r.is_simulator),
            "auto_start": bool(r.auto_start),
        }
        for r in session.execute(
            text(
                "SELECT id, name, protocol, address, port, config_json, area, area_id, "
                "is_simulator, auto_start FROM devices ORDER BY id"
            )
        ).fetchall()
    ]

    points = [
        {
            "original_id": r.id,
            "name": r.name,
            "description": r.description or "",
            "object_type": r.object_type,
            "address": r.address,
            "unit": r.unit or "",
            "writable": bool(r.writable),
            "log_enabled": bool(r.log_enabled),
            "log_interval_ms": r.log_interval_ms,
            "history_interval_seconds": r.history_interval_seconds,
            "area": r.area or "",
            "area_original_id": r.area_id,
            "device_original_id": r.device_id,
        }
        for r in session.execute(
            text(
                "SELECT id, name, description, object_type, address, unit, writable, "
                "log_enabled, log_interval_ms, history_interval_seconds, area, area_id, device_id "
                "FROM points ORDER BY id"
            )
        ).fetchall()
    ]

    logic_scripts = [
        {
            "original_id": r.id,
            "name": r.name,
            "description": r.description or "",
            "code": r.code or "",
            "interval_seconds": r.interval_seconds,
        }
        for r in session.execute(
            text("SELECT id, name, description, code, interval_seconds FROM logic_scripts ORDER BY id")
        ).fetchall()
    ]

    test_scripts = [
        {
            "original_id": r.id,
            "name": r.name,
            "description": r.description or "",
            "code": r.code or "",
        }
        for r in session.execute(
            text("SELECT id, name, description, code FROM test_scripts ORDER BY id")
        ).fetchall()
    ]

    documents = [
        {
            "original_id": r.id,
            "title": r.title,
            "content_markdown": r.content_markdown or "",
        }
        for r in session.execute(
            text(
                "SELECT id, title, content_markdown FROM documents "
                "WHERE type = 'manual' ORDER BY id"
            )
        ).fetchall()
    ]

    payload = {
        "version": HIRA_FORMAT_VERSION,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "areas": areas,
        "devices": devices,
        "points": points,
        "logic_scripts": logic_scripts,
        "test_scripts": test_scripts,
        "documents": documents,
    }

    json_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    return gzip.compress(json_bytes)


def get_export_preview(session: Session) -> dict:
    """Retorna conteos y tamaño estimado sin generar el gzip."""
    def _count(table: str, where: str = "") -> int:
        q = f"SELECT COUNT(*) FROM {table}"
        if where:
            q += f" WHERE {where}"
        return session.execute(text(q)).scalar() or 0

    areas = _count("areas")
    devices = _count("devices")
    points = _count("points")
    logic_scripts = _count("logic_scripts")
    test_scripts = _count("test_scripts")
    documents = _count("documents", "type = 'manual'")

    # Estimación de tamaño: generamos el JSON en memoria sin comprimir
    payload = {
        "version": HIRA_FORMAT_VERSION,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "areas": areas,
        "devices": devices,
        "points": points,
        "logic_scripts": logic_scripts,
        "test_scripts": test_scripts,
        "documents": documents,
    }
    estimated_size_kb = round(len(json.dumps(payload)) / 1024, 1)

    return {
        "areas": areas,
        "devices": devices,
        "points": points,
        "logic_scripts": logic_scripts,
        "test_scripts": test_scripts,
        "documents": documents,
        "estimated_size_kb": estimated_size_kb,
    }


def import_project(data: bytes, mode: str, session: Session) -> dict:
    """
    Importa un archivo .hira.

    mode='merge': inserta solo lo que no existe (por nombre único).
    mode='replace': elimina toda la configuración actual antes de insertar.
    """
    try:
        json_bytes = gzip.decompress(data)
        payload = json.loads(json_bytes.decode("utf-8"))
    except Exception as exc:
        raise ValueError(f"Archivo .hira inválido o corrupto: {exc}") from exc

    if payload.get("version") != HIRA_FORMAT_VERSION:
        raise ValueError(
            f"Versión de formato no soportada: {payload.get('version')!r}. "
            f"Esperada: {HIRA_FORMAT_VERSION!r}"
        )

    imported = {k: 0 for k in ("areas", "devices", "points", "logic_scripts", "test_scripts", "documents")}
    skipped = {k: 0 for k in ("areas", "devices", "points", "logic_scripts", "test_scripts", "documents")}
    errors: list[str] = []

    if mode == "replace":
        # DELETE en cascada — orden inverso de FKs
        session.execute(text("DELETE FROM document_chunks"))
        session.execute(text("DELETE FROM documents WHERE type = 'manual'"))
        session.execute(text("DELETE FROM script_executions"))
        session.execute(text("DELETE FROM test_scripts"))
        session.execute(text("DELETE FROM logic_scripts"))
        session.execute(text("DELETE FROM points"))
        session.execute(text("DELETE FROM devices"))
        session.execute(text("DELETE FROM areas"))
        session.flush()

    # Map original_id → nuevo id para reconstruir FKs
    area_id_map: dict[int, int] = {}
    device_id_map: dict[int, int] = {}

    # ── Áreas ────────────────────────────────────────────────────────────────
    for a in payload.get("areas", []):
        try:
            if mode == "merge":
                existing = session.execute(
                    text("SELECT id FROM areas WHERE name = :name"), {"name": a["name"]}
                ).fetchone()
                if existing:
                    area_id_map[a["original_id"]] = existing.id
                    skipped["areas"] += 1
                    continue
            result = session.execute(
                text(
                    "INSERT INTO areas (name, description) VALUES (:name, :desc) RETURNING id"
                ),
                {"name": a["name"], "desc": a.get("description", "")},
            )
            new_id = result.fetchone().id
            area_id_map[a["original_id"]] = new_id
            imported["areas"] += 1
        except Exception as exc:
            errors.append(f"Area '{a.get('name')}': {exc}")

    # ── Dispositivos ─────────────────────────────────────────────────────────
    for d in payload.get("devices", []):
        try:
            resolved_area_id = area_id_map.get(d.get("area_original_id") or -1)
            if mode == "merge":
                existing = session.execute(
                    text("SELECT id FROM devices WHERE name = :name"), {"name": d["name"]}
                ).fetchone()
                if existing:
                    device_id_map[d["original_id"]] = existing.id
                    skipped["devices"] += 1
                    continue
            config_json = json.dumps(d.get("config_json")) if d.get("config_json") else None
            result = session.execute(
                text(
                    "INSERT INTO devices (name, protocol, address, port, config_json, area, area_id, "
                    "is_simulator, auto_start, status) "
                    "VALUES (:name, :protocol, :address, :port, :config_json::jsonb, :area, :area_id, "
                    ":is_simulator, :auto_start, 'offline') RETURNING id"
                ),
                {
                    "name": d["name"],
                    "protocol": d["protocol"],
                    "address": d["address"],
                    "port": d.get("port"),
                    "config_json": config_json,
                    "area": d.get("area", ""),
                    "area_id": resolved_area_id,
                    "is_simulator": bool(d.get("is_simulator", False)),
                    "auto_start": bool(d.get("auto_start", False)),
                },
            )
            new_id = result.fetchone().id
            device_id_map[d["original_id"]] = new_id
            imported["devices"] += 1
        except Exception as exc:
            errors.append(f"Device '{d.get('name')}': {exc}")

    # ── Puntos ───────────────────────────────────────────────────────────────
    for p in payload.get("points", []):
        try:
            resolved_device_id = device_id_map.get(p.get("device_original_id") or -1)
            if resolved_device_id is None:
                skipped["points"] += 1
                continue
            resolved_area_id = area_id_map.get(p.get("area_original_id") or -1)
            if mode == "merge":
                existing = session.execute(
                    text("SELECT id FROM points WHERE name = :name AND device_id = :did"),
                    {"name": p["name"], "did": resolved_device_id},
                ).fetchone()
                if existing:
                    skipped["points"] += 1
                    continue
            session.execute(
                text(
                    "INSERT INTO points (device_id, name, description, object_type, address, unit, "
                    "writable, log_enabled, log_interval_ms, history_interval_seconds, area, area_id) "
                    "VALUES (:device_id, :name, :description, :object_type, :address, :unit, "
                    ":writable, :log_enabled, :log_interval_ms, :history_interval_seconds, :area, :area_id)"
                ),
                {
                    "device_id": resolved_device_id,
                    "name": p["name"],
                    "description": p.get("description", ""),
                    "object_type": p["object_type"],
                    "address": p["address"],
                    "unit": p.get("unit", ""),
                    "writable": bool(p.get("writable", False)),
                    "log_enabled": bool(p.get("log_enabled", False)),
                    "log_interval_ms": p.get("log_interval_ms", 60000),
                    "history_interval_seconds": p.get("history_interval_seconds", 60),
                    "area": p.get("area", ""),
                    "area_id": resolved_area_id,
                },
            )
            imported["points"] += 1
        except Exception as exc:
            errors.append(f"Point '{p.get('name')}': {exc}")

    # ── Scripts de Lógica ────────────────────────────────────────────────────
    for ls in payload.get("logic_scripts", []):
        try:
            if mode == "merge":
                existing = session.execute(
                    text("SELECT id FROM logic_scripts WHERE name = :name"), {"name": ls["name"]}
                ).fetchone()
                if existing:
                    skipped["logic_scripts"] += 1
                    continue
            session.execute(
                text(
                    "INSERT INTO logic_scripts (name, description, code, interval_seconds, status) "
                    "VALUES (:name, :desc, :code, :interval, 'stopped')"
                ),
                {
                    "name": ls["name"],
                    "desc": ls.get("description", ""),
                    "code": ls.get("code", ""),
                    "interval": ls.get("interval_seconds", 10),
                },
            )
            imported["logic_scripts"] += 1
        except Exception as exc:
            errors.append(f"LogicScript '{ls.get('name')}': {exc}")

    # ── Scripts de Prueba ────────────────────────────────────────────────────
    for ts in payload.get("test_scripts", []):
        try:
            if mode == "merge":
                existing = session.execute(
                    text("SELECT id FROM test_scripts WHERE name = :name"), {"name": ts["name"]}
                ).fetchone()
                if existing:
                    skipped["test_scripts"] += 1
                    continue
            session.execute(
                text(
                    "INSERT INTO test_scripts (name, description, code) "
                    "VALUES (:name, :desc, :code)"
                ),
                {"name": ts["name"], "desc": ts.get("description", ""), "code": ts.get("code", "")},
            )
            imported["test_scripts"] += 1
        except Exception as exc:
            errors.append(f"TestScript '{ts.get('name')}': {exc}")

    # ── Documentos Manuales ──────────────────────────────────────────────────
    for doc in payload.get("documents", []):
        try:
            if mode == "merge":
                existing = session.execute(
                    text("SELECT id FROM documents WHERE title = :title AND type = 'manual'"),
                    {"title": doc["title"]},
                ).fetchone()
                if existing:
                    skipped["documents"] += 1
                    continue
            session.execute(
                text(
                    "INSERT INTO documents (title, type, content_markdown) "
                    "VALUES (:title, 'manual', :content)"
                ),
                {"title": doc["title"], "content": doc.get("content_markdown", "")},
            )
            imported["documents"] += 1
        except Exception as exc:
            errors.append(f"Document '{doc.get('title')}': {exc}")

    session.flush()
    logger.info(
        "Proyecto importado",
        extra={"mode": mode, "imported": imported, "skipped": skipped, "errors": len(errors)},
    )
    return {"imported": imported, "skipped": skipped, "errors": errors}
