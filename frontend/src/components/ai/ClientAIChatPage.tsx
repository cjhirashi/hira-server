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

export function ClientAIChatPage() {
  const [messages, setMessages] = useState<Message[]>([
    { role: 'agent', content: 'Hola, soy el Asistente de Operaciones de Hira. Puedo consultar el estado de puntos, alarmas activas e historial de variables. ¿En qué puedo ayudarte?' },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

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
      const r = await fetch(`${API}/ai/cliente/chat`, {
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
      <h2 style={{ margin: '0 0 16px', color: 'var(--text-primary)' }}>Asistente de Operaciones</h2>

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
              background: m.role === 'user' ? 'var(--accent-subtle)' : 'var(--bg-elevated)',
              color: m.role === 'user' ? 'var(--accent-text)' : 'var(--text-primary)',
              borderRadius: m.role === 'user' ? '18px 18px 4px 18px' : '18px 18px 18px 4px',
              padding: '10px 14px',
              fontSize: 14,
              lineHeight: 1.5,
              whiteSpace: 'pre-wrap',
              border: `1px solid ${m.role === 'user' ? 'var(--accent)' : 'var(--border-subtle)'}`,
            }}>
              {m.content}
              {m.tool_calls && m.tool_calls.length > 0 && (
                <details style={{ marginTop: 8, fontSize: 12 }}>
                  <summary style={{ cursor: 'pointer', color: 'var(--accent)', opacity: 0.7 }}>
                    {m.tool_calls.length} herramienta{m.tool_calls.length > 1 ? 's' : ''} ejecutada{m.tool_calls.length > 1 ? 's' : ''}
                  </summary>
                  {m.tool_calls.map((tc, j) => (
                    <div key={j} style={{ marginTop: 6, opacity: 0.7, fontFamily: 'monospace' }}>
                      <div>→ {tc.tool}({JSON.stringify(tc.input)})</div>
                      <div style={{ color: 'var(--text-secondary)' }}>← {String(tc.output).slice(0, 200)}</div>
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
              background: 'var(--bg-elevated)',
              borderRadius: '18px 18px 18px 4px',
              padding: '10px 14px',
              fontSize: 14,
              color: 'var(--text-muted)',
              border: '1px solid var(--border-subtle)',
            }}>
              Procesando…
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div style={{ display: 'flex', gap: 8, paddingTop: 12, borderTop: '1px solid var(--border-subtle)' }}>
        <textarea
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKey}
          placeholder="Escribe tu pregunta… (Enter para enviar, Shift+Enter para nueva línea)"
          rows={2}
          style={{
            flex: 1,
            padding: '10px 12px',
            background: 'var(--bg-elevated)',
            border: '1px solid var(--border-default)',
            borderRadius: 10,
            color: 'var(--text-primary)',
            fontSize: 14,
            resize: 'none',
            fontFamily: 'inherit',
            lineHeight: 1.4,
            outline: 'none',
          }}
        />
        <button
          onClick={send}
          disabled={loading || !input.trim()}
          style={{
            background: loading || !input.trim() ? 'var(--bg-elevated)' : 'var(--accent)',
            color: loading || !input.trim() ? 'var(--text-muted)' : '#fff',
            border: `1px solid ${loading || !input.trim() ? 'var(--border-default)' : 'var(--accent)'}`,
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
