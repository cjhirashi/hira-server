import { useBinding, type Binding } from './bindings'
import { usePointsStore } from '../../store/pointsStore'

type SensorType = 'temperature' | 'humidity' | 'pressure' | 'co2' | 'flow' | 'generic'

interface SensorProps {
  width?: number
  height?: number
  label?: string
  sensor_type?: SensorType
  bindings?: {
    value?: Binding
  }
  display?: {
    unit?: string
    decimals?: number
    min?: number
    max?: number
  }
}

const SENSOR_ICONS: Record<SensorType, string> = {
  temperature: '°',
  humidity: '%',
  pressure: 'Pa',
  co2: 'CO₂',
  flow: 'L/s',
  generic: '◆',
}

export function Sensor({ width = 80, height = 80, label, sensor_type = 'generic', bindings, display }: SensorProps) {
  const value = useBinding(bindings?.value)
  const quality = usePointsStore((s) =>
    bindings?.value ? s.points[bindings.value.point_id]?.quality : undefined
  )

  const unit = display?.unit ?? SENSOR_ICONS[sensor_type]
  const decimals = display?.decimals ?? 1
  const min = display?.min
  const max = display?.max

  let alarmColor = 'var(--md-sys-color-primary)'
  if (quality === 'bad') alarmColor = 'var(--hira-alarm-critical)'
  else if (quality === 'uncertain') alarmColor = 'var(--hira-alarm-medium)'

  const pct = value !== null && min !== undefined && max !== undefined
    ? Math.max(0, Math.min(1, (value - min) / (max - min)))
    : null

  const cx = width / 2
  const bodyH = height - (label ? 16 : 6)
  const cy = bodyH / 2
  const r = Math.min(cx, cy) - 6

  const circumference = 2 * Math.PI * r
  const dashoffset = pct !== null ? circumference * (1 - pct) : circumference

  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} aria-label={label}>
      <circle cx={cx} cy={cy} r={r} fill="none" stroke={alarmColor} strokeWidth={2} opacity={0.2} />
      {pct !== null && (
        <circle
          cx={cx}
          cy={cy}
          r={r}
          fill="none"
          stroke={alarmColor}
          strokeWidth={3}
          strokeDasharray={circumference}
          strokeDashoffset={dashoffset}
          strokeLinecap="round"
          transform={`rotate(-90, ${cx}, ${cy})`}
          opacity={0.7}
        />
      )}
      <text x={cx} y={cy - 2} textAnchor="middle" fontSize={14} fill={alarmColor} fontWeight="bold">
        {value !== null ? value.toFixed(decimals) : '—'}
      </text>
      <text x={cx} y={cy + 12} textAnchor="middle" fontSize={9} fill={alarmColor} opacity={0.8}>
        {unit}
      </text>
      {label && (
        <text x={cx} y={height - 2} textAnchor="middle" fontSize={9} fill={alarmColor} opacity={0.7}>
          {label}
        </text>
      )}
    </svg>
  )
}
