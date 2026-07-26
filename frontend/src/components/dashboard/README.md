# components/dashboard — Dashboard de Mimics

## Propósito
Vista principal de operación: carga el primer mimic disponible, renderiza el canvas HVAC con los componentes SVG y muestra el panel de control para setpoints escribibles.

## Archivos
- `DashboardPage.tsx` — Página principal: llama `GET /api/v1/mimics`, activa `usePoints()` para suscripción WebSocket, renderiza `MimicCanvas` y `ControlPanel`
- `MimicCanvas.tsx` — Renderiza el canvas posicional. Dibuja líneas de conexión (duct/pipe) en SVG y posiciona cada componente HVAC absolutamente según `position` del elemento
- `ControlPanel.tsx` — Panel inferior con filas para cada elemento `Setpoint` escribible. Permite ingresar un valor y llamar a `POST /api/v1/points/{id}/write`

## Cómo funciona
```
DashboardPage
  ├── usePoints()           → activa WebSocket + actualiza pointsStore
  ├── GET /api/v1/mimics    → carga definición del primer mimic
  ├── MimicCanvas           → SVG connections + posicionamiento absoluto de componentes
  └── ControlPanel          → filas de escritura para Setpoints
```

## Dependencias
- `../../svg/hvac` — Componentes SVG HVAC
- `../../store/pointsStore` — Zustand store de puntos en tiempo real
- `../../hooks/usePoints` — Suscripción WebSocket
- `../../services/api` — Axios para carga de mimics y escritura de puntos
