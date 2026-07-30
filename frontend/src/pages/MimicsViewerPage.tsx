import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  ReactFlow,
  useNodesState,
  useEdgesState,
  Background,
  Controls,
  Handle,
  Position,
  type Node,
  type Edge,
  type NodeProps,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { ArrowLeft, Maximize2, Minimize2 } from 'lucide-react'
import { api } from '../services/api'
import { Fan } from '../svg/hvac/Fan'
import { Damper } from '../svg/hvac/Damper'
import { Valve } from '../svg/hvac/Valve'
import { Chiller } from '../svg/hvac/Chiller'
import { AHU } from '../svg/hvac/AHU'
import { Sensor } from '../svg/hvac/Sensor'
import { Setpoint } from '../svg/hvac/Setpoint'
import { useWebSocket, type WsMessage } from '../hooks/useWebSocket'
import { usePointsStore } from '../store/pointsStore'

// ── Types ─────────────────────────────────────────────────────────────────────

interface MimicNodeData {
  label: string
  point_id: number | null
  [key: string]: unknown
}

// ── Read-only custom nodes (read values from global store) ────────────────────

function makeViewerNode(
  Comp: React.ComponentType<{ width?: number; height?: number; label?: string; bindings?: Record<string, { point_id: number } | undefined> }>,
  defaultW: number,
  defaultH: number,
) {
  return function ViewerNode({ data }: NodeProps) {
    const d = data as MimicNodeData
    const bindings = d.point_id ? { running: { point_id: d.point_id } } : undefined
    return (
      <div style={{ borderRadius: 6, background: 'var(--bg-surface)', padding: 2 }}>
        <Handle type="target" position={Position.Left} style={{ background: 'var(--accent)' }} />
        <Comp width={defaultW} height={defaultH} label={d.label || undefined} bindings={bindings as never} />
        <Handle type="source" position={Position.Right} style={{ background: 'var(--accent)' }} />
      </div>
    )
  }
}

const ViewerSensorNode = ({ data }: NodeProps) => {
  const d = data as MimicNodeData
  const bindings = d.point_id ? { value: { point_id: d.point_id } } : undefined
  return (
    <div style={{ borderRadius: 6, background: 'var(--bg-surface)', padding: 2 }}>
      <Handle type="target" position={Position.Left} style={{ background: 'var(--accent)' }} />
      <Sensor width={80} height={80} label={d.label || undefined} bindings={bindings as never} />
      <Handle type="source" position={Position.Right} style={{ background: 'var(--accent)' }} />
    </div>
  )
}

const ViewerSetpointNode = ({ data }: NodeProps) => {
  const d = data as MimicNodeData
  const bindings = d.point_id ? { value: { point_id: d.point_id } } : undefined
  return (
    <div style={{ borderRadius: 6, background: 'var(--bg-surface)', padding: 2 }}>
      <Handle type="target" position={Position.Left} style={{ background: 'var(--accent)' }} />
      <Setpoint width={80} height={80} label={d.label || undefined} bindings={bindings as never} />
      <Handle type="source" position={Position.Right} style={{ background: 'var(--accent)' }} />
    </div>
  )
}

const viewerNodeTypes = {
  fan: makeViewerNode(Fan as never, 80, 80),
  damper: makeViewerNode(Damper as never, 100, 60),
  valve: makeViewerNode(Valve as never, 80, 80),
  chiller: makeViewerNode(Chiller as never, 160, 100),
  ahu: makeViewerNode(AHU as never, 160, 100),
  sensor: ViewerSensorNode,
  setpoint: ViewerSetpointNode,
}

// ── Viewer ─────────────────────────────────────────────────────────────────────

export default function MimicsViewerPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [mimicName, setMimicName] = useState('')
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([])
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([])
  const [fullscreen, setFullscreen] = useState(false)
  const updatePoint = usePointsStore(s => s.updatePoint)
  const containerRef = useRef<HTMLDivElement>(null)

  // Load mimic
  useEffect(() => {
    if (!id) return
    api.get<{ id: number; name: string; canvas: { nodes?: Node[]; edges?: Edge[] } | null }>(`/mimics/${id}`)
      .then(res => {
        setMimicName(res.data.name)
        const canvas = res.data.canvas
        if (canvas?.nodes) setNodes(canvas.nodes)
        if (canvas?.edges) setEdges(canvas.edges)
      })
  }, [id])

  // WebSocket — update pointsStore (same as DashboardPage)
  const handleWsMessage = useCallback((msg: WsMessage) => {
    if (msg.event === 'point_update') {
      const pt = msg.data as { id: number; name: string; value: number | null; unit: string | null; quality: 'good' | 'uncertain' | 'bad'; timestamp: string }
      updatePoint(pt)
    }
  }, [updatePoint])

  useWebSocket({ onMessage: handleWsMessage })

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      containerRef.current?.requestFullscreen()
      setFullscreen(true)
    } else {
      document.exitFullscreen()
      setFullscreen(false)
    }
  }

  useEffect(() => {
    const handler = () => setFullscreen(!!document.fullscreenElement)
    document.addEventListener('fullscreenchange', handler)
    return () => document.removeEventListener('fullscreenchange', handler)
  }, [])

  return (
    <div ref={containerRef} style={{ display: 'flex', flexDirection: 'column', height: '100%', background: 'var(--bg-canvas)' }}>
      {/* Header */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 12, padding: '10px 16px',
        background: 'var(--bg-surface)', borderBottom: '1px solid var(--border-subtle)',
        flexShrink: 0,
      }}>
        <button
          onClick={() => navigate('/mimics')}
          style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: 4 }}
        >
          <ArrowLeft size={16} /> Dashboard
        </button>
        <span style={{ color: 'var(--border-subtle)' }}>|</span>
        <span style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: 'var(--text-base)' }}>
          {mimicName}
        </span>
        <div style={{ flex: 1 }} />
        <button
          onClick={toggleFullscreen}
          title={fullscreen ? 'Salir de pantalla completa' : 'Pantalla completa'}
          style={{
            background: 'var(--accent-subtle)', border: 'none', borderRadius: 'var(--radius-sm)',
            padding: '5px 8px', cursor: 'pointer', color: 'var(--accent)',
            display: 'flex', alignItems: 'center',
          }}
        >
          {fullscreen ? <Minimize2 size={15} /> : <Maximize2 size={15} />}
        </button>
      </div>

      {/* Read-only React Flow canvas */}
      <div style={{ flex: 1, overflow: 'hidden' }}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          nodeTypes={viewerNodeTypes}
          nodesDraggable={false}
          nodesConnectable={false}
          elementsSelectable={false}
          fitView
          style={{ background: 'var(--bg-canvas)' }}
        >
          <Background color="var(--border-subtle)" gap={20} />
          <Controls showInteractive={false} />
        </ReactFlow>
      </div>
    </div>
  )
}
