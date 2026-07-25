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

| Carpeta | Propósito |
|---------|-----------|
| `components/` | Componentes reutilizables (PointValue, AlarmBadge, etc.) |
| `hooks/` | Custom hooks (prefijo `use`) |
| `pages/` | Vistas completas por ruta |
| `styles/` | CSS global y tokens de Material Design 3 |

## Tecnologías

- React 18 con hooks (sin clases)
- TypeScript estricto (sin `any` sin justificación)
- Vite para desarrollo y build
- Material Design 3 con tokens CSS (`var(--md-sys-color-*)`)

## Contenido actual

Esqueleto mínimo (Sprint 0). La UI completa se implementa a partir de Sprint 5+.
