import { useState, useRef, useEffect } from 'react'

const API = '/api/v1'

function authHeaders() {
  return { Authorization: `Bearer ${localStorage.getItem('hira-token') ?? ''}`, 'Content-Type': 'application/json' }
}

interface Message {
  role: 'user' | 'agent'
  content: string
  tool_calls?: { tool: string; input: unknown; output: string }[] | null
}

export function AIChatPage() {
  const [messages, setMessages] = useState<Message[]>([
    { role: 'agent', content: 'Hola, soy el Agente del Integrador de Hira. Puedo ayudarte a consultar puntos, dispositivos, alarmas y generar borradores de scripts. ¿En qué puedo ayudarte?' },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [hasKey, setHasKey] = useState<boolean | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    fetch(`${API}/ai/config`, { headers: authHeaders() })
      .then(r => r.json())
      .then(d => setHasKey(d.has_api_key))
      .catch(() => setHasKey(false))
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const send = async () => {
    const text = input.trim()
    if (!text || loading) return
    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: text }])
    setLoading(true)
    try {
      const r = await fetch(`${API}/ai/chat`, {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify({ message: text }),
      })
      const d = await r.json()
      if (!r.ok) {
        setMessages(prev => [...prev, { role: 'agent', content: `Error: ${d.detail ?? 'Error desconocido'}` }])
      } else {
        setMessages(prev => [...prev, { role: 'agent', content: d.reply, tool_calls: d.tool_calls }])
      }
    } catch {
      setMessages(prev => [...prev, { role: 'agent', content: 'Error de red. Verifica tu conexión.' }])
    } finally {
      setLoading(false)
    }
  }

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 120px)', maxWidth: 800 }}>
      <h2 style={{ margin: '0 0 16px', color: 'var(--md-sys-color-on-surface)' }}>Agente del Integrador</h2>

      {hasKey === false && (
        <div style={{
          background: 'var(--md-sys-color-error-container, #4e0010)',
          color: 'var(--md-sys-color-on-error-container, #ffdad6)',
          borderRadius: 8,
          padding: '10px 14px',
          marginBottom: 16,
          fontSize: 13,
        }}>
          API key no configurada. Ve a <strong>Configuración &gt; IA</strong> para agregar tu clave de API.
        </div>
      )}

      <div style={{
        flex: 1,
        overflowY: 'auto',
        padding: '12px 0',
        display: 'flex',
        flexDirection: 'column',
        gap: 12,
      }}>
        {messages.map((m, i) => (
          <div key={i} style={{ display: 'flex', justifyContent: m.role === 'user' ? 'flex-end' : 'flex-start' }}>
            <div style={{
              maxWidth: '75%',
              background: m.role === 'user'
                ? 'var(--md-sys-color-primary-container, #003547)'
                : 'var(--md-sys-color-surface-container-high, #2a2a3a)',
              color: m.role === 'user'
                ? 'var(--md-sys-color-on-primary-container, #b3ecff)'
                : 'var(--md-sys-color-on-surface, #e0e0e0)',
              borderRadius: m.role === 'user' ? '18px 18px 4px 18px' : '18px 18px 18px 4px',
              padding: '10px 14px',
              fontSize: 14,
              lineHeight: 1.5,
              whiteSpace: 'pre-wrap',
            }}>
              {m.content}
              {m.tool_calls && m.tool_calls.length > 0 && (
                <details style={{ marginTop: 8, fontSize: 12 }}>
                  <summary style={{ cursor: 'pointer', color: 'var(--md-sys-color-primary, #00b4d8)', opacity: 0.7 }}>
                    {m.tool_calls.length} herramienta{m.tool_calls.length > 1 ? 's' : ''} ejecutada{m.tool_calls.length > 1 ? 's' : ''}
                  </summary>
                  {m.tool_calls.map((tc, j) => (
                    <div key={j} style={{ marginTop: 6, opacity: 0.7, fontFamily: 'monospace' }}>
                      <div>→ {tc.tool}({JSON.stringify(tc.input)})</div>
                      <div style={{ color: 'var(--md-sys-color-on-surface-variant)' }}>← {String(tc.output).slice(0, 200)}</div>
                    </div>
                  ))}
                </details>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div style={{ display: 'flex', justifyContent: 'flex-start' }}>
            <div style={{
              background: 'var(--md-sys-color-surface-container-high, #2a2a3a)',
              borderRadius: '18px 18px 18px 4px',
              padding: '10px 14px',
              fontSize: 14,
              color: 'var(--md-sys-color-on-surface-variant, #888)',
            }}>
              Procesando…
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div style={{ display: 'flex', gap: 8, paddingTop: 12, borderTop: '1px solid var(--md-sys-color-outline-variant, #333)' }}>
        <textarea
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKey}
          placeholder="Escribe tu pregunta… (Enter para enviar, Shift+Enter para nueva línea)"
          rows={2}
          style={{
            flex: 1,
            padding: '10px 12px',
            background: 'var(--md-sys-color-surface-container, #1e1e2e)',
            border: '1px solid var(--md-sys-color-outline-variant, #333)',
            borderRadius: 10,
            color: 'var(--md-sys-color-on-surface, #e0e0e0)',
            fontSize: 14,
            resize: 'none',
            fontFamily: 'inherit',
            lineHeight: 1.4,
          }}
        />
        <button
          onClick={send}
          disabled={loading || !input.trim()}
          style={{
            background: loading || !input.trim() ? 'var(--md-sys-color-surface-variant)' : 'var(--md-sys-color-primary, #00b4d8)',
            color: 'var(--md-sys-color-on-primary, #fff)',
            border: 'none',
            borderRadius: 10,
            padding: '0 20px',
            cursor: loading || !input.trim() ? 'not-allowed' : 'pointer',
            fontWeight: 600,
            fontSize: 14,
            minWidth: 80,
          }}
        >
          Enviar
        </button>
      </div>
    </div>
  )
}
