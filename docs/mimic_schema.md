# Schema JSON de Mimics — Hira [M-01]

> Este documento es el contrato entre backend y frontend para el schema de mimics.
> Se define ANTES de implementar cualquier componente SVG.
> El schema no cambia en v0.3 — el editor drag-and-drop produce el mismo JSON.

---

## Schema raíz

```json
{
  "schema_version": "1.0",
  "id": "mimic-uuid",
  "name": "Sala de Máquinas Piso 3",
  "canvas": {
    "width": 1200,
    "height": 800,
    "background": "#1a1a2e"
  },
  "elements": [ ... ],
  "connections": [ ... ]
}
```

| Campo | Tipo | Descripción |
|---|---|---|
| `schema_version` | `string` | Versión del schema (actual: `"1.0"`) |
| `id` | `string` | UUID del mimic |
| `name` | `string` | Nombre descriptivo del mimic |
| `canvas.width` | `number` | Ancho del viewport SVG en píxeles |
| `canvas.height` | `number` | Alto del viewport SVG en píxeles |
| `canvas.background` | `string` | Color CSS de fondo del canvas |
| `elements` | `Element[]` | Lista de componentes HVAC posicionados |
| `connections` | `Connection[]` | Líneas tipo "pipe" entre elementos |

---

## Estructura base de un elemento

Todos los elementos comparten esta estructura base:

```json
{
  "id": "el-uuid",
  "type": "Fan",
  "position": { "x": 200, "y": 150 },
  "size": { "width": 80, "height": 80 },
  "label": "Ventilador AHU-01",
  "bindings": { ... },
  "style": { ... },
  "display": { ... }
}
```

| Campo | Tipo | Descripción |
|---|---|---|
| `id` | `string` | UUID único del elemento en este mimic |
| `type` | `string` | Tipo de componente SVG (ver tipos disponibles) |
| `position.x` | `number` | Coordenada X en el canvas SVG |
| `position.y` | `number` | Coordenada Y en el canvas SVG |
| `size.width` | `number` | Ancho del componente en píxeles SVG |
| `size.height` | `number` | Alto del componente en píxeles SVG |
| `label` | `string` | Etiqueta de texto visible bajo el componente |
| `bindings` | `object` | Mapeo de propiedades del componente a `point_id` |
| `style` | `object` | Colores del componente (usa tokens CSS cuando sea posible) |
| `display` | `object` | Configuración de visualización numérica |

---

## Bindings

Cada binding mapea una propiedad del componente a un punto de la base de datos:

```json
"bindings": {
  "running":   { "point_id": 42, "true_when": "value == 1" },
  "speed_pct": { "point_id": 43 },
  "fault":     { "point_id": 44, "true_when": "value == 1" },
  "value":     { "point_id": 51 }
}
```

### Campo `true_when`

Expresión simple evaluada en el cliente para convertir un valor numérico en booleano.

| Expresión | Evalúa `true` cuando |
|---|---|
| `"value == 1"` | El valor del punto es igual a 1 |
| `"value > 0"` | El valor del punto es mayor a 0 |
| `"value != 0"` | El valor del punto es distinto de 0 |
| `"value >= 50"` | El valor del punto es mayor o igual a 50 |

Si no se especifica `true_when`, el valor del punto se usa directamente (para valores numéricos o de string).

---

## Tipos de elementos disponibles en MVP

### `Fan` — Ventilador

```json
{
  "type": "Fan",
  "bindings": {
    "running":   { "point_id": 42, "true_when": "value == 1" },
    "speed_pct": { "point_id": 43 },
    "fault":     { "point_id": 44, "true_when": "value == 1" }
  },
  "style": {
    "color_normal": "#00ff88",
    "color_fault":  "#ff4444",
    "color_off":    "#888888"
  }
}
```

Animación CSS: `running = true` → aspas rotan (velocidad proporcional a `speed_pct`); `fault = true` → color `color_fault`.

---

### `Damper` — Compuerta de aire

```json
{
  "type": "Damper",
  "bindings": {
    "open_pct": { "point_id": 45 },
    "fault":    { "point_id": 46, "true_when": "value == 1" }
  },
  "style": {
    "color_normal": "#00b4d8",
    "color_fault":  "#ff4444",
    "color_off":    "#888888"
  }
}
```

Lamas rotan según `open_pct` (0% = cerrado, 100% = abierto 90°).

---

### `Valve` — Válvula

```json
{
  "type": "Valve",
  "bindings": {
    "open_pct": { "point_id": 47 },
    "fault":    { "point_id": 48, "true_when": "value == 1" }
  },
  "style": {
    "color_normal": "#00b4d8",
    "color_fault":  "#ff4444"
  }
}
```

Elemento interior (bola) rota según `open_pct`.

---

### `Chiller` — Enfriadora

```json
{
  "type": "Chiller",
  "bindings": {
    "running":  { "point_id": 49, "true_when": "value == 1" },
    "fault":    { "point_id": 50, "true_when": "value == 1" },
    "load_pct": { "point_id": 51 }
  },
  "style": {
    "color_running": "#00b4d8",
    "color_fault":   "#ff4444",
    "color_off":     "#888888"
  }
}
```

Rectángulo con copo de nieve. Texto de carga si hay binding `load_pct`.

---

### `AHU` — Unidad Manejadora de Aire

```json
{
  "type": "AHU",
  "bindings": {
    "running":      { "point_id": 52, "true_when": "value == 1" },
    "fault":        { "point_id": 53, "true_when": "value == 1" },
    "supply_temp":  { "point_id": 54 },
    "return_temp":  { "point_id": 55 }
  },
  "style": {
    "color_running": "#00ff88",
    "color_fault":   "#ff4444",
    "color_off":     "#888888"
  }
}
```

Rectángulo con flechas de flujo de aire y ventiladores internos que giran cuando `running = true`.

---

### `Sensor` — Sensor de campo

```json
{
  "type": "Sensor",
  "sensor_type": "temperature",
  "bindings": {
    "value": { "point_id": 56 }
  },
  "display": {
    "unit":     "°C",
    "decimals": 1,
    "min":      10,
    "max":      40
  }
}
```

Icono según `sensor_type`:
- `temperature` → termómetro
- `humidity` → gota
- `co2` → nube
- `pressure` → gauge

---

### `Setpoint` — Punto de ajuste (writable)

```json
{
  "type": "Setpoint",
  "bindings": {
    "value":    { "point_id": 57 },
    "writable": true
  },
  "display": {
    "unit":     "°C",
    "decimals": 1,
    "min":      16,
    "max":      28
  }
}
```

Muestra valor actual. Si `writable = true` → click abre input inline → `POST /api/v1/points/{point_id}/write`.

---

### `Label` — Etiqueta de texto

```json
{
  "type": "Label",
  "label": "Zona Norte — Piso 3",
  "style": { "font_size": 14, "color": "#aaaaaa" }
}
```

---

### `StatusIndicator` — Indicador de estado

```json
{
  "type": "StatusIndicator",
  "bindings": {
    "active": { "point_id": 58, "true_when": "value == 1" }
  },
  "style": {
    "color_active":   "#00ff88",
    "color_inactive": "#888888"
  }
}
```

---

## Connections

```json
"connections": [
  {
    "id":    "conn-uuid",
    "from":  "el-uuid-fan",
    "to":    "el-uuid-ahu",
    "style": "pipe"
  }
]
```

| Campo | Tipo | Descripción |
|---|---|---|
| `id` | `string` | UUID único de la conexión |
| `from` | `string` | `id` del elemento origen |
| `to` | `string` | `id` del elemento destino |
| `style` | `"pipe" \| "duct" \| "wire"` | Estilo visual de la línea |

---

## Ejemplo completo — Demo HVAC

```json
{
  "schema_version": "1.0",
  "name": "Demo HVAC",
  "canvas": { "width": 1200, "height": 800, "background": "#0d0d1a" },
  "elements": [
    {
      "id": "fan-01", "type": "Fan",
      "position": { "x": 300, "y": 200 }, "size": { "width": 80, "height": 80 },
      "label": "Ventilador AHU-01",
      "bindings": {
        "running": { "point_id": 3, "true_when": "value > 0" },
        "speed_pct": { "point_id": 3 }
      },
      "style": { "color_normal": "#00ff88", "color_fault": "#ff4444", "color_off": "#888888" }
    },
    {
      "id": "sensor-01", "type": "Sensor", "sensor_type": "temperature",
      "position": { "x": 600, "y": 200 }, "size": { "width": 80, "height": 80 },
      "label": "Temperatura Suministro",
      "bindings": { "value": { "point_id": 3 } },
      "display": { "unit": "°C", "decimals": 1, "min": 0, "max": 50 }
    },
    {
      "id": "setpoint-01", "type": "Setpoint",
      "position": { "x": 600, "y": 350 }, "size": { "width": 80, "height": 80 },
      "label": "Setpoint Temperatura",
      "bindings": { "value": { "point_id": 4 }, "writable": true },
      "display": { "unit": "°C", "decimals": 1, "min": 16, "max": 28 }
    }
  ],
  "connections": [
    { "id": "conn-01", "from": "fan-01", "to": "sensor-01", "style": "duct" }
  ]
}
```
