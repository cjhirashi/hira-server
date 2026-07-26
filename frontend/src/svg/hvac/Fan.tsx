import { useEffect, useRef } from 'react'
import { useBoolBinding, useBinding, type Binding } from './bindings'

interface FanProps {
  width?: number
  height?: number
  label?: string
  bindings?: {
    running?: Binding
    speed_pct?: Binding
    fault?: Binding
  }
  style?: {
    color_normal?: string
    color_fault?: string
    color_off?: string
  }
}

export function Fan({ width = 80, height = 80, label, bindings, style }: FanProps) {
  const running = useBoolBinding(bindings?.running)
  const fault = useBoolBinding(bindings?.fault)
  const speedPct = useBinding(bindings?.speed_pct)
  const bladeRef = useRef<SVGGElement>(null)
  const angleRef = useRef(0)
  const rafRef = useRef<number>(0)

  const colorFault = style?.color_fault ?? 'var(--hira-alarm-high)'
  const colorNormal = style?.color_normal ?? 'var(--md-sys-color-primary)'
  const colorOff = style?.color_off ?? 'var(--hira-status-offline)'

  const color = fault ? colorFault : running ? colorNormal : colorOff
  const rpm = running ? ((speedPct ?? 100) / 100) * 360 : 0

  useEffect(() => {
    let last = performance.now()
    const tick = (now: number) => {
      const dt = (now - last) / 1000
      last = now
      angleRef.current = (angleRef.current + rpm * dt) % 360
      if (bladeRef.current) {
        bladeRef.current.setAttribute('transform', `rotate(${angleRef.current}, 40, 40)`)
      }
      rafRef.current = requestAnimationFrame(tick)
    }
    rafRef.current = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(rafRef.current)
  }, [rpm])

  const cx = width / 2
  const cy = height / 2
  const r = Math.min(width, height) / 2 - 4

  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} aria-label={label}>
      <circle cx={cx} cy={cy} r={r} fill="none" stroke={color} strokeWidth={2} opacity={0.3} />
      <g ref={bladeRef}>
        {[0, 120, 240].map((angle) => (
          <ellipse
            key={angle}
            cx={cx}
            cy={cy - r * 0.5}
            rx={r * 0.28}
            ry={r * 0.48}
            fill={color}
            opacity={0.85}
            transform={`rotate(${angle}, ${cx}, ${cy})`}
          />
        ))}
      </g>
      <circle cx={cx} cy={cy} r={4} fill={color} />
      {label && (
        <text x={cx} y={height - 2} textAnchor="middle" fontSize={9} fill={color} opacity={0.8}>
          {label}
        </text>
      )}
    </svg>
  )
}
