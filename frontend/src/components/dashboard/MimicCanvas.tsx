import { useEffect, useRef } from 'react'
import { Fan, Damper, Valve, Chiller, AHU, Sensor, Setpoint } from '../../svg/hvac'
import { usePointsStore } from '../../store/pointsStore'

interface MimicElement {
  id: string
  type: string
  sensor_type?: string
  position: { x: number; y: number }
  size: { width: number; height: number }
  label?: string
  bindings?: Record<string, unknown>
  display?: Record<string, unknown>
  style?: Record<string, unknown>
}

interface MimicConnection {
  id: string
  from: string
  to: string
  style?: string
}

interface Canvas {
  width: number
  height: number
  background?: string
}

interface MimicCanvasProps {
  canvas: Canvas
  elements: MimicElement[]
  connections: MimicConnection[]
}

const COMPONENTS: Record<string, React.ComponentType<Record<string, unknown>>> = {
  Fan: Fan as React.ComponentType<Record<string, unknown>>,
  Damper: Damper as React.ComponentType<Record<string, unknown>>,
  Valve: Valve as React.ComponentType<Record<string, unknown>>,
  Chiller: Chiller as React.ComponentType<Record<string, unknown>>,
  AHU: AHU as React.ComponentType<Record<string, unknown>>,
  Sensor: Sensor as React.ComponentType<Record<string, unknown>>,
  Setpoint: Setpoint as React.ComponentType<Record<string, unknown>>,
}

function getElementCenter(el: MimicElement) {
  return {
    x: el.position.x + el.size.width / 2,
    y: el.position.y + el.size.height / 2,
  }
}

export function MimicCanvas({ canvas, elements, connections }: MimicCanvasProps) {
  const elementMap = Object.fromEntries(elements.map((e) => [e.id, e]))

  return (
    <div
      style={{
        position: 'relative',
        width: canvas.width,
        height: canvas.height,
        background: canvas.background ?? 'var(--md-sys-color-surface)',
        overflow: 'hidden',
        borderRadius: 8,
      }}
    >
      <svg
        style={{ position: 'absolute', top: 0, left: 0, pointerEvents: 'none' }}
        width={canvas.width}
        height={canvas.height}
      >
        {connections.map((conn) => {
          const from = elementMap[conn.from]
          const to = elementMap[conn.to]
          if (!from || !to) return null
          const fc = getElementCenter(from)
          const tc = getElementCenter(to)
          const isDuct = conn.style === 'duct'
          return (
            <line
              key={conn.id}
              x1={fc.x}
              y1={fc.y}
              x2={tc.x}
              y2={tc.y}
              stroke={isDuct ? 'var(--md-sys-color-outline)' : 'var(--md-sys-color-tertiary)'}
              strokeWidth={isDuct ? 6 : 3}
              strokeOpacity={0.4}
              strokeDasharray={isDuct ? undefined : '6,3'}
            />
          )
        })}
      </svg>

      {elements.map((el) => {
        const Comp = COMPONENTS[el.type]
        if (!Comp) return null
        return (
          <div
            key={el.id}
            style={{
              position: 'absolute',
              left: el.position.x,
              top: el.position.y,
              width: el.size.width,
              height: el.size.height,
            }}
          >
            <Comp
              width={el.size.width}
              height={el.size.height}
              label={el.label}
              bindings={el.bindings as never}
              display={el.display as never}
              style={el.style as never}
              sensor_type={el.sensor_type as never}
            />
          </div>
        )
      })}
    </div>
  )
}
