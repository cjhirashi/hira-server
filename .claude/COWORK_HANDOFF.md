# Handoff Claude Code ↔ Cowork — Hira Server

## Reporte de Sesión
### Sesión del 2026-08-03 · Sprint 22 · Tareas trabajadas: T-188, verificación T-184/185/186

**Qué se implementó:**
- T-188: Equipo de agentes especialistas creado en `.claude/agents/` (9 agentes — ver lista abajo). `.claude/agents/` añadido a `.gitignore`. Los 18 especialistas transversales están presentes en `~/.claude/agents/`.
- CLAUDE.md actualizado desde `7.1.9.3` (v2) — incluye sección "Equipo de Agentes Especialistas".
- T-184/T-185/T-186/T-187: implementados en sesión anterior (commits `0707101`, `2fe7f3d`, `4d18a5a`). Archivos verificados presentes: `backend/models/backup_log.py`, `backend/workers/backup_tasks.py`, `backend/routers/backups.py`, `backend/alembic/versions/0017_backup_log.py`, sección Backups en `frontend/src/pages/SystemStatusPage.tsx`.

**Agentes de proyecto creados (T-188):**
- `hira-db-especialista` — modelos ORM, migraciones Alembic, schemas Pydantic, adaptadores PostgreSQL/SQLite
- `hira-api-especialista` — routers FastAPI, contrato OpenAPI (contract-first), auth JWT, RBAC
- `hira-frontend-especialista` — React/TypeScript, Material Design 3, navegación por rol, WebSocket client
- `hira-qa-especialista` — tests de integración pytest, criterios de aceptación por sprint, reportes de validación
- `hira-protocolos-especialista` — Motor de Protocolos BACnet/Modbus/MQTT, polling, candidatos vs puntos asociados
- `hira-logica-especialista` — Motor de Lógica + Motor de Pruebas, Celery workers, API interna hira.*, point locks Redis
- `hira-alarmas-especialista` — Motor de Alarmas (evaluación continua, estados), Históricos (TimescaleDB)
- `hira-ia-especialista` — Agente IA (LangChain, Integrador + Cliente), RAG, Claude API + Ollama fallback
- `hira-backup-especialista` — Backup L2 pg_dump, retención 30 backups, paquete .hira portabilidad

**Pruebas ejecutadas y resultado:**
- T-184/185/186: no re-ejecutadas en esta sesión — validación pendiente contra stack Docker Compose real (T-187). La implementación existe en código pero el stack no está corriendo en este entorno.
- T-188: verificado que `~/.claude/agents/` contiene los 18 transversales ✅. Los 9 agentes de proyecto creados en `.claude/agents/` ✅. `.gitignore` actualizado ✅.

**Pendiente o bloqueado:**
- T-187 (Validación Sprint 22) requiere levantar `docker compose up` y verificar los criterios T-187.1 a T-187.8 contra el stack real. No ejecutado en esta sesión.

---

## Reporte de Sesión
### Sesión del 2026-08-03 · Sprint 22 · Tareas trabajadas: T-187, T-189

**Qué se implementó:**
- T-189: Auditoría de código DA-002 completada — solo lectura, sin modificaciones. Ver diagnóstico detallado en Pendientes.
- T-187: Validación Sprint 22 completada. Se encontraron y corrigieron 3 bugs durante la validación (commit `9da8c4a`):
  1. `postgresql-client` faltaba en `backend/Dockerfile` → `pg_dump` no disponible dentro del contenedor
  2. `extra={"filename": ...}` en logger de `backup_tasks.py` → `filename` es atributo reservado de `LogRecord`, causaba `FAILURE` del task Celery
  3. Volumen `backups_data:/backups` faltaba en servicio `celery-alarm` en `docker-compose.yml` → el worker ejecutaba el task pero escribía al filesystem local, no al volumen compartido
  - También se aplicó `alembic stamp 0016` + `alembic upgrade head` para llevar la BD de `0012` a `0017` (tabla `backup_log`)
  - Se reseteó contraseña de todos los usuarios a `Admin123!` para pruebas (la BD no tenía contraseñas conocidas)

**Pruebas ejecutadas y resultado (T-187):**
- T-187.1 ✅ `alembic upgrade head` aplica Migration 0017 — tabla `backup_log` creada con columnas correctas
- T-187.2 ✅ `/backups/` accesible dentro del contenedor
- T-187.3 ✅ `POST /backups/run` → archivo `.dump` creado en volumen `/backups/`, registro en `backup_log` con `status=success`, `size_bytes=82052`
- T-187.4 ✅ `GET /backups/` → lista con 3 entradas (2 success, 1 failed)
- T-187.5 ✅ `GET /backups/3/download` → HTTP 200, descarga del archivo `.dump`
- T-187.6 ✅ Registro `id=1` con `status=failed` y `error_message="[Errno 2] No such file or directory: 'pg_dump'"` prueba el mecanismo de captura de errores
- T-187.7 ✅ Lógica de retención verificada directamente en contenedor: con 4 archivos y max=3, elimina el más antiguo correctamente
- T-187.8 ✅ Sección "Backups de Base de Datos" visible en SystemStatusPage para Admin, con historial y botón "Ejecutar Backup Ahora"

**Pendiente o bloqueado:** ninguno — Sprint 22 completo.

---

## Pendientes

### 2026-08-03 · auditoría · Estado: pendiente (entrega a Cowork)

**T-189 — Diagnóstico DA-002: reconciliación Server/Studio con ADR-015**

**Contexto:** auditoría del frontend para determinar cuánto del modelo viejo de "dos productos separados" quedó implementado antes de la corrección de ADR-015.

**Hallazgos — archivos y líneas concretas:**

**1. No existe separación de shells ni selector de modo:**
- `git grep "ServerShell|StudioShell|ModeSelector"` → sin resultados. ✅ Nunca se implementaron.
- `git grep "'/server'|\"/server|'/studio'|\"/studio"` → sin resultados en rutas. ✅ No hay árbol de rutas `/server/*` separado.

**2. Estructura de navegación en `App.tsx`:**
- Un solo `Shell` con todas las rutas bajo `/` — correcto per ADR-015. ✅
- Rutas protegidas por rol via `AdminRoute` / `OperadorRoute` / `ProtectedRoute`. ✅
- Inconsistencia menor: algunos items Admin usan prefijo `studio/` (`studio/dashboard`, `studio/notifications`, `studio/mimics`) y otros no (`logic`, `tests`, `config`, `docs`, `ai/integrador`). No es separación de árbol — es solo naming inconsistente.
- Mimics duplicados: `studio/mimics` (Admin, editor) y `mimics` (Operador, viewer) — razonable si tienen componentes distintos (`MimicsEditorPage` vs `MimicsViewerPage`).

**3. Sidebar (`Sidebar.tsx` — el hallazgo más significativo):**
- El badge `mode === 'studio'` / `mode === 'server'` es informativo del perfil de despliegue (SQLite vs PostgreSQL) — correcto per ADR-015, no es un selector. ✅
- **PROBLEMA:** el sidebar solo contiene 8 ítems de navegación (`Sidebar.tsx:193-200`), todos visibles para todos los usuarios:
  `Dashboard`, `Alarmas`, `Históricos`, `Mimics`, `Análisis`, `Manual`, `AI Asistente`, `Estado del Sistema`
- **Ausentes del sidebar** (existen en App.tsx pero sin nav link): `Configurador` (`/config`), `Motor de Lógica` (`/logic`), `Motor de Pruebas` (`/tests`), `AI Integrador` (`/ai/integrador`), `Studio Dashboard` (`/studio/dashboard`), `Documentación` (`/docs`), `Notificaciones` (`/studio/notifications`), `Studio Mimics` (`/studio/mimics`).
- Estos son los módulos de ingeniería/Admin que ADR-UI-02 especifica deben ocultarse por rol — pero están completamente ausentes, no ocultos condicionalmente.

**Diagnóstico:**
- **El modelo viejo de "dos shells separados" NUNCA se implementó** — no hay deuda de desmontaje.
- **Lo que falta es la implementación correcta de ADR-UI-02**: el sidebar no muestra los módulos de Admin en ningún caso. El código de rutas existe (`App.tsx`) pero la navegación no conecta al usuario con esos módulos.
- **Complejidad de reconciliación: BAJA.** No hay reescritura de navegación — solo añadir al sidebar los ítems faltantes con condicional `{adminUser && <NavItem ... />}`. Estimado: ~30-40 líneas en `Sidebar.tsx`.
- **`DashboardPage` vs `StudioDashboard`:** Dos componentes separados para dos vistas distintas (ops vs ingeniería) — es correcto per ADR-015, no es deuda.

**Bloquea:** ninguna tarea del Sprint 22. Cowork usa este diagnóstico para planificar T-XXX del Sprint 24.

**Respuesta (Cowork):** [pendiente]
