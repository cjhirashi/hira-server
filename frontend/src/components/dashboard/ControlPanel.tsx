import { useState } from 'react'
import { usePointsStore } from '../../store/pointsStore'
import { api } from '../../services/api'

interface MimicElement {
  id: string
  type: string
  label?: string
  bindings?: {
    value?: { point_id: number }
    running?: { point_id: number }
    writable?: boolean
  }
  display?: {
    unit?: string
    decimals?: number
    min?: number
    max?: number
  }
}

interface ControlPanelProps {
  elements: MimicElement[]
}

interface SetpointRowProps {
  element: MimicElement
}

function SetpointRow({ element }: SetpointRowProps) {
  const pointId = element.bindings?.value?.point_id
  const value = usePointsStore((s) => (pointId ? s.points[pointId]?.value : undefined))
  const unit = element.display?.unit ?? ''
  const decimals = element.display?.decimals ?? 1
  const min = element.display?.min ?? 0
  const max = element.display?.max ?? 100

  const [input, setInput] = useState('')
  const [writing, setWriting] = useState(false)
  const [msg, setMsg] = useState<string | null>(null)

  async function handleWrite() {
    if (!pointId) return
    const v = parseFloat(input)
    if (isNaN(v) || v < min || v > max) {
      setMsg(`Valor fuera de rango [${min}–${max}]`)
      return
    }
    setWriting(true)
    setMsg(null)
    try {
      await api.post(`/points/${pointId}/write`, { value: v })
      setMsg('OK')
      setInput('')
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } }
      setMsg(err?.response?.data?.detail ?? 'Error')
    } finally {
      setWriting(false)
    }
  }

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        padding: '8px 0',
        borderBottom: '1px solid var(--border-subtle)',
      }}
    >
      <span
        style={{
          flex: 1,
          fontSize: 13,
          color: 'var(--text-primary)',
        }}
      >
        {element.label ?? element.id}
      </span>
      <span
        style={{
          minWidth: 70,
          fontSize: 16,
          fontWeight: 600,
          color: 'var(--hira-status-writing)',
          textAlign: 'right',
        }}
      >
        {value !== undefined ? `${(value as number).toFixed(decimals)} ${unit}` : '—'}
      </span>
      <input
        type="number"
        min={min}
        max={max}
        step={0.5}
        value={input}
        onChange={(e) => setInput(e.target.value)}
        placeholder={`${min}–${max}`}
        disabled={writing}
        style={{
          width: 80,
          padding: '4px 8px',
          borderRadius: 4,
          border: '1px solid var(--border-default)',
          background: 'var(--bg-elevated)',
          color: 'var(--text-secondary)',
          fontSize: 13,
        }}
      />
      <button
        onClick={handleWrite}
        disabled={writing || !input}
        style={{
          padding: '4px 12px',
          borderRadius: 4,
          border: 'none',
          background: 'var(--accent)',
          color: '#000',
          cursor: writing || !input ? 'not-allowed' : 'pointer',
          fontSize: 13,
          opacity: writing || !input ? 0.5 : 1,
        }}
      >
        {writing ? '…' : 'Set'}
      </button>
      {msg && (
        <span
          style={{
            fontSize: 11,
            color: msg === 'OK' ? 'var(--hira-status-ok)' : 'var(--hira-alarm-critical)',
          }}
        >
          {msg}
        </span>
      )}
    </div>
  )
}

export function ControlPanel({ elements }: ControlPanelProps) {
  const writable = elements.filter(
    (el) => el.type === 'Setpoint' && el.bindings?.writable && el.bindings?.value?.point_id
  )

  if (writable.length === 0) return null

  return (
    <div
      style={{
        background: 'var(--bg-surface)',
        borderRadius: 8,
        padding: '12px 16px',
      }}
    >
      <h3
        style={{
          margin: '0 0 8px',
          fontSize: 14,
          fontWeight: 600,
          color: 'var(--text-secondary)',
          textTransform: 'uppercase',
          letterSpacing: '0.05em',
        }}
      >
        Panel de Control
      </h3>
      {writable.map((el) => (
        <SetpointRow key={el.id} element={el} />
      ))}
    </div>
  )
}
