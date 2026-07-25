# backend/routers/

Endpoints FastAPI. Cada router implementa el contrato definido en `docs/openapi.yaml`.

## Convención

- Un archivo por dominio: `monitor.py`, `auth.py`, `devices.py`, etc.
- Cada router se registra en `main.py` con `app.include_router(...)`
- **El endpoint debe existir en `docs/openapi.yaml` antes de implementarlo**

## Archivos

| Archivo | Propósito |
|---------|-----------|
| `monitor.py` | `GET /health` — estado de todos los servicios (público) |
| `auth.py` | `POST /auth/login`, `/auth/refresh`, `/auth/logout` — autenticación y renovación de tokens |
| `users.py` | `GET/POST /users` y `GET/PATCH/DELETE /users/{id}` — CRUD de usuarios con RBAC |

## Cómo agregar un router nuevo

1. Añadir los endpoints al contrato en `docs/openapi.yaml`
2. Crear `backend/routers/nuevo_dominio.py` con un `APIRouter`
3. Registrarlo en `main.py`: `app.include_router(nuevo_router, prefix="/nuevo")`
