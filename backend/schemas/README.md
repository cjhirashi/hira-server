# backend/schemas/

Pydantic schemas para validación de requests y serialización de responses.

## Convención

- Un archivo por dominio: `auth.py`, `devices.py`, `points.py`, etc.
- Separar schemas de request y response dentro del mismo archivo
- Sufijos: `*Request`, `*Response`, `*Create`, `*Update`

## Ejemplo

```python
# schemas/devices.py
from pydantic import BaseModel

class DeviceCreate(BaseModel):
    name: str
    protocol: str
    address: str

class DeviceResponse(BaseModel):
    id: int
    name: str
    protocol: str
    status: str
```

## Archivos

| Archivo | Schemas |
|---------|---------|
| `auth.py` | `LoginRequest`, `RefreshRequest`, `UserInToken`, `TokenResponse`, `RefreshResponse` |
| `users.py` | `UserCreate`, `UserUpdate`, `UserResponse` |
