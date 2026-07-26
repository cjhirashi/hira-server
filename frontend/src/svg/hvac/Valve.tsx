import { useBinding, type Binding } from './bindings'

interface ValveProps {
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
  }
}

export function Valve({ width = 60, height = 60, label, bindings, style }: ValveProps) {
  const openPct = useBinding(bindings?.open_pct) ?? 0
  const pct = Math.max(0, Math.min(100, openPct))

  const colorNormal = style?.color_normal ?? 'var(--md-sys-color-tertiary)'
  const colorFault = style?.color_fault ?? 'var(--hira-alarm-high)'
  const color = pct > 5 ? colorNormal : 'var(--hira-status-offline)'

  const cx = width / 2
  const cy = height / 2 - (label ? 6 : 0)
  const r = Math.min(width, height) / 2 - 10

  const stemH = 10
  const stemY1 = cy - r - stemH
  const handleAngle = ((100 - pct) / 100) * 90
  const hRad = (handleAngle * Math.PI) / 180
  const hx = cx + r * 0.7 * Math.sin(hRad)
  const hy = stemY1 - r * 0.7 * Math.cos(hRad)

  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} aria-label={label}>
      <polygon
        points={`${cx - r},${cy} ${cx},${cy - r} ${cx + r},${cy} ${cx},${cy + r}`}
        fill="none"
        stroke={color}
        strokeWidth={2}
      />
      <line x1={cx} y1={cy - r} x2={cx} y2={stemY1} stroke={color} strokeWidth={2} />
      <line x1={cx} y1={stemY1} x2={hx} y2={hy} stroke={colorFault} strokeWidth={3} strokeLinecap="round" />
      <circle cx={cx} cy={stemY1} r={2} fill={color} />
      <text x={cx} y={cy + r + 10} textAnchor="middle" fontSize={9} fill={color} opacity={0.9}>
        {pct.toFixed(0)}%
      </text>
      {label && (
        <text x={cx} y={height - 1} textAnchor="middle" fontSize={9} fill={color} opacity={0.7}>
          {label}
        </text>
      )}
    </svg>
  )
}
