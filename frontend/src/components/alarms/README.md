# components/alarms — Panel de alarmas

## Propósito
Vista `/alarms` que muestra el estado en tiempo real del motor de alarmas: lista activa, reconocimiento y historial filtrable.

## Archivos
- `AlarmsPage.tsx` — Página principal con dos secciones: "Activas" (tabla con botón Reconocer) e "Historial" (filtros por prioridad y rango de fechas)

## Convención de colores por prioridad
| Prioridad | Token CSS |
|---|---|
| critical | `var(--hira-alarm-critical)` |
| high | `var(--hira-alarm-high)` |
| medium | `var(--hira-alarm-medium)` |
| low | `var(--hira-alarm-low)` |

## Cómo funciona
1. `useAlarms()` hook carga las alarmas activas via `GET /api/v1/alarms` en mount
2. El hook escucha eventos WebSocket: `alarm:new` → agrega, `alarm:resolved` → elimina, `alarm:acknowledged` → actualiza status
3. "Reconocer" llama a `POST /api/v1/alarms/{id}/acknowledge` y actualiza el store local
4. El badge en el sidebar lee `alarmsStore.unacknowledgedCount()` — se actualiza en tiempo real sin recargar

## Dependencias
- `../../hooks/useAlarms` — Suscripción WebSocket + carga inicial
- `../../store/alarmsStore` — Zustand store de alarmas
- `../../services/api` — Axios para historial y reconocimiento
