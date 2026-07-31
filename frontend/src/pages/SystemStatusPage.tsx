import { useEffect, useState, useCallback, useRef } from 'react'

const API = '/api/v1'

function authHeaders() {
  return { Authorization: `Bearer ${localStorage.getItem('hira-token') ?? ''}` }
}

interface AIUsageLogEntry {
  id: number
  timestamp: string
  agent_type: string
  model: string
  tokens_input: number
  tokens_output: number
  latency_ms: number
  tool_calls_count: number
  query_preview: string | null
}

interface AIUsageTotals {
  requests: number
  tokens: number
  estimated_cost_usd: number
}

interface AIUsageData {
  logs: AIUsageLogEntry[]
  totals: AIUsageTotals
}

interface BackupEntry {
  id: number
  filename: string
  size_bytes: number | null
  status: 'success' | 'failed'
  error_message: string | null
  created_at: string
}

function formatBytes(bytes: number | null): string {
  if (bytes == null) return '—'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

interface ComponentStatus {
  status: string
  latency_ms?: number | null
  size_mb?: number | null
  point_history_rows?: number | null
  memory_used_mb?: number | null
  workers?: { name: string; queues: string[]; active_tasks: number }[]
  total_gb?: number | null
  used_gb?: number | null
  free_gb?: number | null
  percent_used?: number | null
  total?: number
  online?: number
  offline?: number
  offline_names?: string[]
}

interface HealthData {
  status: string
  timestamp: string
  components: {
    database: ComponentStatus
    redis: ComponentStatus
    celery: ComponentStatus
    disk: ComponentStatus
    devices: ComponentStatus
  }
}

interface SystemEvent {
  id: number
  event_type: string
  severity: string
  message: string
  notified: boolean
  created_at: string
}

function statusColor(s: string): string {
  if (s === 'ok' || s === 'healthy') return 'var(--success)'
  if (s === 'warning' || s === 'degraded') return 'var(--warning)'
  if (s === 'critical' || s === 'error') return 'var(--danger)'
  if (s === 'not_applicable') return 'var(--text-muted)'
  return 'var(--text-muted)'
}

function StatusDot({ status }: { status: string }) {
  return (
    <span style={{
      display: 'inline-block',
      width: 8,
      height: 8,
      borderRadius: '50%',
      background: statusColor(status),
      flexShrink: 0,
    }} />
  )
}

function ComponentCard({ title, status, children }: { title: string; status: string; children: React.ReactNode }) {
  return (
    <div style={{
      background: 'var(--bg-surface)',
      border: `1px solid var(--border-default)`,
      borderTop: `2px solid ${statusColor(status)}`,
      borderRadius: 'var(--radius-lg)',
      padding: '14px 16px',
      display: 'flex',
      flexDirection: 'column',
      gap: 6,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
        <StatusDot status={status} />
        <span style={{ fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--text-primary)' }}>{title}</span>
        <span style={{ fontSize: 'var(--text-xs)', color: statusColor(status), marginLeft: 'auto', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          {status === 'not_applicable' ? 'N/A' : status}
        </span>
      </div>
      {children}
    </div>
  )
}

function MetaLine({ label, value }: { label: string; value: string | number | null | undefined }) {
  if (value == null) return null
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 'var(--text-xs)', color: 'var(--text-secondary)' }}>
      <span>{label}</span>
      <span style={{ color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>{value}</span>
    </div>
  )
}

function severityColor(s: string) {
  if (s === 'critical') return 'var(--danger)'
  if (s === 'warning') return 'var(--warning)'
  return 'var(--info)'
}

export default function SystemStatusPage() {
  const [health, setHealth] = useState<HealthData | null>(null)
  const [events, setEvents] = useState<SystemEvent[]>([])
  const [aiUsage, setAiUsage] = useState<AIUsageData | null>(null)
  const [backups, setBackups] = useState<BackupEntry[]>([])
  const [backupRunning, setBackupRunning] = useState(false)
  const [backupToast, setBackupToast] = useState<string | null>(null)
  const [lastUpdate, setLastUpdate] = useState<string>('')
  const [loading, setLoading] = useState(true)
  const toastTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  const fetchBackups = useCallback(async () => {
    try {
      const res = await fetch(`${API}/backups/`, { headers: authHeaders() })
      if (res.ok) setBackups(await res.json())
    } catch { /* silencioso */ }
  }, [])

  const fetchData = useCallback(async () => {
    try {
      const [hRes, eRes, aiRes] = await Promise.all([
        fetch(`${API}/system/health/detailed`, { headers: authHeaders() }),
        fetch(`${API}/notifications/events?limit=10`, { headers: authHeaders() }),
        fetch(`${API}/ai-usage/?limit=10`, { headers: authHeaders() }),
      ])
      if (hRes.ok) {
        const data = await hRes.json()
        setHealth(data)
        setLastUpdate(new Date().toLocaleTimeString())
      }
      if (eRes.ok) setEvents(await eRes.json())
      if (aiRes.ok) setAiUsage(await aiRes.json())
    } catch {
      // silencioso
    } finally {
      setLoading(false)
    }
  }, [])

  const handleRunBackup = async () => {
    if (backupRunning) return
    setBackupRunning(true)
    try {
      const res = await fetch(`${API}/backups/run`, {
        method: 'POST',
        headers: authHeaders(),
      })
      if (res.ok) {
        setBackupToast('Backup iniciado. El historial se actualizará en unos segundos.')
        if (toastTimer.current) clearTimeout(toastTimer.current)
        toastTimer.current = setTimeout(async () => {
          await fetchBackups()
          setBackupToast(null)
        }, 5000)
      }
    } catch { /* silencioso */ }
    finally { setBackupRunning(false) }
  }

  const handleDownloadBackup = (backup: BackupEntry) => {
    const a = document.createElement('a')
    a.href = `${API}/backups/${backup.id}/download`
    a.download = backup.filename
    const token = localStorage.getItem('hira-token') ?? ''
    // Descarga con token via fetch + blob
    fetch(a.href, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => r.blob())
      .then(blob => {
        const url = URL.createObjectURL(blob)
        a.href = url
        a.click()
        URL.revokeObjectURL(url)
      })
  }

  useEffect(() => {
    fetchData()
    fetchBackups()
    const interval = setInterval(fetchData, 30_000)
    return () => clearInterval(interval)
  }, [fetchData, fetchBackups])

  if (loading) {
    return <div style={{ color: 'var(--text-secondary)', padding: 24 }}>Cargando estado del sistema…</div>
  }

  const c = health?.components

  return (
    <div style={{ maxWidth: 960, display: 'flex', flexDirection: 'column', gap: 24 }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <h2 style={{ margin: 0, color: 'var(--text-primary)', fontSize: 'var(--text-xl)', fontWeight: 700 }}>
          Estado del Sistema
        </h2>
        {health && (
          <span style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 6,
            background: health.status === 'healthy' ? 'var(--success-subtle)' : health.status === 'degraded' ? 'var(--warning-subtle)' : 'var(--danger-subtle)',
            color: statusColor(health.status),
            borderRadius: 10,
            padding: '3px 10px',
            fontSize: 'var(--text-xs)',
            fontWeight: 600,
            textTransform: 'uppercase',
          }}>
            <StatusDot status={health.status} />
            {health.status}
          </span>
        )}
        {lastUpdate && (
          <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', marginLeft: 'auto' }}>
            Última actualización: {lastUpdate}
          </span>
        )}
      </div>

      {/* Component Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 12 }}>
        <ComponentCard title="Base de Datos" status={c?.database?.status ?? 'error'}>
          <MetaLine label="Latencia" value={c?.database?.latency_ms != null ? `${c.database.latency_ms} ms` : null} />
          <MetaLine label="Tamaño" value={c?.database?.size_mb != null ? `${c.database.size_mb} MB` : null} />
          <MetaLine label="Históricos" value={c?.database?.point_history_rows?.toLocaleString() ?? null} />
        </ComponentCard>

        <ComponentCard title="Redis" status={c?.redis?.status ?? 'error'}>
          <MetaLine label="Latencia" value={c?.redis?.latency_ms != null ? `${c.redis.latency_ms} ms` : null} />
          <MetaLine label="Memoria" value={c?.redis?.memory_used_mb != null ? `${c.redis.memory_used_mb} MB` : null} />
        </ComponentCard>

        <ComponentCard title="Workers Celery" status={c?.celery?.status ?? 'error'}>
          {c?.celery?.status === 'not_applicable' ? (
            <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>No aplica (modo Studio)</div>
          ) : (
            <>
              <MetaLine label="Activos" value={c?.celery?.workers?.length ?? 0} />
              {c?.celery?.workers?.map(w => (
                <div key={w.name} style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                  {w.name.split('.').pop()}
                </div>
              ))}
            </>
          )}
        </ComponentCard>

        <ComponentCard title="Disco" status={c?.disk?.status ?? 'error'}>
          <MetaLine label="Usado" value={c?.disk?.percent_used != null ? `${c.disk.percent_used}%` : null} />
          <MetaLine label="Libre" value={c?.disk?.free_gb != null ? `${c.disk.free_gb} GB` : null} />
          <MetaLine label="Total" value={c?.disk?.total_gb != null ? `${c.disk.total_gb} GB` : null} />
        </ComponentCard>
      </div>

      {/* Devices */}
      <div>
        <h3 style={{ margin: '0 0 10px', fontSize: 'var(--text-base)', fontWeight: 600, color: 'var(--text-primary)' }}>
          Dispositivos ({c?.devices?.total ?? 0} total)
        </h3>
        <div style={{
          background: 'var(--bg-surface)',
          border: '1px solid var(--border-default)',
          borderRadius: 'var(--radius-lg)',
          overflow: 'hidden',
        }}>
          {!c?.devices?.total ? (
            <div style={{ padding: '14px 16px', fontSize: 'var(--text-sm)', color: 'var(--text-muted)' }}>
              Sin dispositivos configurados
            </div>
          ) : (
            <div>
              {/* Show offline devices */}
              {(c?.devices?.offline_names ?? []).map(name => (
                <div key={name} style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 10,
                  padding: '10px 16px',
                  borderBottom: '1px solid var(--border-subtle)',
                }}>
                  <span style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--danger)', flexShrink: 0 }} />
                  <span style={{ fontSize: 'var(--text-sm)', color: 'var(--text-primary)', flex: 1 }}>{name}</span>
                  <span style={{ fontSize: 'var(--text-xs)', color: 'var(--danger)', fontWeight: 600 }}>Offline</span>
                </div>
              ))}
              {/* Summary for online */}
              {(c?.devices?.online ?? 0) > 0 && (
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 10,
                  padding: '10px 16px',
                }}>
                  <span style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--success)', flexShrink: 0 }} />
                  <span style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)' }}>
                    {c?.devices?.online} dispositivo{(c?.devices?.online ?? 0) !== 1 ? 's' : ''} en línea
                  </span>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Recent Events */}
      <div>
        <h3 style={{ margin: '0 0 10px', fontSize: 'var(--text-base)', fontWeight: 600, color: 'var(--text-primary)' }}>
          Eventos Recientes
        </h3>
        <div style={{
          background: 'var(--bg-surface)',
          border: '1px solid var(--border-default)',
          borderRadius: 'var(--radius-lg)',
          overflow: 'hidden',
        }}>
          {events.length === 0 ? (
            <div style={{ padding: '14px 16px', fontSize: 'var(--text-sm)', color: 'var(--text-muted)' }}>
              Sin eventos recientes
            </div>
          ) : (
            events.map(ev => (
              <div key={ev.id} style={{
                display: 'flex',
                alignItems: 'flex-start',
                gap: 12,
                padding: '10px 16px',
                borderBottom: '1px solid var(--border-subtle)',
                borderLeft: `3px solid ${severityColor(ev.severity)}`,
              }}>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', marginBottom: 2 }}>
                    {ev.event_type}
                  </div>
                  <div style={{ fontSize: 'var(--text-sm)', color: 'var(--text-primary)' }}>{ev.message}</div>
                </div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', whiteSpace: 'nowrap', flexShrink: 0 }}>
                  {new Date(ev.created_at).toLocaleTimeString()}
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Backups */}
      <div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
          <h3 style={{ margin: 0, fontSize: 'var(--text-base)', fontWeight: 600, color: 'var(--text-primary)' }}>
            Backups de Base de Datos
          </h3>
          <button
            onClick={handleRunBackup}
            disabled={backupRunning}
            style={{
              padding: '6px 14px',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--border-default)',
              background: backupRunning ? 'var(--bg-elevated)' : 'var(--md-sys-color-primary)',
              color: backupRunning ? 'var(--text-muted)' : 'var(--md-sys-color-on-primary)',
              fontSize: 'var(--text-sm)',
              fontWeight: 600,
              cursor: backupRunning ? 'not-allowed' : 'pointer',
            }}
          >
            {backupRunning ? 'Iniciando…' : 'Ejecutar Backup Ahora'}
          </button>
        </div>

        {backupToast && (
          <div style={{
            marginBottom: 10,
            padding: '8px 14px',
            borderRadius: 'var(--radius-md)',
            background: 'var(--success-subtle)',
            color: 'var(--success)',
            fontSize: 'var(--text-sm)',
            fontWeight: 500,
          }}>
            {backupToast}
          </div>
        )}

        {backups.length > 0 && (
          <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)', marginBottom: 8 }}>
            Último backup exitoso:{' '}
            <strong style={{ color: 'var(--text-primary)' }}>
              {(() => {
                const last = backups.find(b => b.status === 'success')
                return last ? new Date(last.created_at).toLocaleString() : 'ninguno'
              })()}
            </strong>
          </div>
        )}

        <div style={{
          background: 'var(--bg-surface)',
          border: '1px solid var(--border-default)',
          borderRadius: 'var(--radius-lg)',
          overflow: 'hidden',
        }}>
          {backups.length === 0 ? (
            <div style={{ padding: '14px 16px', fontSize: 'var(--text-sm)', color: 'var(--text-muted)' }}>
              Sin backups registrados
            </div>
          ) : (
            <>
              <div style={{
                display: 'grid',
                gridTemplateColumns: '160px 1fr 80px 60px',
                gap: 8,
                padding: '8px 16px',
                borderBottom: '1px solid var(--border-default)',
                fontSize: 'var(--text-xs)',
                fontWeight: 600,
                color: 'var(--text-muted)',
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
              }}>
                <span>Fecha/Hora</span>
                <span>Archivo</span>
                <span>Tamaño</span>
                <span>Estado</span>
              </div>
              {backups.map(backup => (
                <div
                  key={backup.id}
                  onClick={() => backup.status === 'success' && handleDownloadBackup(backup)}
                  title={backup.status === 'failed' ? (backup.error_message ?? 'Error desconocido') : 'Click para descargar'}
                  style={{
                    display: 'grid',
                    gridTemplateColumns: '160px 1fr 80px 60px',
                    gap: 8,
                    padding: '8px 16px',
                    borderBottom: '1px solid var(--border-subtle)',
                    fontSize: 'var(--text-xs)',
                    color: 'var(--text-secondary)',
                    alignItems: 'center',
                    cursor: backup.status === 'success' ? 'pointer' : 'default',
                  }}
                >
                  <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                    {new Date(backup.created_at).toLocaleString()}
                  </span>
                  <span style={{
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                    color: backup.status === 'success' ? 'var(--md-sys-color-primary)' : 'var(--text-muted)',
                    fontFamily: 'var(--font-mono)',
                    fontSize: 11,
                  }}>
                    {backup.filename}
                  </span>
                  <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-primary)' }}>
                    {formatBytes(backup.size_bytes)}
                  </span>
                  <span style={{ fontSize: 16 }}>
                    {backup.status === 'success' ? '✅' : '❌'}
                  </span>
                </div>
              ))}
            </>
          )}
        </div>
      </div>

      {/* Observabilidad */}
      <div>
        <h3 style={{ margin: '0 0 10px', fontSize: 'var(--text-base)', fontWeight: 600, color: 'var(--text-primary)' }}>
          Observabilidad
        </h3>
        <div style={{
          background: 'var(--bg-surface)',
          border: '1px solid var(--border-default)',
          borderRadius: 'var(--radius-lg)',
          padding: '14px 16px',
          display: 'flex',
          gap: 12,
          flexWrap: 'wrap',
          marginBottom: 12,
        }}>
          <a
            href="http://localhost:3001"
            target="_blank"
            rel="noopener noreferrer"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 6,
              padding: '6px 14px',
              borderRadius: 'var(--radius-md)',
              background: 'var(--bg-elevated)',
              border: '1px solid var(--border-default)',
              color: 'var(--text-primary)',
              fontSize: 'var(--text-sm)',
              textDecoration: 'none',
              fontWeight: 500,
            }}
          >
            Abrir Grafana →
          </a>
          <a
            href="http://localhost:9090"
            target="_blank"
            rel="noopener noreferrer"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 6,
              padding: '6px 14px',
              borderRadius: 'var(--radius-md)',
              background: 'var(--bg-elevated)',
              border: '1px solid var(--border-default)',
              color: 'var(--text-primary)',
              fontSize: 'var(--text-sm)',
              textDecoration: 'none',
              fontWeight: 500,
            }}
          >
            Abrir Prometheus →
          </a>
        </div>

        {/* AI Usage */}
        <h3 style={{ margin: '0 0 10px', fontSize: 'var(--text-base)', fontWeight: 600, color: 'var(--text-primary)' }}>
          Uso del Agente IA
        </h3>
        {aiUsage && (
          <div style={{
            fontSize: 'var(--text-xs)',
            color: 'var(--text-secondary)',
            marginBottom: 10,
            display: 'flex',
            gap: 20,
            flexWrap: 'wrap',
          }}>
            <span>Total requests: <strong style={{ color: 'var(--text-primary)' }}>{aiUsage.totals.requests.toLocaleString()}</strong></span>
            <span>Tokens consumidos: <strong style={{ color: 'var(--text-primary)' }}>{aiUsage.totals.tokens.toLocaleString()}</strong></span>
            <span>Costo estimado: <strong style={{ color: 'var(--text-primary)' }}>${aiUsage.totals.estimated_cost_usd}</strong></span>
          </div>
        )}
        <div style={{
          background: 'var(--bg-surface)',
          border: '1px solid var(--border-default)',
          borderRadius: 'var(--radius-lg)',
          overflow: 'hidden',
        }}>
          {!aiUsage || aiUsage.logs.length === 0 ? (
            <div style={{ padding: '14px 16px', fontSize: 'var(--text-sm)', color: 'var(--text-muted)' }}>
              Sin invocaciones registradas
            </div>
          ) : (
            <>
              <div style={{
                display: 'grid',
                gridTemplateColumns: '140px 90px 80px 80px 60px 1fr',
                gap: 8,
                padding: '8px 16px',
                borderBottom: '1px solid var(--border-default)',
                fontSize: 'var(--text-xs)',
                fontWeight: 600,
                color: 'var(--text-muted)',
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
              }}>
                <span>Timestamp</span>
                <span>Agente</span>
                <span>Tokens</span>
                <span>Latencia</span>
                <span>Tools</span>
                <span>Query</span>
              </div>
              {aiUsage.logs.map(log => (
                <div key={log.id} style={{
                  display: 'grid',
                  gridTemplateColumns: '140px 90px 80px 80px 60px 1fr',
                  gap: 8,
                  padding: '8px 16px',
                  borderBottom: '1px solid var(--border-subtle)',
                  fontSize: 'var(--text-xs)',
                  color: 'var(--text-secondary)',
                  alignItems: 'center',
                }}>
                  <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                    {new Date(log.timestamp).toLocaleString()}
                  </span>
                  <span style={{
                    padding: '2px 6px',
                    borderRadius: 4,
                    background: log.agent_type === 'integrador' ? 'var(--info-subtle)' : 'var(--success-subtle)',
                    color: log.agent_type === 'integrador' ? 'var(--info)' : 'var(--success)',
                    fontWeight: 600,
                    textAlign: 'center',
                  }}>
                    {log.agent_type}
                  </span>
                  <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-primary)' }}>
                    {(log.tokens_input + log.tokens_output).toLocaleString()}
                  </span>
                  <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-primary)' }}>
                    {log.latency_ms.toLocaleString()} ms
                  </span>
                  <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-primary)' }}>
                    {log.tool_calls_count}
                  </span>
                  <span style={{
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                    color: 'var(--text-muted)',
                  }}>
                    {log.query_preview ?? '—'}
                  </span>
                </div>
              ))}
            </>
          )}
        </div>
      </div>
    </div>
  )
}
