# frontend/src/components/historicals/

Página de históricos: selector de punto, rangos temporales, gráfico Plotly y exportación CSV.

## Archivos

| Archivo | Descripción |
|---------|-------------|
| `HistoryPage.tsx` | Página completa con selector de punto, rangos rápidos (1h/24h/7d/30d), inputs de fecha manual, selector de intervalo, gráfico Plotly y botón de exportación CSV |

## Cómo funciona

1. Al montar, carga la lista de puntos vía `GET /api/v1/points` y la muestra en un `<select>` filtreable.
2. Al seleccionar un punto, `usePointHistory` hace `GET /api/v1/points/{id}/history` con los parámetros actuales.
3. El gráfico Plotly muestra la serie temporal como `scatter` con `mode: "lines"`.
4. Los puntos con `quality=bad` se excluyen de la traza principal (se podrían añadir como traza separada en rojo).
5. El botón "Exportar CSV" hace un fetch autenticado y descarga el blob directamente — evita exponer el token en la URL.

## Agregar nuevos intervalos de agregación

1. Añadir la opción al array `INTERVALS` en `HistoryPage.tsx`.
2. Añadir la traducción al dict `_BUCKET_MAP` en `backend/routers/history.py`.
3. Actualizar el enum `interval` en `docs/openapi.yaml` y en `schemas/history.py`.
4. Actualizar el `pattern` del Query param `interval` en el router.

## Dependencias

- `react-plotly.js` + `plotly.js-dist-min` — gráfico
- `usePointHistory` (`src/hooks/usePointHistory.ts`) — fetching de datos
- `services/api.ts` — cliente axios autenticado
