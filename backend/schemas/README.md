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

## Contenido actual

Vacío en Sprint 0. Los schemas se crean junto con sus routers a partir de Sprint 1.
