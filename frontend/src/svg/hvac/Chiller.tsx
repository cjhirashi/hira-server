import { useBoolBinding, useBinding, type Binding } from './bindings'

interface ChillerProps {
  width?: number
  height?: number
  label?: string
  bindings?: {
    running?: Binding
    load_pct?: Binding
    fault?: Binding
  }
  style?: {
    color_running?: string
    color_fault?: string
    color_off?: string
  }
}

export function Chiller({ width = 120, height = 100, label, bindings, style }: ChillerProps) {
  const running = useBoolBinding(bindings?.running)
  const fault = useBoolBinding(bindings?.fault)
  const loadPct = useBinding(bindings?.load_pct) ?? 0
  const pct = Math.max(0, Math.min(100, loadPct))

  const colorRunning = style?.color_running ?? 'var(--md-sys-color-primary)'
  const colorFault = style?.color_fault ?? 'var(--hira-alarm-critical)'
  const colorOff = style?.color_off ?? 'var(--hira-status-offline)'
  const color = fault ? colorFault : running ? colorRunning : colorOff

  const bodyH = height - (label ? 20 : 10)
  const barW = width - 20
  const barH = 8
  const barY = bodyH - barH - 4
  const fillW = (pct / 100) * barW

  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} aria-label={label}>
      <rect x={4} y={4} width={width - 8} height={bodyH - 4} rx={6} fill="none" stroke={color} strokeWidth={2} />
      <text x={width / 2} y={18} textAnchor="middle" fontSize={10} fill={color} fontWeight="bold">
        CHILLER
      </text>
      <rect x={8} y={22} width={width - 16} height={bodyH - 42} rx={3} fill={color} opacity={0.08} />
      <circle cx={width / 2} cy={(22 + bodyH - 16) / 2} r={12} fill={color} opacity={running ? 0.4 : 0.1} />
      <text x={width / 2} y={(22 + bodyH - 16) / 2 + 4} textAnchor="middle" fontSize={9} fill={color}>
        {running ? 'ON' : 'OFF'}
      </text>
      <rect x={10} y={barY} width={barW} height={barH} rx={3} fill="none" stroke={color} strokeWidth={1} opacity={0.4} />
      <rect x={10} y={barY} width={fillW} height={barH} rx={3} fill={color} opacity={0.7} />
      <text x={10 + barW + 2} y={barY + barH - 1} fontSize={8} fill={color} opacity={0.8}>
        {pct.toFixed(0)}%
      </text>
      {label && (
        <text x={width / 2} y={height - 2} textAnchor="middle" fontSize={9} fill={color} opacity={0.7}>
          {label}
        </text>
      )}
    </svg>
  )
}
