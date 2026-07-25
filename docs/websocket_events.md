# Contrato de Eventos WebSocket — Hira

> Este documento es el contrato entre backend y frontend para la comunicación
> en tiempo real. Se define ANTES de implementar el manager y los hooks.
> Cualquier cambio al contrato implica actualizar ambos lados.

---

## Endpoint

```
GET ws://<host>/ws
```

Requiere autenticación JWT via query param o header:

```
ws://localhost/ws?token=<jwt>
```

El servidor responde con un evento `connection:ack` al establecer la conexión.

---

## Formato de mensaje

Todos los mensajes son JSON con el campo `event` como discriminador:

```json
{
  "event": "<nombre_del_evento>",
  "data": { ... }
}
```

---

## Eventos servidor → cliente

### `connection:ack`

Enviado inmediatamente al conectar. Confirma que la conexión está activa.

```json
{
  "event": "connection:ack",
  "data": {
    "client_id": "string",
    "server_time": "2024-01-15T10:30:00.000Z"
  }
}
```

| Campo | Tipo | Descripción |
|---|---|---|
| `client_id` | `string` | UUID único asignado a esta conexión |
| `server_time` | `string` | ISO 8601 UTC del servidor al conectar |

---

### `point:update`

Publicado cuando un punto cambia de valor. El backend lo retransmite desde
el canal Redis `point:{id}:updates`.

```json
{
  "event": "point:update",
  "data": {
    "id": 42,
    "name": "zone_1_temp",
    "value": 23.5,
    "unit": "°C",
    "quality": "good",
    "timestamp": "2024-01-15T10:30:00.000Z"
  }
}
```

| Campo | Tipo | Descripción |
|---|---|---|
| `id` | `integer` | ID del punto en BD |
| `name` | `string` | Nombre del punto |
| `value` | `number \| null` | Valor actual. `null` si calidad `bad` |
| `unit` | `string \| null` | Unidad de ingeniería (p.e. `°C`, `%`, `Pa`) |
| `quality` | `"good" \| "uncertain" \| "bad"` | Calidad OPC-UA |
| `timestamp` | `string` | ISO 8601 UTC del timestamp del poller |

---

### `alarm:new`

Publicado cuando se activa una alarma nueva. Retransmitido desde Redis
canal `alarm:updates`.

```json
{
  "event": "alarm:new",
  "data": {
    "id": 7,
    "point_id": 42,
    "point_name": "zone_1_temp",
    "severity": "high",
    "message": "Temperatura sobre límite: 42.1 °C",
    "triggered_at": "2024-01-15T10:30:00.000Z",
    "acknowledged": false
  }
}
```

| Campo | Tipo | Descripción |
|---|---|---|
| `id` | `integer` | ID de la alarma |
| `point_id` | `integer` | ID del punto que la originó |
| `point_name` | `string` | Nombre del punto |
| `severity` | `"critical" \| "high" \| "medium" \| "low"` | Nivel de severidad |
| `message` | `string` | Mensaje descriptivo |
| `triggered_at` | `string` | ISO 8601 UTC de activación |
| `acknowledged` | `boolean` | `false` al dispararse, siempre |

---

### `alarm:resolved`

Publicado cuando una alarma se resuelve o reconoce.

```json
{
  "event": "alarm:resolved",
  "data": {
    "id": 7,
    "resolved_at": "2024-01-15T10:35:00.000Z"
  }
}
```

| Campo | Tipo | Descripción |
|---|---|---|
| `id` | `integer` | ID de la alarma resuelta |
| `resolved_at` | `string` | ISO 8601 UTC de resolución |

---

## Mensajes cliente → servidor

### `subscribe:points`

Solicita recibir actualizaciones de una lista de puntos. El servidor filtra
y solo retransmite los IDs suscritos a este cliente.

> Sprint 3: implementación simplificada — el servidor retransmite TODOS
> los puntos a TODOS los clientes. La suscripción selectiva es Sprint 4.

```json
{
  "event": "subscribe:points",
  "data": {
    "point_ids": [42, 43, 44]
  }
}
```

| Campo | Tipo | Descripción |
|---|---|---|
| `point_ids` | `integer[]` | IDs de puntos a suscribir |

---

### `unsubscribe:points`

Cancela la suscripción a una lista de puntos.

```json
{
  "event": "unsubscribe:points",
  "data": {
    "point_ids": [42]
  }
}
```

---

## Canal Redis → eventos WebSocket

| Canal Redis | Evento WebSocket generado |
|---|---|
| `point:{id}:updates` | `point:update` |
| `alarm:updates` | `alarm:new` o `alarm:resolved` según campo `type` |

El suscriptor Redis en FastAPI lifespan escucha estos canales con pattern
matching (`point:*:updates`) y retransmite a todos los clientes conectados.

---

## Consideraciones de seguridad

- El token JWT se valida al conectar. Si es inválido, el servidor cierra
  con código `4001` (Unauthorized).
- El token expirado durante una sesión activa cierra la conexión con `4001`
  en el siguiente mensaje del servidor.
- Los clientes no autenticados reciben `{"event": "error", "data": {"code": 4001, "message": "Unauthorized"}}` antes del cierre.
