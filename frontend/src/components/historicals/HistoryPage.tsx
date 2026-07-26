import { useEffect, useState } from 'react'
import Plot from 'react-plotly.js'
import { api } from '../../services/api'
import { usePointHistory, type HistoryInterval, type PointHistoryRecord } from '../../hooks/usePointHistory'

interface PointOption {
  id: number
  name: string
  unit: string
}

const QUICK_RANGES: { label: string; hours: number }[] = [
  { label: '1h', hours: 1 },
  { label: '24h', hours: 24 },
  { label: '7d', hours: 168 },
  { label: '30d', hours: 720 },
]

const INTERVALS: { label: string; value: HistoryInterval }[] = [
  { label: 'Raw', value: 'raw' },
  { label: '1 min', value: '1min' },
  { label: '5 min', value: '5min' },
  { label: '1 hora', value: '1hour' },
  { label: '1 día', value: '1day' },
]

function toIso(d: Date): string {
  return d.toISOString()
}

function nowIso(): string {
  return toIso(new Date())
}

function hoursAgoIso(h: number): string {
  return toIso(new Date(Date.now() - h * 3600 * 1000))
}

function qualityColor(r: PointHistoryRecord): string {
  if (r.quality === 'bad') return 'var(--hira-alarm-high)'
  if (r.quality === 'uncertain') return 'var(--hira-alarm-medium)'
  return 'var(--hira-status-ok)'
}

export default function HistoryPage() {
  const [points, setPoints] = useState<PointOption[]>([])
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [search, setSearch] = useState('')
  const [fromDt, setFromDt] = useState(() => hoursAgoIso(1))
  const [toDt, setToDt] = useState(() => nowIso())
  const [interval, setInterval] = useState<HistoryInterval>('raw')
  const [activeRange, setActiveRange] = useState<number | null>(1)

  useEffect(() => {
    api.get<{ items: PointOption[] }>('/points').then((r) => {
      const list = Array.isArray(r.data) ? r.data : (r.data as any).items ?? []
      setPoints(list)
    }).catch(() => {})
  }, [])

  const { data, loading, error } = usePointHistory({
    pointId: selectedId,
    fromDt,
    toDt,
    interval,
  })

  const selectedPoint = points.find((p) => p.id === selectedId)

  const handleQuickRange = (hours: number) => {
    setActiveRange(hours)
    setToDt(nowIso())
    setFromDt(hoursAgoIso(hours))
  }

  const handleExportCsv = () => {
    if (!selectedId) return
    const token = localStorage.getItem('hira-token') ?? ''
    const params = new URLSearchParams({
      from_dt: fromDt,
      to_dt: toDt,
      interval,
      format: 'csv',
      limit: '10000',
    })
    const url = `/api/v1/points/${selectedId}/history?${params}`
    const a = document.createElement('a')
    a.href = url
    a.setAttribute('download', `point_${selectedId}_history.csv`)
    // Fetch manually to attach auth header, then create blob URL
    fetch(url, { headers: { Authorization: `Bearer ${token}` } })
      .then((r) => r.blob())
      .then((blob) => {
        const objUrl = URL.createObjectURL(blob)
        a.href = objUrl
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        URL.revokeObjectURL(objUrl)
      })
  }

  const filteredPoints = points.filter((p) =>
    p.name.toLowerCase().includes(search.toLowerCase())
  )

  // Build Plotly traces grouped by quality
  const records = data?.records ?? []
  const goodX = records.filter((r) => r.quality !== 'bad').map((r) => r.timestamp)
  const goodY = records.filter((r) => r.quality !== 'bad').map((r) => r.value)

  const yAxisLabel = selectedPoint?.unit ? `${selectedPoint.name} (${selectedPoint.unit})` : selectedPoint?.name ?? 'Valor'

  const isDark = document.documentElement.getAttribute('data-theme') === 'dark'
  const plotBg = isDark ? '#1e1e2e' : '#ffffff'
  const plotPaper = isDark ? '#181825' : '#f5f5f5'
  const fontColor = isDark ? '#cdd6f4' : '#1c1c1e'

  return (
    <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
      <h2 style={{ margin: 0, color: 'var(--md-sys-color-on-surface)' }}>Históricos</h2>

      {/* Point selector */}
      <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', alignItems: 'center' }}>
        <input
          type="text"
          placeholder="Buscar punto..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{
            padding: '8px 12px',
            borderRadius: '8px',
            border: '1px solid var(--md-sys-color-outline)',
            background: 'var(--md-sys-color-surface-variant)',
            color: 'var(--md-sys-color-on-surface-variant)',
            minWidth: '200px',
          }}
        />
        <select
          value={selectedId ?? ''}
          onChange={(e) => setSelectedId(e.target.value ? Number(e.target.value) : null)}
          style={{
            padding: '8px 12px',
            borderRadius: '8px',
            border: '1px solid var(--md-sys-color-outline)',
            background: 'var(--md-sys-color-surface-variant)',
            color: 'var(--md-sys-color-on-surface-variant)',
            minWidth: '200px',
          }}
        >
          <option value="">— Seleccionar punto —</option>
          {filteredPoints.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name} {p.unit ? `(${p.unit})` : ''}
            </option>
          ))}
        </select>
      </div>

      {/* Quick ranges */}
      <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
        {QUICK_RANGES.map((r) => (
          <button
            key={r.hours}
            onClick={() => handleQuickRange(r.hours)}
            style={{
              padding: '6px 14px',
              borderRadius: '20px',
              border: '1px solid var(--md-sys-color-outline)',
              background: activeRange === r.hours ? 'var(--md-sys-color-primary)' : 'transparent',
              color: activeRange === r.hours ? 'var(--md-sys-color-on-primary)' : 'var(--md-sys-color-on-surface)',
              cursor: 'pointer',
              fontWeight: 500,
            }}
          >
            {r.label}
          </button>
        ))}
        <input
          type="datetime-local"
          value={fromDt.slice(0, 16)}
          onChange={(e) => { setActiveRange(null); setFromDt(new Date(e.target.value).toISOString()) }}
          style={{ padding: '6px', borderRadius: '8px', border: '1px solid var(--md-sys-color-outline)', background: 'var(--md-sys-color-surface-variant)', color: 'var(--md-sys-color-on-surface-variant)' }}
        />
        <span style={{ color: 'var(--md-sys-color-on-surface-variant)' }}>→</span>
        <input
          type="datetime-local"
          value={toDt.slice(0, 16)}
          onChange={(e) => { setActiveRange(null); setToDt(new Date(e.target.value).toISOString()) }}
          style={{ padding: '6px', borderRadius: '8px', border: '1px solid var(--md-sys-color-outline)', background: 'var(--md-sys-color-surface-variant)', color: 'var(--md-sys-color-on-surface-variant)' }}
        />
      </div>

      {/* Interval selector */}
      <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
        <span style={{ color: 'var(--md-sys-color-on-surface-variant)', fontSize: '14px' }}>Intervalo:</span>
        {INTERVALS.map((i) => (
          <button
            key={i.value}
            onClick={() => setInterval(i.value)}
            style={{
              padding: '5px 12px',
              borderRadius: '20px',
              border: '1px solid var(--md-sys-color-outline)',
              background: interval === i.value ? 'var(--md-sys-color-secondary)' : 'transparent',
              color: interval === i.value ? 'var(--md-sys-color-on-secondary)' : 'var(--md-sys-color-on-surface)',
              cursor: 'pointer',
              fontSize: '13px',
            }}
          >
            {i.label}
          </button>
        ))}

        {selectedId && (
          <button
            onClick={handleExportCsv}
            style={{
              marginLeft: 'auto',
              padding: '6px 16px',
              borderRadius: '8px',
              border: '1px solid var(--md-sys-color-primary)',
              background: 'transparent',
              color: 'var(--md-sys-color-primary)',
              cursor: 'pointer',
              fontWeight: 500,
            }}
          >
            Exportar CSV
          </button>
        )}
      </div>

      {/* Chart */}
      {loading && (
        <div style={{ color: 'var(--md-sys-color-on-surface-variant)', padding: '32px', textAlign: 'center' }}>
          Cargando datos...
        </div>
      )}
      {error && (
        <div style={{ color: 'var(--hira-alarm-critical)', padding: '12px', borderRadius: '8px', background: 'color-mix(in srgb, var(--hira-alarm-critical) 10%, transparent)' }}>
          {error}
        </div>
      )}
      {!loading && !error && records.length === 0 && selectedId && (
        <div style={{ color: 'var(--md-sys-color-on-surface-variant)', padding: '32px', textAlign: 'center' }}>
          Sin datos para el rango seleccionado
        </div>
      )}
      {!loading && records.length > 0 && (
        <div style={{ borderRadius: '12px', overflow: 'hidden', border: '1px solid var(--md-sys-color-outline)' }}>
          <Plot
            data={[
              {
                x: goodX,
                y: goodY,
                type: 'scatter',
                mode: 'lines',
                line: { color: 'var(--hira-status-ok)', width: 2 },
                name: yAxisLabel,
                hovertemplate: '<b>%{x|%Y-%m-%d %H:%M:%S}</b><br>Valor: %{y}<br>Calidad: good<extra></extra>',
              },
            ]}
            layout={{
              paper_bgcolor: plotPaper,
              plot_bgcolor: plotBg,
              font: { color: fontColor, family: 'Inter, system-ui, sans-serif', size: 12 },
              margin: { t: 32, r: 16, b: 48, l: 56 },
              xaxis: {
                type: 'date',
                gridcolor: isDark ? '#313244' : '#e0e0e0',
                tickformat: '%H:%M\n%b %d',
              },
              yaxis: {
                title: { text: yAxisLabel },
                gridcolor: isDark ? '#313244' : '#e0e0e0',
              },
              showlegend: false,
              hovermode: 'closest',
            }}
            config={{ responsive: true, displayModeBar: false }}
            style={{ width: '100%', minHeight: '360px' }}
            useResizeHandler
          />
        </div>
      )}
    </div>
  )
}
