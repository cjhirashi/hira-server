import { useState } from 'react'
import { useBinding, type Binding } from './bindings'
import { api } from '../../services/api'

interface SetpointProps {
  width?: number
  height?: number
  label?: string
  bindings?: {
    value?: Binding
    writable?: boolean
  }
  display?: {
    unit?: string
    decimals?: number
    min?: number
    max?: number
  }
}

export function Setpoint({ width = 80, height = 80, label, bindings, display }: SetpointProps) {
  const value = useBinding(bindings?.value)
  const writable = bindings?.writable ?? false
  const pointId = bindings?.value?.point_id

  const unit = display?.unit ?? '°C'
  const decimals = display?.decimals ?? 1
  const min = display?.min ?? 0
  const max = display?.max ?? 100

  const [writing, setWriting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const cx = width / 2
  const bodyH = height - (label ? 16 : 6)
  const cy = bodyH / 2
  const r = Math.min(cx, cy) - 6

  const color = error ? 'var(--hira-alarm-critical)' : 'var(--hira-status-writing)'

  async function handleStep(delta: number) {
    if (!pointId || !writable || writing) return
    const current = value ?? 0
    const next = Math.max(min, Math.min(max, current + delta))
    setWriting(true)
    setError(null)
    try {
      await api.post(`/points/${pointId}/write`, { value: next })
    } catch {
      setError('write error')
    } finally {
      setWriting(false)
    }
  }

  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} aria-label={label}>
      <circle cx={cx} cy={cy} r={r} fill="none" stroke={color} strokeWidth={2} opacity={0.25} />
      {writable && (
        <>
          <polygon
            points={`${cx},${cy - r + 4} ${cx - 7},${cy - r + 14} ${cx + 7},${cy - r + 14}`}
            fill={writing ? color : 'none'}
            stroke={color}
            strokeWidth={1.5}
            style={{ cursor: 'pointer' }}
            onClick={() => handleStep(0.5)}
          />
          <polygon
            points={`${cx},${cy + r - 4} ${cx - 7},${cy + r - 14} ${cx + 7},${cy + r - 14}`}
            fill={writing ? color : 'none'}
            stroke={color}
            strokeWidth={1.5}
            style={{ cursor: 'pointer' }}
            onClick={() => handleStep(-0.5)}
          />
        </>
      )}
      <text x={cx} y={cy - 2} textAnchor="middle" fontSize={14} fill={color} fontWeight="bold">
        {value !== null ? value.toFixed(decimals) : '—'}
      </text>
      <text x={cx} y={cy + 12} textAnchor="middle" fontSize={9} fill={color} opacity={0.8}>
        {unit}
      </text>
      {error && (
        <text x={cx} y={bodyH - 2} textAnchor="middle" fontSize={8} fill="var(--hira-alarm-critical)">
          {error}
        </text>
      )}
      {label && (
        <text x={cx} y={height - 2} textAnchor="middle" fontSize={9} fill={color} opacity={0.7}>
          {label}
        </text>
      )}
    </svg>
  )
}
