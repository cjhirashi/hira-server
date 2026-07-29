import { useEffect, useState } from 'react'
import Plot from 'react-plotly.js'
import { api } from '../services/api'
import { useAuthStore } from '../store/authStore'

// ── Types ────────────────────────────────────────────────────────────────────

interface Point { id: number; name: string; unit: string }
interface TestScript { id: number; name: string }
interface Execution { id: number; started_at: string; ended_at: string | null; status: string; passed: number | null; failed: number | null }
interface ChartPoint { timestamp: string; point_name: string; value: number }
interface TrendRow { execution_id: number; started_at: string; status: string; duration_ms: number | null; result_summary: string | null }
interface CompareRow { execution_id: number; started_at: string; points: { t_offset_ms: number; point_name: string; value: number }[] }

// ── Helpers ──────────────────────────────────────────────────────────────────

function hoursAgoIso(h: number) { return new Date(Date.now() - h * 3600000).toISOString() }
function nowIso() { return new Date().toISOString() }
function fmtDate(iso: string) { return new Date(iso).toLocaleString() }
function fmtDuration(ms: number | null) { return ms != null ? ms < 1000 ? `${ms}ms` : `${(ms/1000).toFixed(1)}s` : '—' }

async function downloadPdf(url: string, filename: string) {
  const token = localStorage.getItem('hira-token') ?? ''
  const r = await fetch(url, { headers: { Authorization: `Bearer ${token}` } })
  if (!r.ok) throw new Error('Error descargando PDF')
  const blob = await r.blob()
  const href = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = href; a.download = filename; a.click()
  URL.revokeObjectURL(href)
}

const STATUS_COLOR: Record<string, string> = {
  success: 'var(--hira-status-ok)',
  failure: 'var(--hira-alarm-high)',
  error: 'var(--hira-alarm-critical)',
  running: 'var(--accent)',
}

const DARK = document.documentElement.getAttribute('data-theme') === 'dark'
const PLOTLY_LAYOUT_BASE = {
  paper_bgcolor: 'transparent',
  plot_bgcolor: 'transparent',
  font: { color: DARK ? '#e2e8f0' : '#1e293b', size: 11 },
  margin: { l: 48, r: 16, t: 24, b: 40 },
  legend: { orientation: 'h' as const },
}

// ── Tab: Históricos ───────────────────────────────────────────────────────────

function HistoricosTab() {
  const [points, setPoints] = useState<Point[]>([])
  const [selected, setSelected] = useState<Point | null>(null)
  const [search, setSearch] = useState('')
  const [from, setFrom] = useState(hoursAgoIso(1))
  const [to, setTo] = useState(nowIso)
  const [bucket, setBucket] = useState('1hour')
  const [chartData, setChartData] = useState<{ x: string[]; y: number[] } | null>(null)
  const [stats, setStats] = useState<{ min: number; max: number; avg: number } | null>(null)
  const [loading, setLoading] = useState(false)
  const [downloading, setDownloading] = useState(false)

  useEffect(() => {
    api.get<Point[]>('/points').then(r => setPoints(r.data)).catch(() => {})
  }, [])

  const load = async () => {
    if (!selected) return
    setLoading(true)
    try {
      const r = await api.get<{ records: { timestamp: string; value: number }[] }>(
        `/history/${selected.id}?from_dt=${from}&to_dt=${to}&interval=${bucket}&limit=2000`
      )
      const xs = r.data.records.map(d => d.timestamp)
      const ys = r.data.records.map(d => d.value)
      setChartData({ x: xs, y: ys })
      if (ys.length > 0) {
        setStats({ min: Math.min(...ys), max: Math.max(...ys), avg: ys.reduce((a, b) => a + b, 0) / ys.length })
      } else {
        setStats(null)
      }
    } finally {
      setLoading(false)
    }
  }

  const dlPdf = async () => {
    if (!selected) return
    setDownloading(true)
    try {
      await downloadPdf(
        `/api/v1/analysis/history/${selected.id}/report?start=${encodeURIComponent(from)}&end=${encodeURIComponent(to)}&bucket=${bucket}`,
        `historico_${selected.name}_${bucket}.pdf`,
      )
    } catch { alert('Error descargando PDF') }
    finally { setDownloading(false) }
  }

  const filtered = points.filter(p => p.name.toLowerCase().includes(search.toLowerCase()))

  return (
    <div style={{ display: 'flex', gap: 16, height: '100%' }}>
      {/* Left: point list */}
      <div style={{ width: 200, flexShrink: 0, display: 'flex', flexDirection: 'column', gap: 8 }}>
        <input
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="Buscar punto…"
          style={inputStyle}
        />
        <div style={{ flex: 1, overflowY: 'auto', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-md)' }}>
          {filtered.map(p => (
            <div
              key={p.id}
              onClick={() => setSelected(p)}
              style={{
                padding: '7px 10px',
                cursor: 'pointer',
                background: selected?.id === p.id ? 'var(--accent-subtle)' : 'transparent',
                borderLeft: selected?.id === p.id ? '3px solid var(--accent)' : '3px solid transparent',
                borderBottom: '1px solid var(--border-subtle)',
                fontSize: 'var(--text-sm)',
                color: selected?.id === p.id ? 'var(--accent)' : 'var(--text-primary)',
              }}
            >
              <div style={{ fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{p.name}</div>
              {p.unit && <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>{p.unit}</div>}
            </div>
          ))}
          {filtered.length === 0 && <div style={{ padding: 12, fontSize: 11, color: 'var(--text-muted)' }}>Sin puntos</div>}
        </div>
      </div>

      {/* Right: controls + chart */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 12 }}>
        {selected ? (
          <>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
              <span style={{ fontWeight: 700, color: 'var(--text-primary)', fontSize: 'var(--text-sm)' }}>{selected.name}</span>
              <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>Desde:</span>
              <input type="datetime-local" value={from.slice(0,16)} onChange={e => setFrom(new Date(e.target.value).toISOString())} style={{ ...inputStyle, width: 170 }} />
              <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>Hasta:</span>
              <input type="datetime-local" value={to.slice(0,16)} onChange={e => setTo(new Date(e.target.value).toISOString())} style={{ ...inputStyle, width: 170 }} />
              <select value={bucket} onChange={e => setBucket(e.target.value)} style={inputStyle}>
                {['raw','1min','5min','1hour','1day'].map(b => <option key={b} value={b}>{b}</option>)}
              </select>
              <button onClick={load} disabled={loading} style={{ ...btnBase, background: 'var(--accent)', color: '#fff' }}>
                {loading ? 'Cargando…' : 'Ver gráfica'}
              </button>
              <button onClick={dlPdf} disabled={downloading} style={{ ...btnBase, background: 'var(--bg-hover)', color: 'var(--text-primary)', border: '1px solid var(--border-default)' }}>
                {downloading ? 'Descargando…' : '⬇ PDF'}
              </button>
            </div>

            {stats && (
              <div style={{ display: 'flex', gap: 16 }}>
                {[['Mín', stats.min], ['Máx', stats.max], ['Promedio', stats.avg]].map(([label, val]) => (
                  <div key={label as string} style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-md)', padding: '8px 14px', minWidth: 90 }}>
                    <div style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>{label}</div>
                    <div style={{ fontSize: 'var(--text-base)', fontWeight: 700, color: 'var(--text-primary)' }}>
                      {(val as number).toFixed(2)} {selected.unit}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {chartData && chartData.x.length > 0 ? (
              <div style={{ flex: 1, minHeight: 280 }}>
                <Plot
                  data={[{ x: chartData.x, y: chartData.y, type: 'scatter', mode: 'lines', name: selected.name, line: { color: '#0891b2', width: 2 } }]}
                  layout={{ ...PLOTLY_LAYOUT_BASE, yaxis: { title: selected.unit || '' } }}
                  style={{ width: '100%', height: '100%' }}
                  config={{ responsive: true, displaylogo: false }}
                />
              </div>
            ) : chartData ? (
              <div style={{ color: 'var(--text-muted)', fontSize: 'var(--text-sm)' }}>Sin datos en el rango seleccionado.</div>
            ) : (
              <div style={{ color: 'var(--text-muted)', fontSize: 'var(--text-sm)' }}>Selecciona rango y haz clic en "Ver gráfica".</div>
            )}
          </>
        ) : (
          <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: 'var(--text-sm)' }}>
            Selecciona un punto para analizar
          </div>
        )}
      </div>
    </div>
  )
}

// ── Tab: Pruebas ──────────────────────────────────────────────────────────────

type TestView = 'execution' | 'compare' | 'trend'

function PruebasTab() {
  const [scripts, setScripts] = useState<TestScript[]>([])
  const [selectedScript, setSelectedScript] = useState<TestScript | null>(null)
  const [executions, setExecutions] = useState<Execution[]>([])
  const [selectedExec, setSelectedExec] = useState<Execution | null>(null)
  const [compareExecs, setCompareExecs] = useState<Set<number>>(new Set())
  const [view, setView] = useState<TestView>('execution')
  const [chartData, setChartData] = useState<ChartPoint[]>([])
  const [trendData, setTrendData] = useState<TrendRow[]>([])
  const [compareData, setCompareData] = useState<CompareRow[]>([])
  const [loading, setLoading] = useState(false)
  const [downloading, setDownloading] = useState(false)

  useEffect(() => {
    api.get<TestScript[]>('/tests/scripts').then(r => setScripts(r.data)).catch(() => {})
  }, [])

  const selectScript = async (s: TestScript) => {
    setSelectedScript(s)
    setSelectedExec(null)
    setCompareExecs(new Set())
    setChartData([]); setTrendData([]); setCompareData([])
    try {
      const r = await api.get<Execution[]>(`/tests/scripts/${s.id}/executions?limit=50`)
      setExecutions(r.data)
    } catch { setExecutions([]) }
  }

  const loadExecChart = async (exec: Execution) => {
    setSelectedExec(exec)
    setLoading(true)
    try {
      const r = await api.get<ChartPoint[]>(`/analysis/executions/${exec.id}/chart`)
      setChartData(r.data)
    } finally { setLoading(false) }
  }

  const loadTrend = async () => {
    if (!selectedScript) return
    setLoading(true)
    try {
      const r = await api.get<TrendRow[]>(`/analysis/scripts/${selectedScript.id}/trend`)
      setTrendData(r.data)
    } finally { setLoading(false) }
  }

  const loadCompare = async () => {
    if (compareExecs.size < 2) { alert('Selecciona 2-5 ejecuciones para comparar'); return }
    setLoading(true)
    try {
      const ids = Array.from(compareExecs).join(',')
      const r = await api.get<CompareRow[]>(`/analysis/executions/compare?ids=${ids}`)
      setCompareData(r.data)
    } catch (e: unknown) {
      alert('Error: ' + ((e as Error)?.message ?? 'No se pueden comparar esas ejecuciones'))
    } finally { setLoading(false) }
  }

  const dlPdf = async () => {
    if (!selectedExec) return
    setDownloading(true)
    try {
      await downloadPdf(`/api/v1/analysis/executions/${selectedExec.id}/report`, `report_${selectedExec.id}.pdf`)
    } catch { alert('Error descargando PDF') }
    finally { setDownloading(false) }
  }

  // Plotly data for execution chart
  const execPlotTraces = () => {
    const byPoint: Record<string, { x: string[]; y: number[] }> = {}
    for (const d of chartData) {
      if (!byPoint[d.point_name]) byPoint[d.point_name] = { x: [], y: [] }
      byPoint[d.point_name].x.push(d.timestamp)
      byPoint[d.point_name].y.push(d.value)
    }
    return Object.entries(byPoint).map(([name, data]) => ({
      x: data.x, y: data.y, type: 'scatter' as const, mode: 'lines+markers' as const, name,
    }))
  }

  // Plotly data for compare chart
  const comparePlotTraces = () =>
    compareData.flatMap(row =>
      (() => {
        const byPoint: Record<string, { x: number[]; y: number[] }> = {}
        for (const p of row.points) {
          if (!byPoint[p.point_name]) byPoint[p.point_name] = { x: [], y: [] }
          byPoint[p.point_name].x.push(p.t_offset_ms)
          byPoint[p.point_name].y.push(p.value)
        }
        return Object.entries(byPoint).map(([pn, d]) => ({
          x: d.x, y: d.y, type: 'scatter' as const, mode: 'lines+markers' as const,
          name: `#${row.execution_id} · ${pn}`,
        }))
      })()
    )

  return (
    <div style={{ display: 'flex', gap: 16, height: '100%' }}>
      {/* Left panel */}
      <div style={{ width: 220, flexShrink: 0, display: 'flex', flexDirection: 'column', gap: 8 }}>
        <div style={{ fontSize: 10, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>Script</div>
        <select value={selectedScript?.id ?? ''} onChange={e => {
          const s = scripts.find(x => x.id === +e.target.value)
          if (s) selectScript(s)
        }} style={inputStyle}>
          <option value="">— Seleccionar —</option>
          {scripts.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
        </select>

        {executions.length > 0 && (
          <>
            <div style={{ fontSize: 10, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', marginTop: 8 }}>
              Ejecuciones
              {view === 'compare' && <span style={{ color: 'var(--accent)', marginLeft: 4 }}>(selecciona 2-5)</span>}
            </div>
            <div style={{ flex: 1, overflowY: 'auto', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-md)' }}>
              {executions.map(exec => {
                const isSelected = selectedExec?.id === exec.id
                const inCompare = compareExecs.has(exec.id)
                return (
                  <div
                    key={exec.id}
                    onClick={() => {
                      if (view === 'compare') {
                        setCompareExecs(prev => {
                          const next = new Set(prev)
                          next.has(exec.id) ? next.delete(exec.id) : (next.size < 5 && next.add(exec.id))
                          return next
                        })
                      } else if (view === 'execution') {
                        loadExecChart(exec)
                      } else {
                        setSelectedExec(exec)
                      }
                    }}
                    style={{
                      padding: '7px 10px',
                      cursor: 'pointer',
                      background: (isSelected && view !== 'compare') || (inCompare && view === 'compare') ? 'var(--accent-subtle)' : 'transparent',
                      borderLeft: (isSelected && view !== 'compare') || (inCompare && view === 'compare') ? '3px solid var(--accent)' : '3px solid transparent',
                      borderBottom: '1px solid var(--border-subtle)',
                      display: 'flex', alignItems: 'center', gap: 8,
                    }}
                  >
                    <span style={{ width: 7, height: 7, borderRadius: '50%', flexShrink: 0, background: STATUS_COLOR[exec.status] ?? 'var(--text-muted)' }} />
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-primary)' }}>#{exec.id}</div>
                      <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>{fmtDuration(exec.ended_at ? (new Date(exec.ended_at).getTime() - new Date(exec.started_at).getTime()) : null)}</div>
                    </div>
                  </div>
                )
              })}
            </div>
          </>
        )}
      </div>

      {/* Right panel */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 12 }}>
        {/* View tabs */}
        <div style={{ display: 'flex', gap: 4, borderBottom: '1px solid var(--border-subtle)', paddingBottom: 8 }}>
          {(['execution', 'compare', 'trend'] as TestView[]).map(v => (
            <button
              key={v}
              onClick={() => {
                setView(v)
                if (v === 'trend' && selectedScript) loadTrend()
              }}
              style={{
                ...btnBase,
                background: view === v ? 'var(--accent-subtle)' : 'transparent',
                color: view === v ? 'var(--accent)' : 'var(--text-secondary)',
                border: view === v ? '1px solid var(--accent)' : '1px solid transparent',
              }}
            >
              {v === 'execution' ? 'Ejecución' : v === 'compare' ? 'Comparar' : 'Tendencia'}
            </button>
          ))}
          {view === 'execution' && selectedExec && (
            <button onClick={dlPdf} disabled={downloading} style={{ ...btnBase, marginLeft: 'auto', background: 'var(--bg-hover)', border: '1px solid var(--border-default)', color: 'var(--text-primary)' }}>
              {downloading ? 'Descargando…' : '⬇ PDF'}
            </button>
          )}
          {view === 'compare' && compareExecs.size >= 2 && (
            <button onClick={loadCompare} disabled={loading} style={{ ...btnBase, marginLeft: 'auto', background: 'var(--accent)', color: '#fff' }}>
              {loading ? 'Cargando…' : `Comparar (${compareExecs.size})`}
            </button>
          )}
        </div>

        {/* View: Execution */}
        {view === 'execution' && (
          loading ? (
            <div style={{ color: 'var(--text-muted)', fontSize: 'var(--text-sm)' }}>Cargando datos…</div>
          ) : chartData.length > 0 ? (
            <div style={{ flex: 1, minHeight: 300 }}>
              <Plot
                data={execPlotTraces()}
                layout={{ ...PLOTLY_LAYOUT_BASE, title: selectedExec ? `Ejecución #${selectedExec.id}` : '' }}
                style={{ width: '100%', height: '100%' }}
                config={{ responsive: true, displaylogo: false }}
              />
            </div>
          ) : (
            <div style={{ color: 'var(--text-muted)', fontSize: 'var(--text-sm)' }}>
              {selectedExec ? 'Esta ejecución no tiene datos de puntos medidos (logs DATA).' : 'Selecciona una ejecución para ver la gráfica.'}
            </div>
          )
        )}

        {/* View: Compare */}
        {view === 'compare' && (
          compareData.length > 0 ? (
            <div style={{ flex: 1, minHeight: 300 }}>
              <Plot
                data={comparePlotTraces()}
                layout={{ ...PLOTLY_LAYOUT_BASE, xaxis: { title: 'Tiempo relativo (ms)' } }}
                style={{ width: '100%', height: '100%' }}
                config={{ responsive: true, displaylogo: false }}
              />
            </div>
          ) : (
            <div style={{ color: 'var(--text-muted)', fontSize: 'var(--text-sm)' }}>
              Selecciona 2-5 ejecuciones del mismo script y haz clic en "Comparar".
            </div>
          )
        )}

        {/* View: Trend */}
        {view === 'trend' && (
          trendData.length > 0 ? (
            <div style={{ flex: 1, minHeight: 300 }}>
              <Plot
                data={[{
                  x: trendData.map(r => r.started_at),
                  y: trendData.map(r => r.duration_ms ?? 0),
                  type: 'bar',
                  marker: { color: trendData.map(r => r.status === 'success' ? '#22c55e' : r.status === 'failure' ? '#f97316' : '#ef4444') },
                  text: trendData.map(r => `#${r.execution_id} · ${r.status}`),
                  textposition: 'none' as const,
                }]}
                layout={{ ...PLOTLY_LAYOUT_BASE, yaxis: { title: 'Duración (ms)' } }}
                style={{ width: '100%', height: '100%' }}
                config={{ responsive: true, displaylogo: false }}
              />
            </div>
          ) : (
            <div style={{ color: 'var(--text-muted)', fontSize: 'var(--text-sm)' }}>
              {selectedScript ? (loading ? 'Cargando tendencia…' : 'Sin ejecuciones para mostrar.') : 'Selecciona un script.'}
            </div>
          )
        )}
      </div>
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

type Tab = 'historicos' | 'pruebas'

export default function AnalysisPage() {
  const [tab, setTab] = useState<Tab>('historicos')
  const { isAdmin } = useAuthStore()
  const adminUser = isAdmin()

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 48px)', overflow: 'hidden' }}>
      {/* Header + tabs */}
      <div style={{ padding: '0 0 12px', borderBottom: '1px solid var(--border-subtle)', flexShrink: 0 }}>
        <h2 style={{ margin: '0 0 12px', fontSize: 'var(--text-xl)', fontWeight: 700, color: 'var(--text-primary)' }}>
          Módulo de Análisis
        </h2>
        <div style={{ display: 'flex', gap: 4 }}>
          <button
            onClick={() => setTab('historicos')}
            style={{ ...btnBase, background: tab === 'historicos' ? 'var(--accent-subtle)' : 'transparent', color: tab === 'historicos' ? 'var(--accent)' : 'var(--text-secondary)', border: tab === 'historicos' ? '1px solid var(--accent)' : '1px solid transparent' }}
          >
            Históricos
          </button>
          {adminUser && (
            <button
              onClick={() => setTab('pruebas')}
              style={{ ...btnBase, background: tab === 'pruebas' ? 'var(--accent-subtle)' : 'transparent', color: tab === 'pruebas' ? 'var(--accent)' : 'var(--text-secondary)', border: tab === 'pruebas' ? '1px solid var(--accent)' : '1px solid transparent' }}
            >
              Pruebas
            </button>
          )}
        </div>
      </div>

      {/* Tab content */}
      <div style={{ flex: 1, padding: '16px 0', overflow: 'hidden' }}>
        {tab === 'historicos' && <HistoricosTab />}
        {tab === 'pruebas' && adminUser && <PruebasTab />}
      </div>
    </div>
  )
}

// ── Shared styles ─────────────────────────────────────────────────────────────

const inputStyle: React.CSSProperties = {
  background: 'var(--bg-surface)',
  border: '1px solid var(--border-default)',
  borderRadius: 'var(--radius-md)',
  color: 'var(--text-primary)',
  padding: '6px 10px',
  fontSize: 'var(--text-sm)',
  outline: 'none',
}

const btnBase: React.CSSProperties = {
  padding: '6px 12px',
  borderRadius: 'var(--radius-md)',
  border: 'none',
  fontSize: 'var(--text-sm)',
  fontWeight: 600,
  cursor: 'pointer',
}
