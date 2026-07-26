# svg/hvac — Componentes SVG HVAC

## Propósito
Componentes React que renderizan dispositivos HVAC como SVG inline. Cada componente recibe `bindings` que mapean sus propiedades visuales a `point_id` del `pointsStore`. Los valores se actualizan en tiempo real vía WebSocket.

## Archivos
- `bindings.ts` — Hooks y helpers: `useBinding` (valor numérico), `useBoolBinding` (booleano con `true_when`), `collectPointIds`
- `Fan.tsx` — Ventilador con aspas rotatorias animadas por `requestAnimationFrame`. La velocidad de rotación escala con `speed_pct` binding
- `Damper.tsx` — Compuerta con louvers que giran según `open_pct` (0–100%)
- `Valve.tsx` — Válvula de mariposa con manija que rota según `open_pct`
- `Chiller.tsx` — Chiller con barra de carga y estado ON/OFF
- `AHU.tsx` — Unidad manejadora de aire con ventilador central y temperatura de suministro
- `Sensor.tsx` — Sensor genérico con anillo de progreso y soporte para temperatura, humedad, presión, CO₂, flujo
- `Setpoint.tsx` — Setpoint con flechas up/down que llaman a `POST /api/v1/points/{id}/write`
- `index.ts` — Re-exporta todos los componentes

## Cómo funciona
1. `MimicCanvas` renderiza cada elemento y pasa sus `bindings` y `display` al componente correspondiente
2. El componente llama a `useBinding(bindings.value)` → lee `pointsStore.points[point_id].value`
3. El `pointsStore` se actualiza en tiempo real via `usePoints()` hook que escucha el WebSocket

## Dependencias
- `../../store/pointsStore` — Zustand store con valores de puntos
- `../../services/api` — Axios para escrituras (solo Setpoint)
