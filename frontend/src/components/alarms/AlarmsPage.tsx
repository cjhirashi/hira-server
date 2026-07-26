import { useState, useEffect } from 'react'
import { CheckCircle } from 'lucide-react'
import { useAlarms } from '../../hooks/useAlarms'
import { api } from '../../services/api'
import type { AlarmEvent } from '../../store/alarmsStore'
import { Card } from '../ui/Card'
import { Badge } from '../ui/Badge'
import type { Column } from '../ui/DataTable'
import { DataTable } from '../ui/DataTable'

type Priority = 'critical' | 'high' | 'medium' | 'low'
type BadgeVariant = 'danger' | 'warning' | 'info' | 'neutral'

const PRIORITY_BADGE: Record<Priority, BadgeVariant> = {
  critical: 'danger',
  high:     'warning',
  medium:   'warning',
  low:      'info',
}

const PRIORITY_BORDER: Record<Priority, string> = {
  critical: 'var(--hira-alarm-critical)',
  high:     'var(--hira-alarm-high)',
  medium:   'var(--hira-alarm-medium)',
  low:      'var(--hira-alarm-low)',
}

function timeAgo(iso: string): string {
  const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 1000)
  if (diff < 60) return `${diff}s`
  if (diff < 3600) return `${Math.floor(diff / 60)}m`
  return `${Math.floor(diff / 3600)}h`
}

const inputStyle: React.CSSProperties = {
  padding: '6px 10px',
  borderRadius: 'var(--radius-md)',
  border: '1px solid var(--border-default)',
  background: 'var(--bg-elevated)',
  color: 'var(--text-primary)',
  fontSize: 'var(--text-sm)',
}

const btnStyle: React.CSSProperties = {
  padding: '6px 14px',
  borderRadius: 'var(--radius-md)',
  border: 'none',
  cursor: 'pointer',
  background: 'var(--accent)',
  color: '#000',
  fontSize: 'var(--text-sm)',
  fontWeight: 600,
}

interface HistoryEntry extends AlarmEvent {
  resolved_at: string | null
}

export function AlarmsPage() {
  const { activeAlarms, unacknowledgedCount, acknowledge } = useAlarms()
  const [tab, setTab] = useState<'active' | 'history'>('active')
  const [history, setHistory] = useState<HistoryEntry[]>([])
  const [histLoading, setHistLoading] = useState(false)
  const [filterPriority, setFilterPriority] = useState('')
  const [fromDt, setFromDt] = useState('')
  const [toDt, setToDt] = useState('')

  const active = Object.values(activeAlarms).sort(
    (a, b) => new Date(b.triggered_at).getTime() - new Date(a.triggered_at).getTime()
  )

  async function loadHistory() {
    setHistLoading(true)
    const params = new URLSearchParams()
    if (filterPriority) params.set('priority', filterPriority)
    if (fromDt) params.set('from_dt', new Date(fromDt).toISOString())
    if (toDt) params.set('to_dt', new Date(toDt).toISOString())
    const r = await api.get<HistoryEntry[]>(`/alarms/history?${params}`)
    setHistory(r.data)
    setHistLoading(false)
  }

  useEffect(() => { if (tab === 'history') loadHistory() }, [tab])

  // Columns for active alarms
  const activeColumns: Column<AlarmEvent>[] = [
    {
      key: 'priority',
      header: 'Severidad',
      render: row => (
        <Badge
          variant={PRIORITY_BADGE[row.priority as Priority] ?? 'neutral'}
          label={row.priority.toUpperCase()}
          dot
        />
      ),
    },
    { key: 'point_name', header: 'Punto' },
    {
      key: 'triggered_value',
      header: 'Valor',
      render: row => (
        <span style={{ fontFamily: 'var(--font-mono)', color: PRIORITY_BORDER[row.priority as Priority] }}>
          {Number(row.triggered_value).toFixed(2)}
        </span>
      ),
    },
    { key: 'message', header: 'Condición', style: { color: 'var(--text-secondary)', maxWidth: 280 } },
    {
      key: 'triggered_at',
      header: 'Hace',
      render: row => <span style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-xs)' }}>{timeAgo(row.triggered_at)}</span>,
    },
    {
      key: 'status',
      header: 'Estado',
      render: row => row.status === 'acknowledged'
        ? <Badge variant="success" label={`ACK ${row.acknowledged_by ?? ''}`.trim()} dot />
        : <Badge variant="neutral" label="Activa" />,
    },
    {
      key: 'actions',
      header: '',
      render: row => {
        if (row.status !== 'active') return null
        return (
          <button
            onClick={() => acknowledge(row.id)}
            style={{
              display: 'flex', alignItems: 'center', gap: 5,
              padding: '4px 10px', borderRadius: 'var(--radius-md)',
              border: '1px solid var(--border-default)', background: 'transparent',
              color: 'var(--text-secondary)', cursor: 'pointer', fontSize: 'var(--text-xs)',
              transition: 'all 120ms',
            }}
            onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--success)'; e.currentTarget.style.color = 'var(--success)' }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border-default)'; e.currentTarget.style.color = 'var(--text-secondary)' }}
          >
            <CheckCircle size={13} />
            Reconocer
          </button>
        )
      },
    },
  ]

  // Columns for history
  const histColumns: Column<HistoryEntry>[] = [
    {
      key: 'priority',
      header: 'Severidad',
      render: row => <Badge variant={PRIORITY_BADGE[row.priority as Priority] ?? 'neutral'} label={row.priority.toUpperCase()} dot />,
    },
    { key: 'point_name', header: 'Punto' },
    {
      key: 'triggered_value',
      header: 'Valor',
      render: row => <span style={{ fontFamily: 'var(--font-mono)' }}>{Number(row.triggered_value).toFixed(2)}</span>,
    },
    {
      key: 'status',
      header: 'Estado',
      render: row => <Badge variant={row.status === 'resolved' ? 'success' : 'neutral'} label={row.status} />,
    },
    {
      key: 'triggered_at',
      header: 'Disparada',
      render: row => <span style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-xs)' }}>{new Date(row.triggered_at).toLocaleString()}</span>,
    },
    {
      key: 'resolved_at',
      header: 'Resuelta',
      render: row => row.resolved_at
        ? <span style={{ color: 'var(--success)', fontSize: 'var(--text-xs)' }}>{new Date(row.resolved_at).toLocaleString()}</span>
        : <span style={{ color: 'var(--text-muted)' }}>—</span>,
    },
  ]

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <h1 style={{ margin: 0, fontSize: 'var(--text-xl)', fontWeight: 700 }}>Alarmas</h1>
        {unacknowledgedCount > 0 && (
          <Badge variant="danger" label={String(unacknowledgedCount)} />
        )}
      </div>

      {/* Tab switcher */}
      <div style={{ display: 'flex', gap: 4, borderBottom: '1px solid var(--border-subtle)', paddingBottom: 0 }}>
        {(['active', 'history'] as const).map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            style={{
              padding: '8px 16px',
              border: 'none',
              background: 'transparent',
              cursor: 'pointer',
              fontSize: 'var(--text-sm)',
              fontWeight: 500,
              color: tab === t ? 'var(--accent)' : 'var(--text-secondary)',
              borderBottom: tab === t ? '2px solid var(--accent)' : '2px solid transparent',
              marginBottom: -1,
              transition: 'color 120ms',
            }}
          >
            {t === 'active' ? `Activas (${active.length})` : 'Historial'}
          </button>
        ))}
      </div>

      {/* Active tab */}
      {tab === 'active' && (
        <Card padding="0">
          <DataTable
            columns={activeColumns}
            data={active}
            rowKey={r => r.id}
            emptyMessage="Sin alarmas activas"
            rowStyle={row => ({
              borderLeft: `3px solid ${PRIORITY_BORDER[row.priority as Priority] ?? 'transparent'}`,
            })}
          />
        </Card>
      )}

      {/* History tab */}
      {tab === 'history' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {/* Filters */}
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
            <select value={filterPriority} onChange={e => setFilterPriority(e.target.value)} style={inputStyle}>
              <option value="">Todas las prioridades</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
            <input type="datetime-local" value={fromDt} onChange={e => setFromDt(e.target.value)} style={inputStyle} />
            <span style={{ color: 'var(--text-muted)', fontSize: 'var(--text-xs)' }}>→</span>
            <input type="datetime-local" value={toDt} onChange={e => setToDt(e.target.value)} style={inputStyle} />
            <button onClick={loadHistory} style={btnStyle}>Filtrar</button>
          </div>
          <Card padding="0">
            <DataTable
              columns={histColumns}
              data={history}
              rowKey={r => r.id}
              loading={histLoading}
              emptyMessage="Sin registros en el historial"
            />
          </Card>
        </div>
      )}
    </div>
  )
}
