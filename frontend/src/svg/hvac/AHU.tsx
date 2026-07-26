import { useBoolBinding, useBinding, type Binding } from './bindings'

interface AHUProps {
  width?: number
  height?: number
  label?: string
  bindings?: {
    running?: Binding
    supply_temp?: Binding
    fault?: Binding
  }
  style?: {
    color_normal?: string
    color_fault?: string
    color_off?: string
  }
}

export function AHU({ width = 160, height = 100, label, bindings, style }: AHUProps) {
  const running = useBoolBinding(bindings?.running)
  const fault = useBoolBinding(bindings?.fault)
  const supplyTemp = useBinding(bindings?.supply_temp)

  const colorNormal = style?.color_normal ?? 'var(--md-sys-color-primary)'
  const colorFault = style?.color_fault ?? 'var(--hira-alarm-critical)'
  const colorOff = style?.color_off ?? 'var(--hira-status-offline)'
  const color = fault ? colorFault : running ? colorNormal : colorOff

  const bodyH = height - (label ? 16 : 6)
  const cx = width / 2
  const cy = bodyH / 2

  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} aria-label={label}>
      <rect x={2} y={2} width={width - 4} height={bodyH - 2} rx={6} fill={color} fillOpacity={0.06} stroke={color} strokeWidth={2} />
      <text x={8} y={16} fontSize={9} fill={color} opacity={0.9} fontWeight="bold">
        AHU
      </text>
      <rect x={8} y={20} width={34} height={bodyH - 30} rx={3} fill="none" stroke={color} strokeWidth={1.5} opacity={0.5} />
      <text x={25} y={bodyH / 2 - 2} textAnchor="middle" fontSize={7} fill={color} opacity={0.7}>FILTER</text>
      <text x={25} y={bodyH / 2 + 7} textAnchor="middle" fontSize={7} fill={color} opacity={0.7}>COIL</text>
      <circle cx={cx} cy={cy} r={bodyH * 0.28} fill="none" stroke={color} strokeWidth={2} opacity={0.3} />
      {[0, 120, 240].map((a) => {
        const r = bodyH * 0.28
        const rad = (a * Math.PI) / 180
        return (
          <ellipse
            key={a}
            cx={cx}
            cy={cy - r * 0.5}
            rx={r * 0.25}
            ry={r * 0.45}
            fill={color}
            opacity={running ? 0.8 : 0.2}
            transform={`rotate(${a}, ${cx}, ${cy})`}
          />
        )
      })}
      <circle cx={cx} cy={cy} r={4} fill={color} />
      {supplyTemp !== null && (
        <text x={width - 8} y={bodyH / 2 + 4} textAnchor="end" fontSize={11} fill={color} fontWeight="bold">
          {supplyTemp?.toFixed(1)}°
        </text>
      )}
      <line x1={width - 44} y1={cy} x2={width - 8} y2={cy} stroke={color} strokeWidth={1.5} strokeDasharray="3,2" opacity={0.4} />
      {label && (
        <text x={cx} y={height - 2} textAnchor="middle" fontSize={9} fill={color} opacity={0.7}>
          {label}
        </text>
      )}
    </svg>
  )
}
