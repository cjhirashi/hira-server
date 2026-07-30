import { useCallback, useEffect, useState } from 'react'
import { api } from '../services/api'

// ── Types ─────────────────────────────────────────────────────────────────────

interface LogicScript { id: number; name: string; status: string; interval_seconds: number }
interface Device { id: number; name: string; protocol: string }
interface Area { id: number; name: string }
interface Point { id: number; area_id: number | null }
interface DocSummary { id: number; title: string; type: string }
interface RecentExecution {
  id: number; script_id: number; script_name: string
  started_at: string; ended_at: string | null; status: string
  passed: number | null; failed: number | null
}

// ── Card ──────────────────────────────────────────────────────────────────────

function SummaryCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{
      background: 'var(--bg-surface)',
      border: '1px solid var(--border-subtle)',
      borderRadius: 'var(--radius-lg)',
      padding: '16px 20px',
      flex: 1,
      minWidth: 0,
    }}>
      <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 12 }}>
        {title}
      </div>
      {children}
    </div>
  )
}

function Stat({ value, label, color }: { value: number | string; label: string; color?: string }) {
  return (
    <div style={{ display: 'flex', alignItems: 'baseline', gap: 6, marginBottom: 4 }}>
      <span style={{ fontSize: 'var(--text-xl)', fontWeight: 700, color: color ?? 'var(--text-primary)' }}>{value}</span>
      <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>{label}</span>
    </div>
  )
}

// ── Status badge ──────────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: string }) {
  const running = status === 'running'
  return (
    <span style={{
      fontSize: 10,
      padding: '2px 7px',
      borderRadius: 8,
      fontWeight: 600,
      background: running ? 'rgba(34,197,94,0.12)' : 'var(--bg-hover)',
      color: running ? 'var(--hira-status-ok)' : 'var(--text-muted)',
      border: `1px solid ${running ? 'var(--hira-status-ok)' : 'var(--border-default)'}`,
    }}>
      {running ? '● running' : '○ stopped'}
    </span>
  )
}

function ExecBadge({ status, passed, failed }: { status: string; passed: number | null; failed: number | null }) {
  const done = status === 'completed'
  const err = status === 'failed' || (failed !== null && failed > 0)
  const color = !done ? 'var(--text-muted)' : err ? 'var(--hira-alarm-high)' : 'var(--hira-status-ok)'
  const label = !done ? status : err ? `✗ ${failed ?? 0} errores` : `✓ ${passed ?? 0} ok`
  return (
    <span style={{ fontSize: 10, fontWeight: 600, color }}>{label}</span>
  )
}

// ── Section panel ─────────────────────────────────────────────────────────────

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{
      background: 'var(--bg-surface)',
      border: '1px solid var(--border-subtle)',
      borderRadius: 'var(--radius-lg)',
      padding: '16px 20px',
      flex: 1,
      minWidth: 0,
    }}>
      <div style={{ fontSize: 'var(--text-sm)', fontWeight: 700, color: 'var(--text-primary)', marginBottom: 12, borderBottom: '1px solid var(--border-subtle)', paddingBottom: 8 }}>
        {title}
      </div>
      {children}
    </div>
  )
}

// ── Main ──────────────────────────────────────────────────────────────────────

export default function StudioDashboard() {
  const [scripts, setScripts] = useState<LogicScript[]>([])
  const [devices, setDevices] = useState<Device[]>([])
  const [areas, setAreas] = useState<Area[]>([])
  const [points, setPoints] = useState<Point[]>([])
  const [docs, setDocs] = useState<DocSummary[]>([])
  const [docsIndexed, setDocsIndexed] = useState(0)
  const [recentExecs, setRecentExecs] = useState<RecentExecution[]>([])
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null)
  const [loading, setLoading] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [logicRes, devRes, areaRes, pointRes, docRes, docStatsRes, execRes] = await Promise.allSettled([
        api.get<LogicScript[]>('/logic'),
        api.get<Device[]>('/devices'),
        api.get<Area[]>('/areas'),
        api.get<Point[]>('/points'),
        api.get<DocSummary[]>('/docs'),
        api.get<{ total: number; indexed: number }>('/docs/stats'),
        api.get<RecentExecution[]>('/tests/executions/recent?limit=5'),
      ])

      if (logicRes.status === 'fulfilled') setScripts(logicRes.value.data)
      if (devRes.status === 'fulfilled') setDevices(devRes.value.data)
      if (areaRes.status === 'fulfilled') setAreas(areaRes.value.data)
      if (pointRes.status === 'fulfilled') setPoints(pointRes.value.data)
      if (docRes.status === 'fulfilled') setDocs(docRes.value.data)
      if (docStatsRes.status === 'fulfilled') setDocsIndexed(docStatsRes.value.data.indexed)
      if (execRes.status === 'fulfilled') setRecentExecs(execRes.value.data)

      setLastUpdate(new Date())
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  // ── computed ──────────────────────────────────────────────────────────────
  const runningScripts = scripts.filter(s => s.status === 'running').length
  const stoppedScripts = scripts.length - runningScripts

  const devicesByProtocol = devices.reduce<Record<string, number>>((acc, d) => {
    acc[d.protocol] = (acc[d.protocol] ?? 0) + 1
    return acc
  }, {})

  const pointsByArea = areas.map(a => ({
    name: a.name,
    count: points.filter(p => p.area_id === a.id).length,
  })).sort((a, b) => b.count - a.count)

  const sinArea = points.filter(p => p.area_id === null).length

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <h2 style={{ margin: 0, fontSize: 'var(--text-xl)', fontWeight: 700, color: 'var(--text-primary)', flex: 1 }}>
          Panel de Ingeniería
        </h2>
        {lastUpdate && (
          <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>
            Actualizado: {lastUpdate.toLocaleTimeString()}
          </span>
        )}
        <button
          onClick={load}
          disabled={loading}
          style={{
            padding: '6px 12px',
            borderRadius: 'var(--radius-md)',
            border: '1px solid var(--border-default)',
            background: 'var(--bg-hover)',
            color: 'var(--text-primary)',
            fontSize: 'var(--text-sm)',
            fontWeight: 600,
            cursor: loading ? 'default' : 'pointer',
          }}
        >
          {loading ? '…' : '⟳ Actualizar'}
        </button>
      </div>

      {/* Summary cards row */}
      <div style={{ display: 'flex', gap: 16 }}>
        <SummaryCard title="Scripts de Lógica">
          <Stat value={runningScripts} label="activos" color="var(--hira-status-ok)" />
          <Stat value={stoppedScripts} label="detenidos" color="var(--text-muted)" />
        </SummaryCard>

        <SummaryCard title="Dispositivos Configurados">
          <Stat value={devices.length} label="total" />
          {Object.entries(devicesByProtocol).map(([proto, n]) => (
            <div key={proto} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 'var(--text-xs)', color: 'var(--text-secondary)', marginBottom: 2 }}>
              <span>{proto}</span>
              <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{n}</span>
            </div>
          ))}
          {devices.length === 0 && <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>Sin dispositivos</span>}
        </SummaryCard>

        <SummaryCard title="Documentación">
          <Stat value={docs.length} label="documentos" />
          <Stat value={docsIndexed} label="indexados RAG" color={docsIndexed > 0 ? 'var(--hira-status-ok)' : 'var(--text-muted)'} />
        </SummaryCard>
      </div>

      {/* Middle panels */}
      <div style={{ display: 'flex', gap: 16 }}>
        <Panel title="Scripts de Lógica">
          {scripts.length === 0 ? (
            <div style={{ fontSize: 'var(--text-sm)', color: 'var(--text-muted)' }}>Sin scripts configurados</div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {scripts.map(s => (
                <div key={s.id} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '6px 8px', borderRadius: 'var(--radius-sm)', background: 'var(--bg-hover)' }}>
                  <span style={{ flex: 1, fontSize: 'var(--text-sm)', color: 'var(--text-primary)', fontWeight: 500 }}>{s.name}</span>
                  <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>{s.interval_seconds}s</span>
                  <StatusBadge status={s.status} />
                </div>
              ))}
            </div>
          )}
        </Panel>

        <Panel title="Últimas Pruebas">
          {recentExecs.length === 0 ? (
            <div style={{ fontSize: 'var(--text-sm)', color: 'var(--text-muted)' }}>Sin ejecuciones recientes</div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {recentExecs.map(e => (
                <div key={e.id} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '6px 8px', borderRadius: 'var(--radius-sm)', background: 'var(--bg-hover)' }}>
                  <span style={{ flex: 1, fontSize: 'var(--text-sm)', color: 'var(--text-primary)', fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {e.script_name}
                  </span>
                  <ExecBadge status={e.status} passed={e.passed} failed={e.failed} />
                  <span style={{ fontSize: 10, color: 'var(--text-muted)', flexShrink: 0 }}>
                    {new Date(e.started_at).toLocaleString()}
                  </span>
                </div>
              ))}
            </div>
          )}
        </Panel>
      </div>

      {/* Points by area */}
      <Panel title="Puntos por Área">
        {pointsByArea.length === 0 && sinArea === 0 ? (
          <div style={{ fontSize: 'var(--text-sm)', color: 'var(--text-muted)' }}>Sin puntos configurados</div>
        ) : (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {pointsByArea.map(a => (
              <div key={a.name} style={{
                display: 'flex', alignItems: 'center', gap: 8,
                background: 'var(--bg-hover)', borderRadius: 'var(--radius-md)',
                padding: '6px 12px', border: '1px solid var(--border-subtle)',
              }}>
                <span style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)' }}>{a.name}</span>
                <span style={{ fontSize: 'var(--text-sm)', fontWeight: 700, color: 'var(--accent)' }}>{a.count}</span>
                <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>puntos</span>
              </div>
            ))}
            {sinArea > 0 && (
              <div style={{
                display: 'flex', alignItems: 'center', gap: 8,
                background: 'var(--bg-hover)', borderRadius: 'var(--radius-md)',
                padding: '6px 12px', border: '1px solid var(--border-subtle)',
              }}>
                <span style={{ fontSize: 'var(--text-sm)', color: 'var(--text-muted)' }}>Sin área</span>
                <span style={{ fontSize: 'var(--text-sm)', fontWeight: 700, color: 'var(--text-muted)' }}>{sinArea}</span>
              </div>
            )}
          </div>
        )}
      </Panel>
    </div>
  )
}
