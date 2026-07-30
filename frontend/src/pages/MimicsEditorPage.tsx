import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  ReactFlow,
  addEdge,
  useNodesState,
  useEdgesState,
  Background,
  Controls,
  MiniMap,
  Handle,
  Position,
  type Connection,
  type Node,
  type Edge,
  type NodeProps,
  type ReactFlowInstance,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { ArrowLeft, Save, Loader2 } from 'lucide-react'
import { api } from '../services/api'
import { Fan } from '../svg/hvac/Fan'
import { Damper } from '../svg/hvac/Damper'
import { Valve } from '../svg/hvac/Valve'
import { Chiller } from '../svg/hvac/Chiller'
import { AHU } from '../svg/hvac/AHU'
import { Sensor } from '../svg/hvac/Sensor'
import { Setpoint } from '../svg/hvac/Setpoint'
import { usePointsStore } from '../store/pointsStore'

// ── Types ─────────────────────────────────────────────────────────────────────

interface PointOption { id: number; name: string }

interface MimicNodeData {
  label: string
  point_id: number | null
  [key: string]: unknown
}

// ── Custom Nodes ───────────────────────────────────────────────────────────────

function makeHvacNode(
  Comp: React.ComponentType<{ width?: number; height?: number; label?: string; bindings?: Record<string, { point_id: number } | undefined> }>,
  defaultW: number,
  defaultH: number,
) {
  return function HvacNode({ data, selected }: NodeProps) {
    const d = data as MimicNodeData
    const bindings = d.point_id ? { running: { point_id: d.point_id } } : undefined
    return (
      <div style={{
        border: selected ? '2px solid var(--accent)' : '2px solid transparent',
        borderRadius: 6,
        background: 'var(--bg-surface)',
        padding: 2,
      }}>
        <Handle type="target" position={Position.Left} style={{ background: 'var(--accent)' }} />
        <Comp width={defaultW} height={defaultH} label={d.label || undefined} bindings={bindings as never} />
        <Handle type="source" position={Position.Right} style={{ background: 'var(--accent)' }} />
      </div>
    )
  }
}

const SensorNode = ({ data, selected }: NodeProps) => {
  const d = data as MimicNodeData
  const bindings = d.point_id ? { value: { point_id: d.point_id } } : undefined
  return (
    <div style={{
      border: selected ? '2px solid var(--accent)' : '2px solid transparent',
      borderRadius: 6, background: 'var(--bg-surface)', padding: 2,
    }}>
      <Handle type="target" position={Position.Left} style={{ background: 'var(--accent)' }} />
      <Sensor width={80} height={80} label={d.label || undefined} bindings={bindings as never} />
      <Handle type="source" position={Position.Right} style={{ background: 'var(--accent)' }} />
    </div>
  )
}

const SetpointNode = ({ data, selected }: NodeProps) => {
  const d = data as MimicNodeData
  const bindings = d.point_id ? { value: { point_id: d.point_id } } : undefined
  return (
    <div style={{
      border: selected ? '2px solid var(--accent)' : '2px solid transparent',
      borderRadius: 6, background: 'var(--bg-surface)', padding: 2,
    }}>
      <Handle type="target" position={Position.Left} style={{ background: 'var(--accent)' }} />
      <Setpoint width={80} height={80} label={d.label || undefined} bindings={bindings as never} />
      <Handle type="source" position={Position.Right} style={{ background: 'var(--accent)' }} />
    </div>
  )
}

const nodeTypes = {
  fan: makeHvacNode(Fan as never, 80, 80),
  damper: makeHvacNode(Damper as never, 100, 60),
  valve: makeHvacNode(Valve as never, 80, 80),
  chiller: makeHvacNode(Chiller as never, 160, 100),
  ahu: makeHvacNode(AHU as never, 160, 100),
  sensor: SensorNode,
  setpoint: SetpointNode,
}

const TOOLBAR_ITEMS = [
  { type: 'fan', label: 'Fan' },
  { type: 'damper', label: 'Damper' },
  { type: 'valve', label: 'Valve' },
  { type: 'chiller', label: 'Chiller' },
  { type: 'ahu', label: 'AHU' },
  { type: 'sensor', label: 'Sensor' },
  { type: 'setpoint', label: 'Setpoint' },
]

// ── Editor ─────────────────────────────────────────────────────────────────────

export default function MimicsEditorPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [mimicName, setMimicName] = useState('')
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([])
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([])
  const [rfInstance, setRfInstance] = useState<ReactFlowInstance | null>(null)
  const [selectedNode, setSelectedNode] = useState<Node | null>(null)
  const [saving, setSaving] = useState(false)
  const [savedAt, setSavedAt] = useState<string | null>(null)
  const [points, setPoints] = useState<PointOption[]>([])
  const autoSaveRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const hasChanges = useRef(false)

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

  // Load points for binding dropdown
  useEffect(() => {
    api.get<{ id: number; name: string }[]>('/points')
      .then(res => setPoints(res.data.map(p => ({ id: p.id, name: p.name }))))
      .catch(() => {})
  }, [])

  const handleSave = useCallback(async () => {
    if (!id || !rfInstance) return
    setSaving(true)
    try {
      const flow = rfInstance.toObject()
      await api.put(`/mimics/${id}`, { name: mimicName, canvas: { nodes: flow.nodes, edges: flow.edges } })
      setSavedAt(new Date().toLocaleTimeString())
      hasChanges.current = false
    } finally {
      setSaving(false)
    }
  }, [id, mimicName, rfInstance])

  // Auto-save every 30s if there are changes
  useEffect(() => {
    autoSaveRef.current = setInterval(() => {
      if (hasChanges.current) handleSave()
    }, 30000)
    return () => { if (autoSaveRef.current) clearInterval(autoSaveRef.current) }
  }, [handleSave])

  const onConnect = useCallback(
    (params: Connection) => {
      setEdges(eds => addEdge(params, eds))
      hasChanges.current = true
    },
    [setEdges],
  )

  const onDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.dataTransfer.dropEffect = 'move'
  }, [])

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    if (!rfInstance) return
    const type = e.dataTransfer.getData('application/reactflow')
    if (!type) return
    const position = rfInstance.screenToFlowPosition({ x: e.clientX, y: e.clientY })
    const newNode: Node = {
      id: `${type}-${Date.now()}`,
      type,
      position,
      data: { label: type.toUpperCase(), point_id: null },
    }
    setNodes(nds => nds.concat(newNode))
    hasChanges.current = true
  }, [rfInstance, setNodes])

  const onNodeClick = useCallback((_: React.MouseEvent, node: Node) => {
    setSelectedNode(node)
  }, [])

  const onPaneClick = useCallback(() => {
    setSelectedNode(null)
  }, [])

  const updateSelectedNodeData = (updates: Partial<MimicNodeData>) => {
    if (!selectedNode) return
    setNodes((nds: Node[]) => nds.map(n => n.id === selectedNode.id
      ? { ...n, data: { ...n.data, ...updates } }
      : n,
    ))
    setSelectedNode(prev => prev ? { ...prev, data: { ...prev.data, ...updates } } : null)
    hasChanges.current = true
  }

  const deleteSelectedNode = () => {
    if (!selectedNode) return
    setNodes((nds: Node[]) => nds.filter(n => n.id !== selectedNode.id))
    setEdges((eds: Edge[]) => eds.filter(e => e.source !== selectedNode.id && e.target !== selectedNode.id))
    setSelectedNode(null)
    hasChanges.current = true
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: 'var(--bg-canvas)' }}>
      {/* Header */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 12, padding: '10px 16px',
        background: 'var(--bg-surface)', borderBottom: '1px solid var(--border-subtle)',
        flexShrink: 0,
      }}>
        <button
          onClick={() => navigate('/studio/mimics')}
          style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: 4 }}
        >
          <ArrowLeft size={16} /> Volver
        </button>
        <span style={{ color: 'var(--border-subtle)' }}>|</span>
        <input
          value={mimicName}
          onChange={e => { setMimicName(e.target.value); hasChanges.current = true }}
          style={{
            background: 'transparent', border: 'none', borderBottom: '1px solid var(--border-subtle)',
            color: 'var(--text-primary)', fontSize: 'var(--text-base)', fontWeight: 600,
            padding: '2px 4px', outline: 'none', minWidth: 200,
          }}
        />
        <div style={{ flex: 1 }} />
        {savedAt && (
          <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Guardado {savedAt}</span>
        )}
        <button
          onClick={handleSave}
          disabled={saving}
          style={{
            display: 'flex', alignItems: 'center', gap: 6,
            background: 'var(--accent)', color: '#fff',
            border: 'none', borderRadius: 'var(--radius-md)',
            padding: '6px 14px', fontSize: 'var(--text-sm)', fontWeight: 600,
            cursor: saving ? 'wait' : 'pointer', opacity: saving ? 0.7 : 1,
          }}
        >
          {saving ? <Loader2 size={14} className="spin" /> : <Save size={14} />}
          Guardar
        </button>
      </div>

      {/* Toolbar */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 6, padding: '6px 16px',
        background: 'var(--bg-surface)', borderBottom: '1px solid var(--border-subtle)',
        flexShrink: 0,
      }}>
        <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', marginRight: 4 }}>COMPONENTES:</span>
        {TOOLBAR_ITEMS.map(item => (
          <div
            key={item.type}
            draggable
            onDragStart={e => { e.dataTransfer.setData('application/reactflow', item.type); e.dataTransfer.effectAllowed = 'move' }}
            style={{
              padding: '4px 10px', borderRadius: 'var(--radius-sm)',
              background: 'var(--accent-subtle)', color: 'var(--accent)',
              fontSize: 11, fontWeight: 600, cursor: 'grab',
              border: '1px solid color-mix(in srgb, var(--accent) 30%, transparent)',
              userSelect: 'none',
            }}
          >
            {item.label}
          </div>
        ))}
      </div>

      {/* Canvas + Properties panel */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        {/* React Flow Canvas */}
        <div style={{ flex: 1, position: 'relative' }} onDrop={onDrop} onDragOver={onDragOver}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={(changes) => { onNodesChange(changes); hasChanges.current = true }}
            onEdgesChange={(changes) => { onEdgesChange(changes); hasChanges.current = true }}
            onConnect={onConnect}
            onInit={setRfInstance}
            onNodeClick={onNodeClick}
            onPaneClick={onPaneClick}
            nodeTypes={nodeTypes}
            fitView
            style={{ background: 'var(--bg-canvas)' }}
          >
            <Background color="var(--border-subtle)" gap={20} />
            <Controls />
            <MiniMap style={{ background: 'var(--bg-surface)' }} />
          </ReactFlow>
        </div>

        {/* Properties panel */}
        {selectedNode && (
          <div style={{
            width: 260, borderLeft: '1px solid var(--border-subtle)',
            background: 'var(--bg-surface)', padding: 16,
            display: 'flex', flexDirection: 'column', gap: 12, flexShrink: 0,
            overflowY: 'auto',
          }}>
            <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
              Propiedades del nodo
            </div>

            <div>
              <label style={{ fontSize: 11, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>Tipo</label>
              <div style={{ fontSize: 'var(--text-sm)', color: 'var(--text-primary)', fontWeight: 600, textTransform: 'uppercase' }}>
                {selectedNode.type}
              </div>
            </div>

            <div>
              <label style={{ fontSize: 11, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>Nombre / Etiqueta</label>
              <input
                value={(selectedNode.data as MimicNodeData).label ?? ''}
                onChange={e => updateSelectedNodeData({ label: e.target.value })}
                style={{
                  width: '100%', padding: '5px 8px', boxSizing: 'border-box',
                  borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)',
                  background: 'var(--bg-canvas)', color: 'var(--text-primary)', fontSize: 'var(--text-sm)',
                }}
              />
            </div>

            <div>
              <label style={{ fontSize: 11, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>Punto vinculado</label>
              <select
                value={(selectedNode.data as MimicNodeData).point_id ?? ''}
                onChange={e => updateSelectedNodeData({ point_id: e.target.value ? Number(e.target.value) : null })}
                style={{
                  width: '100%', padding: '5px 8px', boxSizing: 'border-box',
                  borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)',
                  background: 'var(--bg-canvas)', color: 'var(--text-primary)', fontSize: 'var(--text-sm)',
                }}
              >
                <option value="">Sin vinculación</option>
                {points.map(p => (
                  <option key={p.id} value={p.id}>{p.name}</option>
                ))}
              </select>
            </div>

            <button
              onClick={deleteSelectedNode}
              style={{
                background: 'var(--danger-subtle)', color: 'var(--danger)',
                border: '1px solid color-mix(in srgb, var(--danger) 30%, transparent)',
                borderRadius: 'var(--radius-sm)', padding: '6px 12px',
                fontSize: 'var(--text-sm)', fontWeight: 600, cursor: 'pointer',
                marginTop: 'auto',
              }}
            >
              Eliminar nodo
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
