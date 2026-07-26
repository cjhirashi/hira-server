# components/ai/

## Propósito
Componentes React del Agente del Integrador. Permite al usuario chatear con un LLM que tiene acceso a herramientas del sistema Hira (leer puntos, dispositivos, alarmas, generar scripts).

## Archivos

- **AIChatPage.tsx** — Página principal del agente. Interfaz de chat con historial de mensajes, input de texto y visualización colapsable de tool calls ejecutados.
- **AIConfigForm.tsx** — Formulario de configuración del agente. Permite seleccionar proveedor (Anthropic/OpenAI), modelo y guardar la API key cifrada.

## Cómo funciona

1. `AIChatPage` verifica si hay API key configurada al montar (`GET /api/v1/ai/config`)
2. El usuario escribe un mensaje y presiona Enter o "Enviar"
3. Se llama a `POST /api/v1/ai/chat` con el mensaje
4. El backend invoca el agente LangChain, que puede ejecutar tools internas
5. La respuesta incluye `reply` (texto) y `tool_calls` (herramientas usadas)
6. `AIConfigForm` permite cambiar proveedor/modelo y guardar la API key via `PUT /api/v1/ai/config`

## Dependencias

- `react-router-dom` — navegación (consumido desde Shell)
- `/api/v1/ai/*` — endpoints del router de IA del backend
- CSS variables de Material Design 3 para colores y tema
