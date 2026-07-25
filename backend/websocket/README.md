# backend/websocket/

Gestión de conexiones WebSocket para streaming de datos en tiempo real al frontend.

## Responsabilidades previstas

- Mantener registro de conexiones activas por cliente
- Distribuir actualizaciones de valores de puntos a los clientes suscritos
- Distribuir eventos de alarma en tiempo real
- Gestionar reconexiones y timeouts

## Conexiones

Nginx limita a 10 conexiones WebSocket simultáneas por IP (`limit_conn_zone ws`).

## Contenido actual

Vacío en Sprint 0. Se implementa a partir de Sprint 4+.
