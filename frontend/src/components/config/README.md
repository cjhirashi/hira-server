# frontend/src/components/config/

## Propósito
Páginas y tabs del Configurador — UI de administración CRUD para áreas, dispositivos, puntos y usuarios. Sprint 7.

## Archivos

| Archivo | Descripción |
|---|---|
| `ConfigPage.tsx` | Contenedor principal con navegación por tabs (Áreas / Dispositivos / Puntos / Usuarios). Montado en la ruta `/config`. |
| `AreasTab.tsx` | CRUD de áreas: tabla con nombre y descripción, modal para crear/editar, botón eliminar con confirmación. |
| `DevicesTab.tsx` | CRUD de dispositivos: tabla con estado live, modal create/edit, elimina solo dispositivos no-simulador. |
| `PointsTab.tsx` | CRUD de puntos: carga todos los dispositivos y sus puntos, filtro por dispositivo, modal con campos completos. |
| `UsersTab.tsx` | Gestión de usuarios: create con password, edit (nombre + rol), desactivar via `PATCH /users/{id}/disable`. |

## Cómo funciona

1. `App.tsx` monta `<ConfigPage />` en la ruta `/config`.
2. `ConfigPage` mantiene estado interno del tab activo y renderiza el tab correspondiente.
3. Cada tab usa `api` de `services/api.ts` (axios con JWT automático) para consumir los endpoints del Configurador (`config:read` / `config:write`).
4. Los modales de creación/edición aparecen como overlays (posición fixed) — no bloquean la tabla subyacente.

## Dependencias

- `services/api.ts` — cliente axios con interceptor de JWT
- Endpoints backend: `GET/POST/PUT/DELETE /areas`, `GET/POST/PUT/DELETE /devices`, `GET/POST/PUT/DELETE /points`, `GET/POST/PATCH /users`, `PATCH /users/{id}/disable`
- CSS custom properties de Material Design 3 y tokens Hira (`var(--md-sys-color-*)`, `var(--hira-*)`)
