# nginx/

Reverse proxy de Hira. Enruta el tráfico entre frontend, backend y WebSocket.

## Archivos

| Archivo | Propósito |
|---------|-----------|
| `nginx.conf` | Configuración principal: rate limiting, proxy hacia backend y frontend |

## Rutas

| Path | Destino |
|------|---------|
| `/api/*` | `http://backend:8000/` |
| `/ws/*` | `http://backend:8000/ws/` (WebSocket) |
| `/` | `http://frontend:80` |

## Rate limiting (V-03)

- **API REST**: 100 requests/s por IP, burst de 20 sin delay
- **WebSocket**: máximo 10 conexiones simultáneas por IP

Para ajustar los límites, editar `nginx.conf`:

```nginx
# Cambiar el rate de la zona api
limit_req_zone $binary_remote_addr zone=api:10m rate=100r/s;

# Cambiar el burst permitido
limit_req zone=api burst=20 nodelay;

# Cambiar el máximo de conexiones WS
limit_conn ws 10;
```

Después de editar, recargar Nginx sin downtime:

```bash
docker compose exec nginx nginx -s reload
```
