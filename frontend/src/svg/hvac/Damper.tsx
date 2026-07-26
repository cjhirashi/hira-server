import { useBinding, type Binding } from './bindings'

interface DamperProps {
  width?: number
  height?: number
  label?: string
  bindings?: {
    open_pct?: Binding
    fault?: Binding
  }
  style?: {
    color_normal?: string
    color_fault?: string
    color_off?: string
  }
}

export function Damper({ width = 60, height = 80, label, bindings, style }: DamperProps) {
  const openPct = useBinding(bindings?.open_pct) ?? 0
  const pct = Math.max(0, Math.min(100, openPct))

  const colorNormal = style?.color_normal ?? 'var(--md-sys-color-primary)'
  const colorOff = style?.color_off ?? 'var(--hira-status-offline)'

  const color = pct > 5 ? colorNormal : colorOff
  const cx = width / 2
  const top = 8
  const bottom = height - (label ? 16 : 8)
  const slotH = bottom - top
  const louverH = slotH / 4

  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} aria-label={label}>
      <rect x={4} y={top} width={width - 8} height={slotH} rx={2} fill="none" stroke={color} strokeWidth={1.5} opacity={0.3} />
      {[0, 1, 2, 3].map((i) => {
        const y0 = top + i * louverH + louverH * 0.1
        const pivotY = y0 + louverH * 0.4
        const openAngle = (pct / 100) * 80
        const rad = (openAngle * Math.PI) / 180
        const halfW = (width - 16) / 2
        const dx = halfW * Math.cos(rad)
        const dy = halfW * Math.sin(rad)
        return (
          <line
            key={i}
            x1={cx - dx}
            y1={pivotY - dy}
            x2={cx + dx}
            y2={pivotY + dy}
            stroke={color}
            strokeWidth={3}
            strokeLinecap="round"
          />
        )
      })}
      <text x={cx} y={top - 2} textAnchor="middle" fontSize={9} fill={color} opacity={0.9}>
        {pct.toFixed(0)}%
      </text>
      {label && (
        <text x={cx} y={height - 2} textAnchor="middle" fontSize={9} fill={color} opacity={0.7}>
          {label}
        </text>
      )}
    </svg>
  )
}
