import { useEffect, useState } from 'react'

const API = '/api/v1'

function authHeaders(method = 'GET') {
  const h: Record<string, string> = { Authorization: `Bearer ${localStorage.getItem('hira-token') ?? ''}` }
  if (method !== 'GET' && method !== 'DELETE') h['Content-Type'] = 'application/json'
  return h
}

interface Rule {
  id: number
  event_type: string
  channel: string
  destination: string
  threshold_minutes: number
  enabled: boolean
  created_at: string
}

const EVENT_TYPES = ['device_offline', 'worker_down', 'disk_full', 'alarm_flood', 'backup_failed']
const CHANNELS = ['email', 'webhook']

const initialForm = {
  event_type: EVENT_TYPES[0],
  channel: 'email',
  destination: '',
  threshold_minutes: 5,
  enabled: true,
}

export default function NotificationsConfigPage() {
  const [rules, setRules] = useState<Rule[]>([])
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [form, setForm] = useState({ ...initialForm })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = async () => {
    try {
      const r = await fetch(`${API}/notifications/rules`, { headers: authHeaders() })
      if (r.ok) setRules(await r.json())
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const toggleEnabled = async (rule: Rule) => {
    const r = await fetch(`${API}/notifications/rules/${rule.id}`, {
      method: 'PATCH',
      headers: authHeaders('PATCH'),
      body: JSON.stringify({ enabled: !rule.enabled }),
    })
    if (r.ok) {
      const updated: Rule = await r.json()
      setRules(prev => prev.map(x => x.id === updated.id ? updated : x))
    }
  }

  const deleteRule = async (id: number) => {
    if (!confirm('¿Eliminar esta regla de notificación?')) return
    const r = await fetch(`${API}/notifications/rules/${id}`, {
      method: 'DELETE',
      headers: authHeaders('DELETE'),
    })
    if (r.ok || r.status === 204) {
      setRules(prev => prev.filter(x => x.id !== id))
    }
  }

  const submit = async () => {
    setError(null)
    // Client-side validation
    if (form.channel === 'email' && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(form.destination)) {
      setError('El destino debe ser un email válido')
      return
    }
    if (form.channel === 'webhook' && !form.destination.startsWith('http')) {
      setError('El destino webhook debe comenzar con http:// o https://')
      return
    }

    setSaving(true)
    try {
      const r = await fetch(`${API}/notifications/rules`, {
        method: 'POST',
        headers: authHeaders('POST'),
        body: JSON.stringify(form),
      })
      if (r.ok) {
        const created: Rule = await r.json()
        setRules(prev => [...prev, created])
        setShowModal(false)
        setForm({ ...initialForm })
      } else {
        const d = await r.json()
        setError(d.detail ?? 'Error al crear la regla')
      }
    } finally {
      setSaving(false)
    }
  }

  return (
    <div style={{ maxWidth: 860 }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', marginBottom: 24 }}>
        <h2 style={{ margin: 0, fontSize: 'var(--text-xl)', fontWeight: 700, color: 'var(--text-primary)', flex: 1 }}>
          Notificaciones
        </h2>
        <button
          onClick={() => { setShowModal(true); setError(null) }}
          style={{
            background: 'var(--accent)',
            color: '#fff',
            border: 'none',
            borderRadius: 'var(--radius-md)',
            padding: '8px 16px',
            fontSize: 'var(--text-sm)',
            fontWeight: 600,
            cursor: 'pointer',
          }}
        >
          + Nueva Regla
        </button>
      </div>

      {/* Rules table */}
      {loading ? (
        <div style={{ color: 'var(--text-muted)', fontSize: 'var(--text-sm)' }}>Cargando…</div>
      ) : rules.length === 0 ? (
        <div style={{
          background: 'var(--bg-surface)',
          border: '1px solid var(--border-default)',
          borderRadius: 'var(--radius-lg)',
          padding: '24px',
          textAlign: 'center',
          color: 'var(--text-muted)',
          fontSize: 'var(--text-sm)',
        }}>
          Sin reglas configuradas. Crea una para empezar a recibir notificaciones.
        </div>
      ) : (
        <div style={{
          background: 'var(--bg-surface)',
          border: '1px solid var(--border-default)',
          borderRadius: 'var(--radius-lg)',
          overflow: 'hidden',
        }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 'var(--text-sm)' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border-default)' }}>
                {['Evento', 'Canal', 'Destino', 'Umbral', 'Activa', ''].map(h => (
                  <th key={h} style={{
                    textAlign: 'left',
                    padding: '10px 14px',
                    fontSize: 11,
                    fontWeight: 600,
                    color: 'var(--text-muted)',
                    letterSpacing: '0.08em',
                    textTransform: 'uppercase',
                  }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rules.map(rule => (
                <tr key={rule.id} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                  <td style={{ padding: '10px 14px', color: 'var(--text-primary)', fontFamily: 'var(--font-mono)', fontSize: 12 }}>
                    {rule.event_type}
                  </td>
                  <td style={{ padding: '10px 14px', color: 'var(--text-secondary)' }}>{rule.channel}</td>
                  <td style={{ padding: '10px 14px', color: 'var(--text-secondary)', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {rule.destination}
                  </td>
                  <td style={{ padding: '10px 14px', color: 'var(--text-secondary)' }}>
                    {rule.event_type === 'device_offline' ? `${rule.threshold_minutes} min` : '—'}
                  </td>
                  <td style={{ padding: '10px 14px' }}>
                    <button
                      onClick={() => toggleEnabled(rule)}
                      style={{
                        width: 36,
                        height: 20,
                        borderRadius: 10,
                        border: 'none',
                        cursor: 'pointer',
                        background: rule.enabled ? 'var(--accent)' : 'var(--border-default)',
                        position: 'relative',
                        transition: 'background 150ms',
                      }}
                      title={rule.enabled ? 'Desactivar' : 'Activar'}
                    >
                      <span style={{
                        position: 'absolute',
                        top: 2,
                        left: rule.enabled ? 18 : 2,
                        width: 16,
                        height: 16,
                        borderRadius: '50%',
                        background: '#fff',
                        transition: 'left 150ms',
                      }} />
                    </button>
                  </td>
                  <td style={{ padding: '10px 14px' }}>
                    <button
                      onClick={() => deleteRule(rule.id)}
                      style={{
                        background: 'transparent',
                        border: 'none',
                        cursor: 'pointer',
                        color: 'var(--text-muted)',
                        fontSize: 16,
                        padding: '2px 6px',
                        borderRadius: 'var(--radius-sm)',
                      }}
                      onMouseEnter={e => { e.currentTarget.style.color = 'var(--danger)'; e.currentTarget.style.background = 'var(--danger-subtle)' }}
                      onMouseLeave={e => { e.currentTarget.style.color = 'var(--text-muted)'; e.currentTarget.style.background = 'transparent' }}
                      title="Eliminar regla"
                    >
                      ×
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Modal */}
      {showModal && (
        <div style={{
          position: 'fixed', inset: 0,
          background: 'rgba(0,0,0,0.6)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          zIndex: 1000,
        }}
          onClick={e => { if (e.target === e.currentTarget) setShowModal(false) }}
        >
          <div style={{
            background: 'var(--bg-elevated)',
            border: '1px solid var(--border-default)',
            borderRadius: 'var(--radius-xl)',
            padding: 24,
            width: 420,
            display: 'flex',
            flexDirection: 'column',
            gap: 16,
          }}>
            <h3 style={{ margin: 0, fontSize: 'var(--text-base)', fontWeight: 700, color: 'var(--text-primary)' }}>
              Nueva Regla de Notificación
            </h3>

            <label style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
              <span style={labelStyle}>Evento</span>
              <select value={form.event_type} onChange={e => setForm(f => ({ ...f, event_type: e.target.value }))} style={inputStyle}>
                {EVENT_TYPES.map(et => <option key={et} value={et}>{et}</option>)}
              </select>
            </label>

            <label style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
              <span style={labelStyle}>Canal</span>
              <select value={form.channel} onChange={e => setForm(f => ({ ...f, channel: e.target.value }))} style={inputStyle}>
                {CHANNELS.map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            </label>

            <label style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
              <span style={labelStyle}>{form.channel === 'email' ? 'Email' : 'Webhook URL'}</span>
              <input
                type={form.channel === 'email' ? 'email' : 'url'}
                value={form.destination}
                onChange={e => setForm(f => ({ ...f, destination: e.target.value }))}
                placeholder={form.channel === 'email' ? 'admin@empresa.com' : 'https://hooks.example.com/...'}
                style={inputStyle}
              />
            </label>

            {form.event_type === 'device_offline' && (
              <label style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
                <span style={labelStyle}>Umbral (minutos offline)</span>
                <input
                  type="number"
                  min={1}
                  value={form.threshold_minutes}
                  onChange={e => setForm(f => ({ ...f, threshold_minutes: parseInt(e.target.value) || 5 }))}
                  style={inputStyle}
                />
              </label>
            )}

            {error && (
              <div style={{ fontSize: 'var(--text-xs)', color: 'var(--danger)', background: 'var(--danger-subtle)', borderRadius: 'var(--radius-md)', padding: '6px 10px' }}>
                {error}
              </div>
            )}

            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
              <button
                onClick={() => { setShowModal(false); setError(null) }}
                style={{ ...btnBase, background: 'var(--bg-hover)', color: 'var(--text-secondary)', border: '1px solid var(--border-default)' }}
              >
                Cancelar
              </button>
              <button
                onClick={submit}
                disabled={saving}
                style={{ ...btnBase, background: 'var(--accent)', color: '#fff', opacity: saving ? 0.7 : 1 }}
              >
                {saving ? 'Guardando…' : 'Guardar'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

const labelStyle: React.CSSProperties = {
  fontSize: 'var(--text-xs)',
  fontWeight: 600,
  color: 'var(--text-secondary)',
  letterSpacing: '0.05em',
  textTransform: 'uppercase',
}

const inputStyle: React.CSSProperties = {
  background: 'var(--bg-surface)',
  border: '1px solid var(--border-default)',
  borderRadius: 'var(--radius-md)',
  color: 'var(--text-primary)',
  padding: '8px 10px',
  fontSize: 'var(--text-sm)',
  outline: 'none',
}

const btnBase: React.CSSProperties = {
  padding: '8px 16px',
  borderRadius: 'var(--radius-md)',
  border: 'none',
  fontSize: 'var(--text-sm)',
  fontWeight: 600,
  cursor: 'pointer',
}
