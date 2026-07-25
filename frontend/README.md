# frontend/

Interfaz de usuario de Hira: React 18 + TypeScript + Vite.

## Cómo arrancar en desarrollo

```bash
# Dentro del contenedor (vía docker-compose.dev.yml)
npm run dev

# O localmente (requiere Node 20+)
npm install
npm run dev
```

Disponible en http://localhost:5173. El proxy de Vite redirige `/api/*` al backend en `http://backend:8000`.

## Estructura de `src/`

| Carpeta / Archivo | Propósito |
|---|---|
| `components/auth/LoginPage.tsx` | Formulario de login JWT |
| `components/layout/Shell.tsx` | Shell con navegación lateral y `<Outlet>` |
| `hooks/useWebSocket.ts` | Hook de conexión WebSocket con auto-reconexión exponencial |
| `hooks/usePoints.ts` | Hook que suscribe actualizaciones de puntos via WS |
| `store/pointsStore.ts` | Store Zustand de valores de puntos en tiempo real |
| `services/api.ts` | Cliente axios con interceptores de Auth y 401 |
| `App.tsx` | React Router: rutas `/login`, `/dashboard`, `/alarms`, etc. |

## Tecnologías

- React 18 + TypeScript — hooks, sin clases
- React Router v6 — rutas declarativas
- Zustand — estado global de puntos en tiempo real
- Axios — HTTP con interceptores JWT
- WebSocket nativo — tiempo real (auto-reconexión con backoff exponencial)
- Material Design 3 con tokens CSS (`var(--md-sys-color-*)`, `var(--hira-alarm-*)`)

## Flujo tiempo real

1. `useWebSocket` abre `ws://<host>/ws?token=<jwt>` al montar
2. Mensajes `point:update` se despachan a `usePointsStore` via `usePoints`
3. Componentes consumen `usePointsStore().points[id]` para renderizar valores en vivo
4. Si el WebSocket cierra, se reintenta con backoff: 1s → 2s → 4s → … → 30s máximo
