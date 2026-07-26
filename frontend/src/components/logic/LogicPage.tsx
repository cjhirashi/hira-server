import { useEffect, useRef, useState } from 'react'
import Editor from '@monaco-editor/react'
import { api } from '../../services/api'

interface Script {
  id: number
  name: string
  description: string | null
  code: string
  interval_seconds: number
  status: 'stopped' | 'running' | 'error'
  celery_task_id: string | null
  created_at: string
  updated_at: string
}

interface Execution {
  id: number
  script_id: number
  started_at: string
  ended_at: string | null
  status: 'success' | 'error'
  output: string | null
  error_message: string | null
}

const DEFAULT_CODE = `# API disponible:
# valor = hira.read("nombre_punto")
# hira.write("nombre_punto", valor)
# hira.log("mensaje")

valor = hira.read("temp_supply")
hira.log(f"Temperatura actual: {valor}")
`

const emptyForm = { name: '', description: '', code: DEFAULT_CODE, interval_seconds: 10 }

export default function LogicPage() {
  const [scripts, setScripts] = useState<Script[]>([])
  const [selected, setSelected] = useState<Script | null>(null)
  const [form, setForm] = useState(emptyForm)
  const [editId, setEditId] = useState<number | null>(null)
  const [logs, setLogs] = useState<Execution[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [showEditor, setShowEditor] = useState(false)
  const logsRef = useRef<HTMLDivElement>(null)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const loadScripts = async () => {
    try {
      const r = await api.get<Script[]>('/logic/scripts')
      setScripts(r.data)
    } catch {
      setError('Error al cargar scripts')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadScripts()
    return () => { if (pollRef.current) clearInterval(pollRef.current) }
  }, [])

  const loadLogs = async (scriptId: number) => {
    try {
      const r = await api.get<Execution[]>(`/logic/scripts/${scriptId}/logs?limit=50`)
      setLogs(r.data.reverse())
      setTimeout(() => logsRef.current?.scrollTo(0, logsRef.current.scrollHeight), 50)
    } catch { /* silenciar */ }
  }

  const selectScript = (s: Script) => {
    setSelected(s)
    loadLogs(s.id)
    if (pollRef.current) clearInterval(pollRef.current)
    if (s.status === 'running') {
      pollRef.current = setInterval(() => loadLogs(s.id), 5000)
    }
    setShowEditor(false)
    setError(null)
  }

  const openNew = () => {
    setEditId(null)
    setForm(emptyForm)
    setShowEditor(true)
    setError(null)
  }

  const openEdit = (s: Script) => {
    setEditId(s.id)
    setForm({ name: s.name, description: s.description ?? '', code: s.code, interval_seconds: s.interval_seconds })
    setShowEditor(true)
    setError(null)
  }

  const save = async (andStart = false) => {
    setSaving(true)
    setError(null)
    try {
      let saved: Script
      if (editId === null) {
        const r = await api.post<Script>('/logic/scripts', form)
        saved = r.data
      } else {
        const r = await api.put<Script>(`/logic/scripts/${editId}`, form)
        saved = r.data
      }
      setShowEditor(false)
      await loadScripts()
      selectScript(saved)
      if (andStart) {
        await api.post(`/logic/scripts/${saved.id}/start`)
        await loadScripts()
      }
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: string } } }).response?.data?.detail
      setError(detail ?? 'Error al guardar')
    } finally {
      setSaving(false)
    }
  }

  const start = async (s: Script) => {
    try {
      await api.post(`/logic/scripts/${s.id}/start`)
      await loadScripts()
      const fresh = scripts.find(x => x.id === s.id)
      if (fresh) {
        const updated = { ...fresh, status: 'running' as const }
        setSelected(updated)
        if (pollRef.current) clearInterval(pollRef.current)
        pollRef.current = setInterval(() => loadLogs(s.id), 5000)
      }
    } catch (e: unknown) {
      setError((e as { response?: { data?: { detail?: string } } }).response?.data?.detail ?? 'Error al iniciar')
    }
  }

  const stop = async (s: Script) => {
    try {
      await api.post(`/logic/scripts/${s.id}/stop`)
      if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null }
      await loadScripts()
      if (selected?.id === s.id) setSelected(prev => prev ? { ...prev, status: 'stopped' } : null)
    } catch (e: unknown) {
      setError((e as { response?: { data?: { detail?: string } } }).response?.data?.detail ?? 'Error al detener')
    }
  }

  const remove = async (s: Script) => {
    if (!confirm(`¿Eliminar script "${s.name}"?`)) return
    try {
      await api.delete(`/logic/scripts/${s.id}`)
      if (selected?.id === s.id) { setSelected(null); setLogs([]) }
      await loadScripts()
    } catch (e: unknown) {
      setError((e as { response?: { data?: { detail?: string } } }).response?.data?.detail ?? 'Error al eliminar')
    }
  }

  const statusColor = (s: string) => {
    if (s === 'running') return 'var(--hira-status-ok)'
    if (s === 'error') return 'var(--hira-alarm-critical)'
    return 'var(--hira-status-offline)'
  }

  return (
    <div style={{ display: 'flex', gap: 20, height: 'calc(100vh - 120px)' }}>

      {/* Panel izquierdo — lista de scripts */}
      <div style={{ width: 300, flexShrink: 0, display: 'flex', flexDirection: 'column', gap: 12 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h3 style={{ margin: 0 }}>Scripts</h3>
          <button onClick={openNew} style={btnStyle}>+ Nuevo</button>
        </div>

        {error && <p style={{ color: 'var(--hira-alarm-critical)', margin: 0, fontSize: 13 }}>{error}</p>}

        {loading ? <p>Cargando...</p> : (
          <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 8 }}>
            {scripts.length === 0 && <p style={{ color: 'var(--md-sys-color-on-surface-variant)', fontSize: 13 }}>Sin scripts. Crea el primero.</p>}
            {scripts.map(s => (
              <div
                key={s.id}
                onClick={() => selectScript(s)}
                style={{
                  padding: '10px 12px',
                  borderRadius: 8,
                  cursor: 'pointer',
                  background: selected?.id === s.id
                    ? 'var(--md-sys-color-primary-container, rgba(0,180,216,0.15))'
                    : 'var(--md-sys-color-surface-variant, #1e1e2e)',
                  border: `1px solid ${selected?.id === s.id ? 'var(--md-sys-color-primary, #00b4d8)' : 'transparent'}`,
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontWeight: 600, fontSize: 14 }}>{s.name}</span>
                  <span style={{ fontSize: 11, color: statusColor(s.status), fontWeight: 600 }}>
                    {s.status.toUpperCase()}
                  </span>
                </div>
                <div style={{ fontSize: 12, color: 'var(--md-sys-color-on-surface-variant)', marginTop: 2 }}>
                  cada {s.interval_seconds}s
                </div>
                <div style={{ display: 'flex', gap: 6, marginTop: 8 }}>
                  {s.status !== 'running'
                    ? <button onClick={e => { e.stopPropagation(); start(s) }} style={smallBtnStyle}>▶ Iniciar</button>
                    : <button onClick={e => { e.stopPropagation(); stop(s) }} style={{ ...smallBtnStyle, color: 'var(--hira-alarm-critical)' }}>■ Detener</button>
                  }
                  <button onClick={e => { e.stopPropagation(); openEdit(s) }} style={smallBtnStyle} disabled={s.status === 'running'}>✎ Editar</button>
                  <button onClick={e => { e.stopPropagation(); remove(s) }} style={{ ...smallBtnStyle, color: 'var(--hira-alarm-critical)' }} disabled={s.status === 'running'}>🗑</button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Panel derecho — editor o logs */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 16, minWidth: 0 }}>

        {showEditor ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12, flex: 1 }}>
            <h4 style={{ margin: 0 }}>{editId ? 'Editar script' : 'Nuevo script'}</h4>

            <div style={{ display: 'flex', gap: 12 }}>
              <div style={{ flex: 1 }}>
                <label style={labelStyle}>Nombre *</label>
                <input style={inputStyle} value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} />
              </div>
              <div style={{ width: 120 }}>
                <label style={labelStyle}>Intervalo (s)</label>
                <input style={inputStyle} type="number" min={1} value={form.interval_seconds} onChange={e => setForm(f => ({ ...f, interval_seconds: parseInt(e.target.value) || 10 }))} />
              </div>
            </div>

            <div>
              <label style={labelStyle}>Descripción</label>
              <input style={inputStyle} value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} />
            </div>

            <div style={{ flex: 1, minHeight: 300, borderRadius: 8, overflow: 'hidden', border: '1px solid var(--md-sys-color-outline, #444)' }}>
              <Editor
                height="100%"
                language="python"
                theme="vs-dark"
                value={form.code}
                onChange={v => setForm(f => ({ ...f, code: v ?? '' }))}
                options={{
                  fontSize: 14,
                  minimap: { enabled: false },
                  scrollBeyondLastLine: false,
                  wordWrap: 'on',
                }}
              />
            </div>

            {error && <p style={{ color: 'var(--hira-alarm-critical)', margin: 0, fontSize: 13 }}>{error}</p>}

            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
              <button onClick={() => setShowEditor(false)} style={smallBtnStyle}>Cancelar</button>
              <button onClick={() => save(false)} disabled={saving || !form.name.trim()} style={smallBtnStyle}>
                {saving ? 'Guardando...' : 'Guardar'}
              </button>
              <button onClick={() => save(true)} disabled={saving || !form.name.trim()} style={btnStyle}>
                {saving ? 'Guardando...' : 'Guardar e Iniciar'}
              </button>
            </div>
          </div>
        ) : selected ? (
          <>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <h4 style={{ margin: 0 }}>{selected.name}</h4>
                {selected.description && (
                  <p style={{ margin: '4px 0 0', fontSize: 13, color: 'var(--md-sys-color-on-surface-variant)' }}>{selected.description}</p>
                )}
              </div>
              <span style={{ fontSize: 12, color: statusColor(selected.status), fontWeight: 700 }}>
                ● {selected.status.toUpperCase()}
              </span>
            </div>

            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 8 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h5 style={{ margin: 0, fontSize: 13, color: 'var(--md-sys-color-on-surface-variant)' }}>
                  LOG DE EJECUCIÓN {selected.status === 'running' && '(actualizando cada 5s)'}
                </h5>
                <button onClick={() => loadLogs(selected.id)} style={smallBtnStyle}>↻ Actualizar</button>
              </div>

              <div
                ref={logsRef}
                style={{
                  flex: 1,
                  overflowY: 'auto',
                  background: '#0d0d1a',
                  borderRadius: 8,
                  padding: 12,
                  fontFamily: 'monospace',
                  fontSize: 12,
                  lineHeight: 1.6,
                  maxHeight: 'calc(100vh - 280px)',
                }}
              >
                {logs.length === 0 && (
                  <span style={{ color: '#555' }}>Sin ejecuciones registradas aún.</span>
                )}
                {logs.map((e, i) => (
                  <div key={e.id} style={{ marginBottom: 8, borderBottom: '1px solid #1a1a2e', paddingBottom: 8 }}>
                    <div style={{ color: e.status === 'error' ? 'var(--hira-alarm-critical)' : 'var(--hira-status-ok)', marginBottom: 2 }}>
                      [{new Date(e.started_at).toLocaleTimeString()}] ciclo {logs.length - i} — {e.status}
                    </div>
                    {e.output && (
                      <pre style={{ margin: 0, color: '#c8d3f5', whiteSpace: 'pre-wrap' }}>{e.output}</pre>
                    )}
                    {e.error_message && (
                      <pre style={{ margin: 0, color: 'var(--hira-alarm-critical)', whiteSpace: 'pre-wrap' }}>{e.error_message}</pre>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </>
        ) : (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', flex: 1, color: 'var(--md-sys-color-on-surface-variant)' }}>
            Selecciona un script o crea uno nuevo
          </div>
        )}
      </div>
    </div>
  )
}

const btnStyle: React.CSSProperties = { background: 'var(--md-sys-color-primary, #00b4d8)', color: 'var(--md-sys-color-on-primary, #fff)', border: 'none', borderRadius: 8, padding: '8px 16px', cursor: 'pointer', fontWeight: 600 }
const smallBtnStyle: React.CSSProperties = { background: 'transparent', border: '1px solid var(--md-sys-color-outline, #444)', borderRadius: 6, padding: '4px 10px', cursor: 'pointer', color: 'var(--md-sys-color-on-surface, #e0e0e0)', fontSize: 13 }
const labelStyle: React.CSSProperties = { display: 'block', fontSize: 13, marginBottom: 4, color: 'var(--md-sys-color-on-surface-variant, #aaa)' }
const inputStyle: React.CSSProperties = { display: 'block', width: '100%', padding: '8px 10px', background: 'var(--md-sys-color-surface-variant, #2a2a3a)', border: '1px solid var(--md-sys-color-outline, #444)', borderRadius: 6, color: 'var(--md-sys-color-on-surface, #e0e0e0)', fontSize: 14, boxSizing: 'border-box' }
