"""
Agente del Cliente — LangChain para operación SCADA.

Asiste al operador en monitoreo y operación. Solo lectura + reconocimiento de alarmas.
No tiene acceso a herramientas de construcción (write_point, create_logic_script, etc).
"""
import json
import time
from typing import Any

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import tool

from core.config import settings
from core.logger import get_logger

logger = get_logger(__name__)

_SYNC_URL = settings.sync_database_url


def _get_engine():
    from sqlalchemy import create_engine
    return create_engine(_SYNC_URL, pool_pre_ping=True)


def _get_redis():
    import redis as redis_sync
    return redis_sync.from_url(settings.redis_url, decode_responses=True, socket_connect_timeout=5)


@tool
def get_point_value(point_name: str) -> str:
    """Lee el valor actual de un punto por nombre desde Redis."""
    from sqlalchemy import text

    engine = _get_engine()
    try:
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT id FROM points WHERE name = :name LIMIT 1"),
                {"name": point_name},
            ).fetchone()
    finally:
        engine.dispose()

    if row is None:
        return f"Punto '{point_name}' no encontrado en el sistema."

    r = _get_redis()
    raw = r.get(f"point:{row[0]}:value")
    r.close()

    if raw is None:
        return f"Punto '{point_name}' existe pero no tiene valor en Redis (sin lectura reciente)."

    data = json.loads(raw)
    return f"Punto '{point_name}': valor={data.get('value')}, calidad={data.get('quality')}, timestamp={data.get('timestamp')}"


@tool
def get_active_alarms(severity: str = "all") -> str:
    """Lista alarmas activas. severity puede ser: all, critical, high, medium, low."""
    from sqlalchemy import text

    engine = _get_engine()
    try:
        with engine.connect() as conn:
            if severity == "all":
                rows = conn.execute(
                    text(
                        "SELECT ae.id, ad.name, ad.priority, ae.triggered_at, ae.value "
                        "FROM alarm_events ae "
                        "JOIN alarm_definitions ad ON ae.definition_id = ad.id "
                        "WHERE ae.status = 'active' "
                        "ORDER BY ae.triggered_at DESC LIMIT 20"
                    )
                ).fetchall()
            else:
                rows = conn.execute(
                    text(
                        "SELECT ae.id, ad.name, ad.priority, ae.triggered_at, ae.value "
                        "FROM alarm_events ae "
                        "JOIN alarm_definitions ad ON ae.definition_id = ad.id "
                        "WHERE ae.status = 'active' AND ad.priority = :sev "
                        "ORDER BY ae.triggered_at DESC LIMIT 20"
                    ),
                    {"sev": severity},
                ).fetchall()
    finally:
        engine.dispose()

    if not rows:
        return f"No hay alarmas activas{' con severidad ' + severity if severity != 'all' else ''}."

    lines = [f"- [{r[0]}] {r[1]} | severidad: {r[2]} | disparada: {r[3]} | valor: {r[4]}" for r in rows]
    return f"Alarmas activas ({len(rows)}):\n" + "\n".join(lines)


@tool
def get_point_history_summary(point_name: str, hours: int = 1) -> str:
    """Retorna resumen estadístico (promedio, mín, máx) del punto en las últimas N horas."""
    from sqlalchemy import text

    engine = _get_engine()
    try:
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT id FROM points WHERE name = :name LIMIT 1"),
                {"name": point_name},
            ).fetchone()

            if row is None:
                return f"Punto '{point_name}' no encontrado."

            point_id = row[0]

            if settings.deploy_mode == "studio":
                stats = conn.execute(
                    text(
                        "SELECT AVG(value), MIN(value), MAX(value), COUNT(*) "
                        "FROM point_history WHERE point_id = :pid "
                        "AND recorded_at >= datetime('now', :offset)"
                    ),
                    {"pid": point_id, "offset": f"-{hours} hours"},
                ).fetchone()
            else:
                stats = conn.execute(
                    text(
                        "SELECT AVG(value), MIN(value), MAX(value), COUNT(*) "
                        "FROM point_history WHERE point_id = :pid "
                        "AND recorded_at >= NOW() - INTERVAL ':hours hours'"
                    ),
                    {"pid": point_id, "hours": hours},
                ).fetchone()
    finally:
        engine.dispose()

    if stats is None or stats[3] == 0:
        return f"Sin datos históricos para '{point_name}' en las últimas {hours}h."

    return (
        f"Histórico de '{point_name}' (últimas {hours}h, {stats[3]} muestras): "
        f"promedio={stats[0]:.2f}, mín={stats[1]:.2f}, máx={stats[2]:.2f}"
    )


@tool
def get_device_status(device_name: str) -> str:
    """Retorna el estado de conectividad de un dispositivo por nombre."""
    from sqlalchemy import text

    engine = _get_engine()
    try:
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT name, protocol, ip_address, status FROM devices WHERE name = :name LIMIT 1"),
                {"name": device_name},
            ).fetchone()
    finally:
        engine.dispose()

    if row is None:
        return f"Dispositivo '{device_name}' no encontrado en el sistema."

    return f"Dispositivo '{row[0]}': protocolo={row[1]}, IP={row[2] or 'n/a'}, estado={row[3] or 'desconocido'}"


@tool
def acknowledge_alarm(alarm_id: int, comment: str = "") -> str:
    """Reconoce una alarma activa por su ID. Proporcionar un comentario es opcional."""
    from sqlalchemy import text
    from datetime import datetime, timezone

    engine = _get_engine()
    try:
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT id, status FROM alarm_events WHERE id = :id"),
                {"id": alarm_id},
            ).fetchone()

            if row is None:
                return f"Alarma {alarm_id} no encontrada."
            if row[1] != "active":
                return f"Alarma {alarm_id} no está activa (estado: {row[1]})."

            conn.execute(
                text(
                    "UPDATE alarm_events SET status='acknowledged', acknowledged_at=:now "
                    "WHERE id = :id"
                ),
                {"now": datetime.now(timezone.utc), "id": alarm_id},
            )
            conn.commit()
    finally:
        engine.dispose()

    logger.info("Alarma reconocida via AI Cliente", extra={"alarm_id": alarm_id, "comment": comment})
    return f"Alarma {alarm_id} reconocida correctamente." + (f" Comentario: {comment}" if comment else "")


@tool
def search_docs(query: str, top_k: int = 5) -> str:
    """
    Busca en la documentación del proyecto fragmentos relevantes para la consulta.
    Útil para responder preguntas sobre configuración del sistema, scripts y equipos.

    Args:
        query: Pregunta o tema a buscar
        top_k: Número máximo de fragmentos a retornar (default 5)

    Returns:
        String con los fragmentos más relevantes formateados para el agente.
    """
    try:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session
        from services.rag_service import semantic_search

        engine = create_engine(settings.sync_database_url, pool_pre_ping=True)
        try:
            with Session(engine) as session:
                results = semantic_search(query, top_k, session)
        finally:
            engine.dispose()

        if not results:
            return "No se encontró documentación relevante para esta consulta."

        parts = []
        for r in results:
            parts.append(f"**{r['document_title']}** (relevancia: {r['score']:.2f})\n{r['content']}")

        return "\n\n---\n\n".join(parts)
    except RuntimeError as exc:
        return f"No se pudo acceder a la documentación: {exc}"


_TOOLS = [get_point_value, get_active_alarms, get_point_history_summary, get_device_status, acknowledge_alarm, search_docs]

_SYSTEM_PROMPT = """Eres el Agente del Cliente de Hira SCADA. Tu función es asistir al operador \
en el monitoreo y operación del sistema.

Puedes:
- Consultar valores de puntos en tiempo real
- Revisar alarmas activas (filtradas por severidad si se requiere)
- Obtener resúmenes estadísticos de históricos
- Verificar el estado de conectividad de dispositivos
- Reconocer alarmas activas (SIEMPRE pide confirmación explícita antes de hacerlo)
- Buscar en la documentación del proyecto con search_docs para responder preguntas técnicas

NO puedes:
- Crear ni modificar scripts de lógica
- Modificar la configuración del sistema
- Escribir valores en campo (write_point no está disponible)
- Acceder a configuraciones del integrador

Responde siempre en el idioma del usuario. Sé conciso y directo."""


def build_agent(api_key: str, provider: str, model: str) -> AgentExecutor:
    """Construye el AgentExecutor del Cliente con los tools de operación."""
    if provider == "claude":
        from langchain_anthropic import ChatAnthropic
        llm = ChatAnthropic(model=model, api_key=api_key, timeout=25)
    elif provider == "openai":
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(model=model, api_key=api_key, timeout=25)
    else:
        raise ValueError(f"Provider desconocido: {provider}")

    prompt = ChatPromptTemplate.from_messages([
        ("system", _SYSTEM_PROMPT),
        MessagesPlaceholder("chat_history", optional=True),
        ("human", "{input}"),
        MessagesPlaceholder("agent_scratchpad"),
    ])

    agent = create_tool_calling_agent(llm, _TOOLS, prompt)
    return AgentExecutor(agent=agent, tools=_TOOLS, verbose=False, max_iterations=5)


def invoke_agent(
    agent_state: AgentExecutor,
    user_message: str,
    user_id: int | None = None,
    agent_type: str = "cliente",
) -> dict[str, Any]:
    """Invoca el AgentExecutor y registra el uso en ai_usage_log."""
    t0 = time.time()
    result = agent_state.invoke({"input": user_message})
    latency_ms = int((time.time() - t0) * 1000)

    output = result.get("output", "")
    intermediate = result.get("intermediate_steps", [])
    tool_calls_log = [
        {"tool": step[0].tool, "input": step[0].tool_input, "output": str(step[1])}
        for step in intermediate
        if hasattr(step[0], "tool")
    ]

    try:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session
        from models.ai_usage import AIUsageLog

        engine = create_engine(settings.sync_database_url, pool_pre_ping=True)
        try:
            with Session(engine) as session:
                log = AIUsageLog(
                    user_id=user_id,
                    agent_type=agent_type,
                    model="unknown",
                    tokens_input=0,
                    tokens_output=0,
                    latency_ms=latency_ms,
                    tool_calls_count=len(tool_calls_log),
                    query_preview=user_message[:200],
                )
                session.add(log)
                session.commit()
        finally:
            engine.dispose()
    except Exception as exc:
        logger.warning("No se pudo registrar ai_usage_log", extra={"error": str(exc)})

    return {"output": output, "tool_calls_log": tool_calls_log}
