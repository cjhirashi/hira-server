# components/logic

Motor de lógica Python — interfaz de usuario para crear, editar y ejecutar scripts Python que leen y escriben puntos del sistema.

## Archivos

| Archivo | Descripción |
|---|---|
| `LogicPage.tsx` | Página completa: lista de scripts (izquierda), editor Monaco o panel de logs (derecha) |

## Cómo funciona

1. **Lista de scripts** — carga `GET /api/v1/logic/scripts` al montar. Muestra nombre, estado y controles (▶/■/✎/🗑).
2. **Editor Monaco** — se abre al crear o editar un script. Lenguaje Python, tema `vs-dark`. Campos: nombre, descripción, intervalo en segundos, código.
3. **Guardar** — llama `POST /logic/scripts` (nuevo) o `PUT /logic/scripts/{id}` (edición). El backend valida sintaxis; si falla, muestra el mensaje de error de RestrictedPython.
4. **Guardar e Iniciar** — guarda y luego llama `POST /logic/scripts/{id}/start` en secuencia.
5. **Panel de logs** — carga `GET /logic/scripts/{id}/logs?limit=50`. Si el script está en estado `running`, hace polling automático cada 5 segundos con `setInterval`.

## Dependencias

- `@monaco-editor/react` — wrapper React para Monaco Editor (instalado en Sprint 8)
- `../../services/api` — cliente Axios con interceptor de autenticación
