import { useState, useEffect } from 'react'

const API = '/api/v1'

function authHeaders() {
  return { Authorization: `Bearer ${localStorage.getItem('hira-token') ?? ''}`, 'Content-Type': 'application/json' }
}

interface AIConfig {
  provider: string
  model: string
  has_api_key: boolean
  updated_at: string
}

const PROVIDERS = [
  { id: 'claude', label: 'Anthropic Claude', models: ['claude-sonnet-4-6', 'claude-opus-5', 'claude-haiku-4-5-20251001'] },
  { id: 'openai', label: 'OpenAI', models: ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo'] },
]

export function AIConfigForm() {
  const [config, setConfig] = useState<AIConfig | null>(null)
  const [provider, setProvider] = useState('claude')
  const [model, setModel] = useState('claude-sonnet-4-6')
  const [apiKey, setApiKey] = useState('')
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    fetch(`${API}/ai/config`, { headers: authHeaders() })
      .then(r => r.json())
      .then(d => {
        setConfig(d)
        setProvider(d.provider)
        setModel(d.model)
      })
      .catch(() => setError('Error al cargar configuración de IA'))
  }, [])

  const currentProviderModels = PROVIDERS.find(p => p.id === provider)?.models ?? []

  const handleSave = async () => {
    if (!apiKey.trim()) { setError('Ingresa una API key'); return }
    setSaving(true); setMsg(''); setError('')
    try {
      const r = await fetch(`${API}/ai/config`, {
        method: 'PUT',
        headers: authHeaders(),
        body: JSON.stringify({ provider, model, api_key: apiKey }),
      })
      if (!r.ok) { const d = await r.json(); throw new Error(d.detail ?? 'Error'); }
      const d = await r.json()
      setConfig(d); setApiKey(''); setMsg('Configuración guardada ✓')
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Error al guardar')
    } finally { setSaving(false) }
  }

  const handleDeleteKey = async () => {
    if (!confirm('¿Eliminar la API key guardada?')) return
    const r = await fetch(`${API}/ai/config/api-key`, { method: 'DELETE', headers: authHeaders() })
    if (r.ok) { setConfig(prev => prev ? { ...prev, has_api_key: false } : prev); setMsg('API key eliminada') }
  }

  return (
    <div style={{ maxWidth: 520 }}>
      <h3 style={{ margin: '0 0 20px', color: 'var(--md-sys-color-on-surface)' }}>Agente del Integrador</h3>

      {config?.has_api_key && (
        <div style={{
          background: 'var(--md-sys-color-primary-container, #003547)',
          borderRadius: 8,
          padding: '10px 14px',
          marginBottom: 20,
          fontSize: 13,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}>
          <span style={{ color: 'var(--md-sys-color-on-primary-container, #b3ecff)' }}>
            API key configurada ✓ — {config.provider} / {config.model}
          </span>
          <button
            onClick={handleDeleteKey}
            style={{ background: 'none', border: 'none', color: 'var(--md-sys-color-error, #cf6679)', cursor: 'pointer', fontSize: 12 }}
          >
            Eliminar
          </button>
        </div>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        <label style={{ fontSize: 13, color: 'var(--md-sys-color-on-surface-variant)' }}>
          Proveedor
          <select
            value={provider}
            onChange={e => { setProvider(e.target.value); setModel(PROVIDERS.find(p => p.id === e.target.value)?.models[0] ?? '') }}
            style={selectStyle}
          >
            {PROVIDERS.map(p => <option key={p.id} value={p.id}>{p.label}</option>)}
          </select>
        </label>

        <label style={{ fontSize: 13, color: 'var(--md-sys-color-on-surface-variant)' }}>
          Modelo
          <select value={model} onChange={e => setModel(e.target.value)} style={selectStyle}>
            {currentProviderModels.map(m => <option key={m} value={m}>{m}</option>)}
          </select>
        </label>

        <label style={{ fontSize: 13, color: 'var(--md-sys-color-on-surface-variant)' }}>
          API Key
          <input
            type="password"
            value={apiKey}
            onChange={e => setApiKey(e.target.value)}
            placeholder={config?.has_api_key ? 'Dejar vacío para mantener la actual' : 'sk-ant-... / sk-...'}
            style={{ ...inputStyle, fontFamily: 'monospace', fontSize: 12 }}
          />
        </label>

        {msg && <p style={{ color: 'var(--md-sys-color-primary, #00b4d8)', fontSize: 13, margin: 0 }}>{msg}</p>}
        {error && <p style={{ color: 'var(--md-sys-color-error, #cf6679)', fontSize: 13, margin: 0 }}>{error}</p>}

        <button
          onClick={handleSave}
          disabled={saving}
          style={{
            background: saving ? 'var(--md-sys-color-surface-variant)' : 'var(--md-sys-color-primary, #00b4d8)',
            color: 'var(--md-sys-color-on-primary, #fff)',
            border: 'none',
            borderRadius: 8,
            padding: '10px 20px',
            cursor: saving ? 'not-allowed' : 'pointer',
            fontWeight: 600,
            fontSize: 14,
            alignSelf: 'flex-start',
          }}
        >
          {saving ? 'Guardando…' : 'Guardar configuración'}
        </button>
      </div>
    </div>
  )
}

const selectStyle: React.CSSProperties = {
  display: 'block',
  marginTop: 6,
  width: '100%',
  padding: '8px 10px',
  background: 'var(--md-sys-color-surface-container, #1e1e2e)',
  border: '1px solid var(--md-sys-color-outline-variant, #333)',
  borderRadius: 6,
  color: 'var(--md-sys-color-on-surface, #e0e0e0)',
  fontSize: 13,
}

const inputStyle: React.CSSProperties = {
  display: 'block',
  marginTop: 6,
  width: '100%',
  padding: '8px 10px',
  background: 'var(--md-sys-color-surface-container, #1e1e2e)',
  border: '1px solid var(--md-sys-color-outline-variant, #333)',
  borderRadius: 6,
  color: 'var(--md-sys-color-on-surface, #e0e0e0)',
  fontSize: 13,
  boxSizing: 'border-box',
}
