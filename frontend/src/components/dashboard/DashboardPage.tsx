import { useEffect, useState } from 'react'
import { Wifi, WifiOff } from 'lucide-react'
import { api } from '../../services/api'
import { usePoints } from '../../hooks/usePoints'
import { usePointsStore } from '../../store/pointsStore'
import { MimicCanvas } from './MimicCanvas'
import { ControlPanel } from './ControlPanel'
import { Card } from '../ui/Card'

interface MimicData {
  id: number
  name: string
  schema_version: string
  canvas: { width: number; height: number; background?: string }
  elements: Record<string, unknown>[]
  connections: Record<string, unknown>[]
  updated_at: string
}

function LiveIndicator({ connected }: { connected: boolean }) {
  return (
    <span style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 'var(--text-xs)', color: connected ? 'var(--success)' : 'var(--text-muted)' }}>
      {connected
        ? <><Wifi size={13} /> En vivo</>
        : <><WifiOff size={13} /> Desconectado</>
      }
    </span>
  )
}

function ValuesPanel({ elements }: { elements: Record<string, unknown>[] }) {
  const allPoints = usePointsStore(s => s.points)

  const pointElements = elements.filter(el => {
    const bindings = el.bindings as Record<string, unknown> | undefined
    return bindings && (bindings.value || bindings.running)
  })

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
      {pointElements.map((el, i) => {
        const bindings = el.bindings as Record<string, { point_id?: number }> | undefined
        const pointId = bindings?.value?.point_id ?? bindings?.running?.point_id
        const display = el.display as { unit?: string; decimals?: number } | undefined
        const point = pointId ? allPoints[pointId] : undefined
        const value = point?.value
        const quality = point?.quality ?? 'unknown'

        return (
          <div key={String(el.id ?? i)} style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '7px 0',
            borderBottom: '1px solid var(--border-subtle)',
            gap: 8,
          }}>
            <div>
              <div style={{ fontSize: 'var(--text-xs)', fontWeight: 500, color: 'var(--text-primary)' }}>
                {String(el.label ?? el.id)}
              </div>
              <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>
                {String(el.type)}
              </div>
            </div>
            <div style={{ textAlign: 'right', flexShrink: 0 }}>
              <div style={{
                fontSize: 'var(--text-sm)',
                fontWeight: 600,
                color: quality === 'good' ? 'var(--accent)' : 'var(--text-muted)',
                fontFamily: 'var(--font-mono)',
              }}>
                {value !== undefined && value !== null
                  ? `${Number(value).toFixed(display?.decimals ?? 1)} ${display?.unit ?? ''}`
                  : '—'
                }
              </div>
              <div style={{
                width: 6, height: 6, borderRadius: '50%',
                background: quality === 'good' ? 'var(--success)' : 'var(--border-strong)',
                marginLeft: 'auto',
                marginTop: 3,
              }} />
            </div>
          </div>
        )
      })}
      {pointElements.length === 0 && (
        <div style={{ color: 'var(--text-muted)', fontSize: 'var(--text-xs)', padding: '16px 0', textAlign: 'center' }}>
          Sin puntos con bindings
        </div>
      )}
    </div>
  )
}

export function DashboardPage() {
  const [mimic, setMimic] = useState<MimicData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  usePoints()
  const connected = Object.keys(usePointsStore(s => s.points)).length > 0

  useEffect(() => {
    api.get<MimicData[]>('/mimics')
      .then(r => { if (r.data.length > 0) setMimic(r.data[0]); else setError('No hay mimics configurados') })
      .catch(() => setError('Error al cargar el mimic'))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return (
    <div style={{ color: 'var(--text-secondary)', padding: 32 }}>Cargando dashboard…</div>
  )

  if (error || !mimic) return (
    <div style={{ color: 'var(--danger)', padding: 32 }}>{error ?? 'Sin datos'}</div>
  )

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20, height: '100%' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <h1 style={{ margin: 0, fontSize: 'var(--text-xl)', fontWeight: 700, color: 'var(--text-primary)' }}>
          {mimic.name}
        </h1>
        <LiveIndicator connected={!!connected} />
      </div>

      {/* Main layout: mimic + panel */}
      <div style={{ display: 'flex', gap: 16, flex: 1, minHeight: 0 }}>
        {/* Mimic canvas */}
        <Card style={{ flex: 1, minWidth: 0 }} padding="0">
          <div style={{
            width: '100%',
            height: '100%',
            minHeight: 420,
            backgroundImage: 'radial-gradient(circle, var(--border-subtle) 1px, transparent 1px)',
            backgroundSize: '24px 24px',
            borderRadius: 'var(--radius-lg)',
            overflow: 'hidden',
            padding: 16,
          }}>
            <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', marginBottom: 8 }}>
              {mimic.name}
            </div>
            <MimicCanvas
              canvas={mimic.canvas}
              elements={mimic.elements as never}
              connections={mimic.connections as never}
            />
          </div>
        </Card>

        {/* Values panel */}
        <Card
          title="Valores en tiempo real"
          subtitle="Actualización automática"
          actions={<LiveIndicator connected={!!connected} />}
          style={{ width: 280, flexShrink: 0, overflowY: 'auto' }}
          padding="12px 16px"
        >
          <ValuesPanel elements={mimic.elements} />
        </Card>
      </div>

      {/* Control panel */}
      <ControlPanel elements={mimic.elements as never} />
    </div>
  )
}
