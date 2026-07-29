import { useEffect, useRef, useState } from 'react'
import Editor from '@monaco-editor/react'
import { api } from '../services/api'

interface TestScript {
  id: number
  name: string
  description: string | null
  code: string
  created_at: string
  updated_at: string
}

interface TestExecution {
  id: number
  script_id: number
  started_at: string
  ended_at: string | null
  status: 'running' | 'success' | 'failure' | 'error'
  output: string | null
  error_message: string | null
  passed: number | null
  failed: number | null
}

interface TestLog {
  id: number
  level: 'info' | 'pass' | 'fail' | 'error'
  message: string
  created_at: string
}

interface TestExecutionDetail extends TestExecution {
  logs: TestLog[]
}

const DEFAULT_CODE = `# API disponible en el objeto hira:
# hira.read("nombre_punto")           → float | None
# hira.write("nombre_punto", valor)   → bool  (bloquea el punto 5 min)
# hira.assert_equal("nombre", valor)  → bool
# hira.assert_between("nombre", min, max) → bool
# hira.info("mensaje")

# Ejemplo:
hira.write("setpoint_supply", 22.0)
hira.assert_equal("setpoint_supply", 22.0)
hira.assert_between("temp_supply", 18.0, 26.0)
`

const LOG_LEVEL_COLORS: Record<string, string> = {
  pass: 'var(--hira-status-ok)',
  fail: 'var(--hira-alarm-high)',
  error: 'var(--hira-alarm-critical)',
  info: 'var(--text-secondary)',
}

const STATUS_COLORS: Record<string, string> = {
  running: 'var(--accent)',
  success: 'var(--hira-status-ok)',
  failure: 'var(--hira-alarm-high)',
  error: 'var(--hira-alarm-critical)',
}

function fmtDuration(start: string, end: string | null): string {
  if (!end) return '…'
  const ms = new Date(end).getTime() - new Date(start).getTime()
  return ms < 1000 ? `${ms}ms` : `${(ms / 1000).toFixed(1)}s`
}

export default function TestsPage() {
  const [scripts, setScripts] = useState<TestScript[]>([])
  const [selected, setSelected] = useState<TestScript | null>(null)
  const [code, setCode] = useState(DEFAULT_CODE)
  const [editName, setEditName] = useState('')
  const [editDesc, setEditDesc] = useState('')
  const [isNewScript, setIsNewScript] = useState(false)
  const [saving, setSaving] = useState(false)
  const [running, setRunning] = useState(false)
  const [executions, setExecutions] = useState<TestExecution[]>([])
  const [selectedExec, setSelectedExec] = useState<TestExecutionDetail | null>(null)
  const [loadingExecs, setLoadingExecs] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const loadScripts = async () => {
    try {
      const r = await api.get<TestScript[]>('/tests/scripts')
      setScripts(r.data)
    } catch {
      setError('Error al cargar scripts de prueba')
    }
  }

  useEffect(() => {
    loadScripts()
    return () => { if (pollRef.current) clearInterval(pollRef.current) }
  }, [])

  const selectScript = async (s: TestScript) => {
    setSelected(s)
    setCode(s.code)
    setEditName(s.name)
    setEditDesc(s.description ?? '')
    setIsNewScript(false)
    setSelectedExec(null)
    setError(null)
    setLoadingExecs(true)
    try {
      const r = await api.get<TestExecution[]>(`/tests/scripts/${s.id}/executions`)
      setExecutions(r.data)
    } finally {
      setLoadingExecs(false)
    }
  }

  const startNew = () => {
    setSelected(null)
    setCode(DEFAULT_CODE)
    setEditName('')
    setEditDesc('')
    setIsNewScript(true)
    setExecutions([])
    setSelectedExec(null)
    setError(null)
  }

  const saveScript = async () => {
    if (!editName.trim()) { setError('El nombre es requerido'); return }
    setSaving(true)
    setError(null)
    try {
      if (isNewScript) {
        const r = await api.post<TestScript>('/tests/scripts', { name: editName, description: editDesc || null, code })
        setScripts(prev => [...prev, r.data])
        setSelected(r.data)
        setIsNewScript(false)
      } else if (selected) {
        const r = await api.put<TestScript>(`/tests/scripts/${selected.id}`, { name: editName, description: editDesc || null, code })
        setScripts(prev => prev.map(s => s.id === r.data.id ? r.data : s))
        setSelected(r.data)
      }
    } catch (e: unknown) {
      setError('Error al guardar el script')
    } finally {
      setSaving(false)
    }
  }

  const deleteScript = async () => {
    if (!selected) return
    if (!confirm(`¿Eliminar el script "${selected.name}"?`)) return
    try {
      await api.delete(`/tests/scripts/${selected.id}`)
      setScripts(prev => prev.filter(s => s.id !== selected.id))
      setSelected(null)
      setIsNewScript(false)
      setExecutions([])
      setSelectedExec(null)
    } catch {
      setError('Error al eliminar el script')
    }
  }

  const runScript = async () => {
    if (!selected) return
    setRunning(true)
    setError(null)
    try {
      await saveScript()
      const r = await api.post<{ execution_id: number; status: string }>(`/tests/scripts/${selected.id}/run`)
      const execId = r.data.execution_id
      // Optimistically add running execution
      const runningExec: TestExecution = {
        id: execId, script_id: selected.id,
        started_at: new Date().toISOString(), ended_at: null,
        status: 'running', output: null, error_message: null, passed: null, failed: null,
      }
      setExecutions(prev => [runningExec, ...prev])

      // Poll until done
      if (pollRef.current) clearInterval(pollRef.current)
      pollRef.current = setInterval(async () => {
        try {
          const detail = await api.get<TestExecutionDetail>(`/tests/executions/${execId}`)
          setExecutions(prev => prev.map(e => e.id === execId ? detail.data : e))
          if (detail.data.status !== 'running') {
            clearInterval(pollRef.current!)
            pollRef.current = null
            setSelectedExec(detail.data)
            setRunning(false)
          }
        } catch { /* ignore poll errors */ }
      }, 2000)
    } catch (e: unknown) {
      setError('Error al ejecutar el script')
      setRunning(false)
    }
  }

  const selectExecution = async (exec: TestExecution) => {
    try {
      const r = await api.get<TestExecutionDetail>(`/tests/executions/${exec.id}`)
      setSelectedExec(r.data)
    } catch {
      setError('Error al cargar los detalles de la ejecución')
    }
  }

  const theme = document.documentElement.getAttribute('data-theme') === 'dark' ? 'vs-dark' : 'vs'

  return (
    <div style={{ display: 'flex', height: 'calc(100vh - 48px)', gap: 0, overflow: 'hidden' }}>
      {/* Left panel — script list */}
      <div style={{
        width: 220,
        minWidth: 220,
        borderRight: '1px solid var(--border-subtle)',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
      }}>
        <div style={{ padding: '12px 12px 8px', borderBottom: '1px solid var(--border-subtle)', display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ flex: 1, fontSize: 'var(--text-sm)', fontWeight: 700, color: 'var(--text-primary)' }}>Scripts</span>
          <button
            onClick={startNew}
            style={{
              background: 'var(--accent)',
              color: '#fff',
              border: 'none',
              borderRadius: 'var(--radius-sm)',
              padding: '3px 8px',
              fontSize: 12,
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >+ Nuevo</button>
        </div>
        <div style={{ flex: 1, overflowY: 'auto' }}>
          {scripts.map(s => (
            <div
              key={s.id}
              onClick={() => selectScript(s)}
              style={{
                padding: '9px 12px',
                cursor: 'pointer',
                background: selected?.id === s.id ? 'var(--accent-subtle)' : 'transparent',
                borderLeft: selected?.id === s.id ? '3px solid var(--accent)' : '3px solid transparent',
                fontSize: 'var(--text-sm)',
                color: selected?.id === s.id ? 'var(--accent)' : 'var(--text-primary)',
                borderBottom: '1px solid var(--border-subtle)',
              }}
            >
              <div style={{ fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{s.name}</div>
              {s.description && (
                <div style={{ fontSize: 11, color: 'var(--text-muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{s.description}</div>
              )}
            </div>
          ))}
          {scripts.length === 0 && (
            <div style={{ padding: 16, fontSize: 'var(--text-xs)', color: 'var(--text-muted)', textAlign: 'center' }}>
              Sin scripts. Crea uno.
            </div>
          )}
        </div>
      </div>

      {/* Center panel — editor + controls */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        {(selected || isNewScript) ? (
          <>
            {/* Header */}
            <div style={{ padding: '10px 16px', borderBottom: '1px solid var(--border-subtle)', display: 'flex', alignItems: 'center', gap: 10, flexShrink: 0 }}>
              <input
                value={editName}
                onChange={e => setEditName(e.target.value)}
                placeholder="Nombre del script"
                style={{
                  flex: 1,
                  background: 'var(--bg-surface)',
                  border: '1px solid var(--border-default)',
                  borderRadius: 'var(--radius-md)',
                  color: 'var(--text-primary)',
                  padding: '5px 10px',
                  fontSize: 'var(--text-sm)',
                  fontWeight: 600,
                }}
              />
              <input
                value={editDesc}
                onChange={e => setEditDesc(e.target.value)}
                placeholder="Descripción (opcional)"
                style={{
                  flex: 1,
                  background: 'var(--bg-surface)',
                  border: '1px solid var(--border-default)',
                  borderRadius: 'var(--radius-md)',
                  color: 'var(--text-secondary)',
                  padding: '5px 10px',
                  fontSize: 'var(--text-sm)',
                }}
              />
              <button
                onClick={saveScript}
                disabled={saving}
                style={{ ...btnBase, background: 'var(--bg-hover)', color: 'var(--text-primary)', border: '1px solid var(--border-default)', opacity: saving ? 0.7 : 1 }}
              >{saving ? 'Guardando…' : 'Guardar'}</button>
              {selected && !isNewScript && (
                <>
                  <button
                    onClick={runScript}
                    disabled={running}
                    style={{ ...btnBase, background: 'var(--accent)', color: '#fff', opacity: running ? 0.7 : 1 }}
                  >{running ? 'Ejecutando…' : '▶ Ejecutar'}</button>
                  <button
                    onClick={deleteScript}
                    style={{ ...btnBase, background: 'transparent', color: 'var(--danger)', border: '1px solid var(--danger)' }}
                  >Eliminar</button>
                </>
              )}
            </div>

            {error && (
              <div style={{ padding: '6px 16px', fontSize: 'var(--text-xs)', color: 'var(--danger)', background: 'var(--danger-subtle)', flexShrink: 0 }}>
                {error}
              </div>
            )}

            {/* Monaco Editor */}
            <div style={{ flex: 1, overflow: 'hidden' }}>
              <Editor
                height="100%"
                language="python"
                theme={theme}
                value={code}
                onChange={v => setCode(v ?? '')}
                options={{
                  fontSize: 13,
                  minimap: { enabled: false },
                  lineNumbers: 'on',
                  scrollBeyondLastLine: false,
                  automaticLayout: true,
                }}
              />
            </div>
          </>
        ) : (
          <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: 'var(--text-sm)' }}>
            Selecciona un script o crea uno nuevo
          </div>
        )}
      </div>

      {/* Right panel — executions + logs */}
      {selected && !isNewScript && (
        <div style={{
          width: 320,
          minWidth: 320,
          borderLeft: '1px solid var(--border-subtle)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        }}>
          {/* Execution history */}
          <div style={{ borderBottom: '1px solid var(--border-subtle)', padding: '10px 12px 6px' }}>
            <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>Historial</div>
          </div>
          <div style={{ flex: selectedExec ? '0 0 auto' : 1, maxHeight: selectedExec ? '40%' : '100%', overflowY: 'auto' }}>
            {loadingExecs ? (
              <div style={{ padding: 12, fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>Cargando…</div>
            ) : executions.length === 0 ? (
              <div style={{ padding: 12, fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>Sin ejecuciones aún</div>
            ) : executions.map(exec => (
              <div
                key={exec.id}
                onClick={() => selectExecution(exec)}
                style={{
                  padding: '8px 12px',
                  cursor: 'pointer',
                  background: selectedExec?.id === exec.id ? 'var(--accent-subtle)' : 'transparent',
                  borderBottom: '1px solid var(--border-subtle)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                }}
              >
                <span style={{
                  width: 8, height: 8, borderRadius: '50%', flexShrink: 0,
                  background: STATUS_COLORS[exec.status] ?? 'var(--text-muted)',
                }} />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 11, color: 'var(--text-primary)', fontWeight: 500 }}>
                    {new Date(exec.started_at).toLocaleTimeString()}
                  </div>
                  <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>
                    {fmtDuration(exec.started_at, exec.ended_at)}
                    {exec.passed != null && exec.failed != null && (
                      <span> · <span style={{ color: 'var(--hira-status-ok)' }}>{exec.passed}✓</span> <span style={{ color: exec.failed > 0 ? 'var(--hira-alarm-high)' : 'var(--text-muted)' }}>{exec.failed}✗</span></span>
                    )}
                  </div>
                </div>
                <span style={{ fontSize: 10, color: STATUS_COLORS[exec.status] ?? 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>
                  {exec.status}
                </span>
              </div>
            ))}
          </div>

          {/* Logs of selected execution */}
          {selectedExec && (
            <>
              <div style={{ padding: '8px 12px 4px', borderTop: '1px solid var(--border-subtle)', borderBottom: '1px solid var(--border-subtle)', flexShrink: 0 }}>
                <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                  Logs — #{selectedExec.id}
                </div>
              </div>
              <div style={{ flex: 1, overflowY: 'auto', padding: '4px 0', fontFamily: 'var(--font-mono)', fontSize: 11 }}>
                {selectedExec.logs.length === 0 ? (
                  <div style={{ padding: '8px 12px', color: 'var(--text-muted)' }}>Sin logs</div>
                ) : selectedExec.logs.map(log => (
                  <div key={log.id} style={{ padding: '2px 12px', color: LOG_LEVEL_COLORS[log.level] ?? 'var(--text-secondary)', lineHeight: 1.4 }}>
                    <span style={{ opacity: 0.5, marginRight: 8 }}>{log.level.toUpperCase()}</span>
                    {log.message}
                  </div>
                ))}
                {selectedExec.output && selectedExec.logs.length === 0 && (
                  <pre style={{ margin: 0, padding: '4px 12px', color: 'var(--text-secondary)', whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                    {selectedExec.output}
                  </pre>
                )}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  )
}

const btnBase: React.CSSProperties = {
  padding: '5px 12px',
  borderRadius: 'var(--radius-md)',
  border: 'none',
  fontSize: 'var(--text-sm)',
  fontWeight: 600,
  cursor: 'pointer',
}
