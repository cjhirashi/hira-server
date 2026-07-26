import { useEffect, useState } from 'react'
import { api } from '../../services/api'
import { usePoints } from '../../hooks/usePoints'
import { MimicCanvas } from './MimicCanvas'
import { ControlPanel } from './ControlPanel'


interface MimicData {
  id: number
  name: string
  schema_version: string
  canvas: { width: number; height: number; background?: string }
  elements: Record<string, unknown>[]
  connections: Record<string, unknown>[]
  updated_at: string
}

export function DashboardPage() {
  const [mimic, setMimic] = useState<MimicData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  usePoints()

  useEffect(() => {
    api
      .get<MimicData[]>('/mimics')
      .then((r) => {
        if (r.data.length > 0) setMimic(r.data[0])
        else setError('No hay mimics configurados')
      })
      .catch((e) => {
        console.error('Error cargando mimics', e)
        setError('Error al cargar el mimic')
      })
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div style={{ padding: 24, color: 'var(--md-sys-color-on-surface-variant)' }}>
        Cargando dashboard…
      </div>
    )
  }

  if (error || !mimic) {
    return (
      <div style={{ padding: 24, color: 'var(--hira-alarm-critical)' }}>
        {error ?? 'Sin datos'}
      </div>
    )
  }

  return (
    <div style={{ padding: 16, display: 'flex', flexDirection: 'column', gap: 16 }}>
      <h2
        style={{
          margin: 0,
          fontSize: 18,
          color: 'var(--md-sys-color-on-surface)',
          fontWeight: 600,
        }}
      >
        {mimic.name}
      </h2>

      <div style={{ overflowX: 'auto' }}>
        <MimicCanvas
          canvas={mimic.canvas}
          elements={mimic.elements as never}
          connections={mimic.connections as never}
        />
      </div>

      <ControlPanel elements={mimic.elements as never} />
    </div>
  )
}
