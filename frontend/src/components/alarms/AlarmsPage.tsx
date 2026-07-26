import { useState, useEffect } from 'react'
import { useAlarms } from '../../hooks/useAlarms'
import { api } from '../../services/api'
import type { AlarmEvent } from '../../store/alarmsStore'

const PRIORITY_COLOR: Record<string, string> = {
  critical: 'var(--hira-alarm-critical)',
  high: 'var(--hira-alarm-high)',
  medium: 'var(--hira-alarm-medium)',
  low: 'var(--hira-alarm-low)',
}

function timeAgo(iso: string): string {
  const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 1000)
  if (diff < 60) return `${diff}s`
  if (diff < 3600) return `${Math.floor(diff / 60)}m`
  return `${Math.floor(diff / 3600)}h`
}

interface AlarmRowProps {
  alarm: AlarmEvent
  onAcknowledge: (id: number) => Promise<void>
}

function AlarmRow({ alarm, onAcknowledge }: AlarmRowProps) {
  const [busy, setBusy] = useState(false)
  const color = PRIORITY_COLOR[alarm.priority] ?? 'var(--md-sys-color-on-surface)'

  async function handleAck() {
    setBusy(true)
    try { await onAcknowledge(alarm.id) } finally { setBusy(false) }
  }

  return (
    <tr>
      <td style={{ padding: '8px 12px' }}>
        <span style={{
          display: 'inline-block', padding: '2px 8px', borderRadius: 4,
          background: color, color: '#fff', fontSize: 11, fontWeight: 700,
          textTransform: 'uppercase',
        }}>
          {alarm.priority}
        </span>
      </td>
      <td style={{ padding: '8px 12px', color: 'var(--md-sys-color-on-surface)' }}>{alarm.point_name}</td>
      <td style={{ padding: '8px 12px', color, fontWeight: 600 }}>{alarm.triggered_value.toFixed(2)}</td>
      <td style={{ padding: '8px 12px', color: 'var(--md-sys-color-on-surface-variant)', maxWidth: 300 }}>{alarm.message}</td>
      <td style={{ padding: '8px 12px', color: 'var(--md-sys-color-on-surface-variant)', fontSize: 12 }}>
        {timeAgo(alarm.triggered_at)}
      </td>
      <td style={{ padding: '8px 12px' }}>
        <span style={{
          fontSize: 11,
          color: alarm.status === 'acknowledged' ? 'var(--hira-status-ok)' : 'var(--md-sys-color-on-surface-variant)',
        }}>
          {alarm.status === 'acknowledged' ? `ACK ${alarm.acknowledged_by ?? ''}` : '—'}
        </span>
      </td>
      <td style={{ padding: '8px 12px' }}>
        {alarm.status === 'active' && (
          <button
            onClick={handleAck}
            disabled={busy}
            style={{
              padding: '4px 10px', borderRadius: 4, border: 'none', cursor: busy ? 'not-allowed' : 'pointer',
              background: 'var(--md-sys-color-primary)', color: 'var(--md-sys-color-on-primary)',
              fontSize: 12, opacity: busy ? 0.5 : 1,
            }}
          >
            {busy ? '…' : 'Reconocer'}
          </button>
        )}
      </td>
    </tr>
  )
}

interface HistoryEntry extends AlarmEvent {
  resolved_at: string | null
}

export function AlarmsPage() {
  const { activeAlarms, unacknowledgedCount, acknowledge } = useAlarms()
  const [history, setHistory] = useState<HistoryEntry[]>([])
  const [filterPriority, setFilterPriority] = useState('')
  const [fromDt, setFromDt] = useState('')
  const [toDt, setToDt] = useState('')

  async function loadHistory() {
    const params = new URLSearchParams()
    if (filterPriority) params.set('priority', filterPriority)
    if (fromDt) params.set('from_dt', new Date(fromDt).toISOString())
    if (toDt) params.set('to_dt', new Date(toDt).toISOString())
    const r = await api.get<HistoryEntry[]>(`/alarms/history?${params}`)
    setHistory(r.data)
  }

  useEffect(() => { loadHistory() }, [])

  const active = Object.values(activeAlarms).sort(
    (a, b) => new Date(b.triggered_at).getTime() - new Date(a.triggered_at).getTime()
  )

  const thStyle = { padding: '8px 12px', textAlign: 'left' as const, fontSize: 12, fontWeight: 700,
    color: 'var(--md-sys-color-on-surface-variant)', textTransform: 'uppercase' as const, letterSpacing: '0.05em' }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <h2 style={{ margin: 0, color: 'var(--md-sys-color-on-surface)' }}>Alarmas</h2>
        {unacknowledgedCount > 0 && (
          <span style={{
            background: 'var(--hira-alarm-critical)', color: '#fff',
            borderRadius: 12, padding: '2px 8px', fontSize: 13, fontWeight: 700,
          }}>
            {unacknowledgedCount}
          </span>
        )}
      </div>

      {/* ── Activas ── */}
      <section>
        <h3 style={{ margin: '0 0 8px', color: 'var(--md-sys-color-on-surface)', fontSize: 15 }}>
          Activas ({active.length})
        </h3>
        <div style={{ overflowX: 'auto', background: 'var(--md-sys-color-surface-container)', borderRadius: 8 }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--md-sys-color-outline-variant)' }}>
                <th style={thStyle}>Prioridad</th>
                <th style={thStyle}>Punto</th>
                <th style={thStyle}>Valor</th>
                <th style={thStyle}>Mensaje</th>
                <th style={thStyle}>Hace</th>
                <th style={thStyle}>Estado</th>
                <th style={thStyle}></th>
              </tr>
            </thead>
            <tbody>
              {active.length === 0 ? (
                <tr><td colSpan={7} style={{ padding: '20px 12px', textAlign: 'center', color: 'var(--hira-status-ok)' }}>
                  Sin alarmas activas
                </td></tr>
              ) : (
                active.map((a) => <AlarmRow key={a.id} alarm={a} onAcknowledge={acknowledge} />)
              )}
            </tbody>
          </table>
        </div>
      </section>

      {/* ── Historial ── */}
      <section>
        <h3 style={{ margin: '0 0 8px', color: 'var(--md-sys-color-on-surface)', fontSize: 15 }}>Historial</h3>
        <div style={{ display: 'flex', gap: 10, marginBottom: 10, flexWrap: 'wrap' }}>
          <select
            value={filterPriority}
            onChange={(e) => setFilterPriority(e.target.value)}
            style={{ padding: '4px 8px', borderRadius: 4, border: '1px solid var(--md-sys-color-outline)',
              background: 'var(--md-sys-color-surface-variant)', color: 'var(--md-sys-color-on-surface-variant)' }}
          >
            <option value="">Todas las prioridades</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
          <input type="datetime-local" value={fromDt} onChange={(e) => setFromDt(e.target.value)}
            style={{ padding: '4px 8px', borderRadius: 4, border: '1px solid var(--md-sys-color-outline)',
              background: 'var(--md-sys-color-surface-variant)', color: 'var(--md-sys-color-on-surface-variant)' }} />
          <input type="datetime-local" value={toDt} onChange={(e) => setToDt(e.target.value)}
            style={{ padding: '4px 8px', borderRadius: 4, border: '1px solid var(--md-sys-color-outline)',
              background: 'var(--md-sys-color-surface-variant)', color: 'var(--md-sys-color-on-surface-variant)' }} />
          <button onClick={loadHistory}
            style={{ padding: '4px 14px', borderRadius: 4, border: 'none', cursor: 'pointer',
              background: 'var(--md-sys-color-primary)', color: 'var(--md-sys-color-on-primary)' }}>
            Filtrar
          </button>
        </div>
        <div style={{ overflowX: 'auto', background: 'var(--md-sys-color-surface-container)', borderRadius: 8 }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--md-sys-color-outline-variant)' }}>
                <th style={thStyle}>Prioridad</th>
                <th style={thStyle}>Punto</th>
                <th style={thStyle}>Valor</th>
                <th style={thStyle}>Estado</th>
                <th style={thStyle}>Disparada</th>
                <th style={thStyle}>Resuelta</th>
              </tr>
            </thead>
            <tbody>
              {history.length === 0 ? (
                <tr><td colSpan={6} style={{ padding: '20px 12px', textAlign: 'center',
                  color: 'var(--md-sys-color-on-surface-variant)' }}>Sin registros</td></tr>
              ) : history.map((h) => (
                <tr key={h.id} style={{ borderBottom: '1px solid var(--md-sys-color-outline-variant)' }}>
                  <td style={{ padding: '6px 12px' }}>
                    <span style={{ display: 'inline-block', padding: '2px 6px', borderRadius: 4,
                      background: PRIORITY_COLOR[h.priority] ?? '#888', color: '#fff', fontSize: 11 }}>
                      {h.priority}
                    </span>
                  </td>
                  <td style={{ padding: '6px 12px', color: 'var(--md-sys-color-on-surface)', fontSize: 13 }}>{h.point_name}</td>
                  <td style={{ padding: '6px 12px', color: 'var(--md-sys-color-on-surface)', fontSize: 13 }}>{h.triggered_value.toFixed(2)}</td>
                  <td style={{ padding: '6px 12px', fontSize: 12, color: 'var(--md-sys-color-on-surface-variant)' }}>{h.status}</td>
                  <td style={{ padding: '6px 12px', fontSize: 12, color: 'var(--md-sys-color-on-surface-variant)' }}>
                    {new Date(h.triggered_at).toLocaleString()}
                  </td>
                  <td style={{ padding: '6px 12px', fontSize: 12, color: 'var(--hira-status-ok)' }}>
                    {h.resolved_at ? new Date(h.resolved_at).toLocaleString() : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}
