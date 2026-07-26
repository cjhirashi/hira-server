"""
Agente del Integrador — LangChain LCEL con tools del sistema Hira.

Usa bind_tools() + loop manual (compatible con LangChain 1.x).
Drivers síncronos (psycopg2 + redis-py) para evitar conflictos de event loop.
"""
import json
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool

from core.config import settings
from core.logger import get_logger

logger = get_logger(__name__)

_SYNC_URL = settings.database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")


def _get_engine():
    from sqlalchemy import create_engine
    return create_engine(_SYNC_URL, pool_pre_ping=True)


def _get_redis():
    import redis as redis_sync
    return redis_sync.from_url(settings.redis_url, decode_responses=True, socket_connect_timeout=5)


def _build_context() -> dict[str, str]:
    """Lee puntos y dispositivos de BD para inyectar en el system prompt."""
    from sqlalchemy import text

    engine = _get_engine()
    try:
        with engine.connect() as conn:
            points = conn.execute(
                text("SELECT name, unit, description FROM points ORDER BY name LIMIT 100")
            ).fetchall()
            devices = conn.execute(
                text("SELECT name, protocol, address FROM devices ORDER BY name LIMIT 50")
            ).fetchall()
    finally:
        engine.dispose()

    points_str = "\n".join(
        f"  - {p[0]} (unidad: {p[1] or 'n/a'}, desc: {p[2] or 'n/a'})" for p in points
    ) or "  (sin puntos registrados)"

    devices_str = "\n".join(
        f"  - {d[0]} ({d[1]}, IP: {d[2] or 'n/a'})" for d in devices
    ) or "  (sin dispositivos registrados)"

    return {"points": points_str, "devices": devices_str}


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
def get_point_list() -> str:
    """Lista todos los puntos con nombre, unidad, área y valor actual de Redis."""
    from sqlalchemy import text

    engine = _get_engine()
    try:
        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT p.id, p.name, p.unit, a.name as area "
                    "FROM points p LEFT JOIN areas a ON p.area_id = a.id "
                    "ORDER BY p.name LIMIT 100"
                )
            ).fetchall()
    finally:
        engine.dispose()

    if not rows:
        return "No hay puntos registrados en el sistema."

    r = _get_redis()
    lines = []
    for row in rows:
        raw = r.get(f"point:{row[0]}:value")
        value = "sin valor"
        if raw:
            data = json.loads(raw)
            value = str(data.get("value", "n/a"))
        lines.append(f"- {row[1]} | unidad: {row[2] or 'n/a'} | área: {row[3] or 'n/a'} | valor: {value}")
    r.close()

    return f"Puntos del sistema ({len(rows)} total):\n" + "\n".join(lines)


@tool
def get_device_list() -> str:
    """Lista todos los dispositivos con nombre, protocolo, IP y estado."""
    from sqlalchemy import text

    engine = _get_engine()
    try:
        with engine.connect() as conn:
            rows = conn.execute(
                text("SELECT name, protocol, address, status FROM devices ORDER BY name LIMIT 50")
            ).fetchall()
    finally:
        engine.dispose()

    if not rows:
        return "No hay dispositivos registrados en el sistema."

    lines = [
        f"- {r[0]} | protocolo: {r[1]} | IP: {r[2] or 'n/a'} | estado: {r[3] or 'desconocido'}"
        for r in rows
    ]
    return f"Dispositivos del sistema ({len(rows)} total):\n" + "\n".join(lines)


@tool
def get_alarm_status() -> str:
    """Lista alarmas activas (no reconocidas ni resueltas) del sistema."""
    from sqlalchemy import text

    engine = _get_engine()
    try:
        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT ae.id, ad.name, ae.triggered_at, ae.triggered_value "
                    "FROM alarms ae "
                    "JOIN alarm_definitions ad ON ae.definition_id = ad.id "
                    "WHERE ae.status = 'active' "
                    "ORDER BY ae.triggered_at DESC LIMIT 20"
                )
            ).fetchall()
    finally:
        engine.dispose()

    if not rows:
        return "No hay alarmas activas en este momento."

    lines = [
        f"- [{r[0]}] {r[1]} | disparada: {r[2]} | valor: {r[3]}"
        for r in rows
    ]
    return f"Alarmas activas ({len(rows)}):\n" + "\n".join(lines)


@tool
def create_logic_script_draft(description: str) -> str:
    """
    Genera un borrador de script Python compatible con la API hira
    basado en la descripción dada.
    """
    template = f'''# Borrador de script: {description}
# Generado por el Agente del Integrador de Hira
# Edita y ajusta según tus necesidades antes de ejecutar.

# La variable `hira` está disponible automáticamente en el contexto.
# Métodos disponibles:
#   hira.read("nombre_punto")  -> float | None
#   hira.write("nombre_punto", valor)  -> bool
#   hira.log("mensaje")        -> None (aparece en el log de ejecución)

# --- INICIO DEL SCRIPT ---

valor = hira.read("NOMBRE_PUNTO")
hira.log(f"Valor actual: {{valor}}")

if valor is not None and valor > UMBRAL:
    ok = hira.write("PUNTO_SALIDA", 1.0)
    hira.log(f"Escritura resultado: {{ok}}")
else:
    hira.log("Condición no cumplida o valor no disponible")

# --- FIN DEL SCRIPT ---
# Recuerda: el script se ejecuta en ciclo con el intervalo configurado.
# No uses import, os, sys ni ningún módulo externo — están bloqueados.
'''
    return template


@tool
def write_point(point_name: str, value: float) -> str:
    """
    Escribe un valor en un punto del sistema via Redis.
    ATENCIÓN: Esta acción modifica el sistema en tiempo real.
    Solo ejecutar si el usuario confirmó explícitamente.
    """
    from sqlalchemy import text
    from datetime import datetime, timezone

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
        return f"Error: punto '{point_name}' no encontrado."

    payload = json.dumps({
        "value": value,
        "quality": "good",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "ai_agent",
    })
    r = _get_redis()
    r.set(f"point:{row[0]}:value", payload)
    r.publish(f"point:{row[0]}:update", payload)
    r.close()

    logger.info("AI agent escribió punto", extra={"point": point_name, "value": value})
    return f"Punto '{point_name}' actualizado a {value}."


_TOOLS = [get_point_value, get_point_list, get_device_list, get_alarm_status, create_logic_script_draft, write_point]
_TOOLS_BY_NAME = {t.name: t for t in _TOOLS}

_SYSTEM_PROMPT = """Eres el Agente del Integrador de Hira SCADA. Tu rol es ayudar al integrador \
a entender y operar el sistema de automatización de edificios.

Contexto del proyecto actual:
Puntos registrados:
{points}

Dispositivos:
{devices}

Puedes leer valores en tiempo real, listar alarmas activas, y generar borradores de scripts Python \
usando la API `hira`. Para escribir valores a un punto, SIEMPRE pide confirmación explícita \
antes de ejecutar la herramienta write_point.
Responde en el mismo idioma del usuario."""


def _run_agent_loop(llm_with_tools: Any, messages: list, max_iterations: int = 5) -> dict[str, Any]:
    """Loop LCEL manual: invoca el LLM y ejecuta tool calls hasta obtener respuesta final."""
    tool_calls_log: list[dict] = []

    for _ in range(max_iterations):
        response: AIMessage = llm_with_tools.invoke(messages)
        messages.append(response)

        if not response.tool_calls:
            return {"output": response.content, "tool_calls_log": tool_calls_log}

        for tc in response.tool_calls:
            tool_fn = _TOOLS_BY_NAME.get(tc["name"])
            if tool_fn is None:
                result = f"Tool '{tc['name']}' no encontrada."
            else:
                try:
                    result = tool_fn.invoke(tc["args"])
                except Exception as exc:
                    result = f"Error ejecutando {tc['name']}: {exc}"

            tool_calls_log.append({"tool": tc["name"], "input": tc["args"], "output": str(result)})
            messages.append(ToolMessage(content=str(result), tool_call_id=tc["id"]))

    return {"output": "El agente alcanzó el máximo de iteraciones sin respuesta final.", "tool_calls_log": tool_calls_log}


def build_agent(api_key: str, provider: str, model: str):
    """Construye el LLM con tools enlazados para el loop LCEL."""
    if provider == "claude":
        from langchain_anthropic import ChatAnthropic
        llm = ChatAnthropic(model=model, api_key=api_key, timeout=25)
    elif provider == "openai":
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(model=model, api_key=api_key, timeout=25)
    else:
        raise ValueError(f"Provider desconocido: {provider}")

    ctx = _build_context()
    system_msg = _SYSTEM_PROMPT.format(**ctx)
    llm_with_tools = llm.bind_tools(_TOOLS)

    return {"llm": llm_with_tools, "system_msg": system_msg}


def invoke_agent(agent_state: dict, user_message: str) -> dict[str, Any]:
    """Invoca el agente con el mensaje del usuario. Retorna output y tool_calls."""
    messages = [
        SystemMessage(content=agent_state["system_msg"]),
        HumanMessage(content=user_message),
    ]
    return _run_agent_loop(agent_state["llm"], messages)
