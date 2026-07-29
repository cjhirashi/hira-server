"""
API de pruebas funcionales inyectada en el sandbox de test scripts.

Extiende HiraAPI con:
- write() que establece un lock Redis (lock:point:{id}) antes de escribir
- assert_equal() / assert_between() para verificaciones funcionales
- Recolección de logs tipados (info/pass/fail/error/data) por ejecución
- Logs DATA: cada read/write exitoso emite un log estructurado JSON para análisis
"""
import json as _json
from core.hira_api import HiraAPI
from core.logger import get_logger

logger = get_logger(__name__)

_LOCK_TTL = 300  # segundos


class HiraTestAPI(HiraAPI):
    """
    Disponible en scripts de prueba bajo el nombre `hira`.

    Métodos adicionales:
        assert_equal(point_name, expected)          → bool
        assert_between(point_name, min_val, max_val) → bool
    """

    def __init__(self) -> None:
        super().__init__()
        self._test_logs: list[dict] = []
        self._passed: int = 0
        self._failed: int = 0

    def write(self, point_name: str, value: float) -> bool:
        """Establece lock Redis en el punto, escribe el valor y emite log DATA."""
        point_id = self._resolve_point_id(point_name)
        if point_id is None:
            self.log(f"write: punto '{point_name}' no encontrado")
            self._add_log("error", f"write: punto '{point_name}' no encontrado")
            return False
        self._get_redis().setex(f"lock:point:{point_id}", _LOCK_TTL, "test")
        ok = super().write(point_name, value)
        if ok:
            self._add_log("data", _json.dumps({"point_name": point_name, "action": "write", "value": float(value)}))
        return ok

    def assert_equal(self, point_name: str, expected: float) -> bool:
        """Verifica que el valor del punto sea igual al esperado."""
        actual = self.read(point_name)
        ok = actual is not None and abs(float(actual) - float(expected)) < 1e-9
        if ok:
            msg = f"PASS assert_equal('{point_name}', {expected})"
            self._passed += 1
            self._add_log("pass", msg)
        else:
            msg = f"FAIL assert_equal('{point_name}', {expected}) — got {actual}"
            self._failed += 1
            self._add_log("fail", msg)
        self.log(msg)
        return ok

    def assert_between(self, point_name: str, min_val: float, max_val: float) -> bool:
        """Verifica que el valor del punto esté en el rango [min_val, max_val]."""
        actual = self.read(point_name)
        ok = actual is not None and min_val <= float(actual) <= max_val
        if ok:
            msg = f"PASS assert_between('{point_name}', {min_val}, {max_val})"
            self._passed += 1
            self._add_log("pass", msg)
        else:
            msg = f"FAIL assert_between('{point_name}', {min_val}, {max_val}) — got {actual}"
            self._failed += 1
            self._add_log("fail", msg)
        self.log(msg)
        return ok

    def read(self, point_name: str) -> float | None:
        """Lee el valor del punto y emite log DATA si hay valor."""
        val = super().read(point_name)
        if val is not None:
            self._add_log("data", _json.dumps({"point_name": point_name, "action": "read", "value": float(val)}))
        return val

    def info(self, message: str) -> None:
        """Registra un mensaje informativo en los logs de prueba."""
        self._add_log("info", message)
        self.log(message)

    def _add_log(self, level: str, message: str) -> None:
        self._test_logs.append({"level": level, "message": message})

    def get_test_logs(self) -> list[dict]:
        return list(self._test_logs)

    def get_counts(self) -> tuple[int, int]:
        """Retorna (passed, failed)."""
        return self._passed, self._failed
