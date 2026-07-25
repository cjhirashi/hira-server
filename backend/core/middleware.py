import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from core.logger import trace_id_var

TRACE_ID_HEADER = "X-Trace-ID"


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Lee X-Trace-ID del request (o genera uno nuevo) y lo propaga en:
    - ContextVar trace_id_var → todos los loggers lo leen automáticamente
    - Header X-Trace-ID de la respuesta
    """

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        trace_id = request.headers.get(TRACE_ID_HEADER) or str(uuid.uuid4())
        token = trace_id_var.set(trace_id)
        try:
            response: Response = await call_next(request)
        finally:
            trace_id_var.reset(token)

        response.headers[TRACE_ID_HEADER] = trace_id
        return response
