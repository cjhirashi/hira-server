# backend/schemas/

Pydantic schemas para validación de requests y serialización de responses.

## Convención

- Un archivo por dominio: `auth.py`, `devices.py`, `points.py`, etc.
- Separar schemas de request y response dentro del mismo archivo
- Sufijos: `*Request`, `*Response`, `*Create`, `*Update`
- **No usar `EmailStr`** — usar `str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")` para soportar dominios `.local` internos

## Archivos

| Archivo | Schemas |
|---------|---------|
| `auth.py` | `LoginRequest`, `RefreshRequest`, `UserInToken`, `TokenResponse`, `RefreshResponse` |
| `users.py` | `UserCreate`, `UserUpdate`, `UserResponse` |
| `devices.py` | `DeviceCreate`, `DeviceUpdate`, `DeviceResponse`, `DeviceScanResult` |
| `points.py` | `PointValue`, `PointWriteRequest`, `PointWriteResponse` |
| `simulators.py` | `SimulatorCreate`, `SimulatorResponse` |
