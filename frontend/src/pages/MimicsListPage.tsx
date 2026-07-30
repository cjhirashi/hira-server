import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus, LayoutTemplate, Pencil, Trash2 } from 'lucide-react'
import { api } from '../services/api'

interface MimicSummary {
  id: number
  name: string
  description: string | null
  updated_at: string
}

export default function MimicsListPage() {
  const navigate = useNavigate()
  const [mimics, setMimics] = useState<MimicSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [creating, setCreating] = useState(false)
  const [newName, setNewName] = useState('')
  const [showCreate, setShowCreate] = useState(false)

  const load = async () => {
    try {
      const res = await api.get<MimicSummary[]>('/mimics')
      setMimics(res.data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const handleCreate = async () => {
    if (!newName.trim()) return
    setCreating(true)
    try {
      const res = await api.post<MimicSummary>('/mimics', { name: newName.trim(), canvas: { nodes: [], edges: [] } })
      navigate(`/studio/mimics/${res.data.id}`)
    } finally {
      setCreating(false)
    }
  }

  const handleDelete = async (id: number, name: string) => {
    if (!confirm(`¿Eliminar mimic "${name}"?`)) return
    await api.delete(`/mimics/${id}`)
    setMimics(m => m.filter(x => x.id !== id))
  }

  return (
    <div style={{ padding: '24px 32px', maxWidth: 900 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <LayoutTemplate size={22} color="var(--accent)" />
          <h1 style={{ fontSize: 'var(--text-xl)', fontWeight: 700, color: 'var(--text-primary)', margin: 0 }}>
            Mimics
          </h1>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          style={{
            display: 'flex', alignItems: 'center', gap: 6,
            background: 'var(--accent)', color: '#fff',
            border: 'none', borderRadius: 'var(--radius-md)',
            padding: '7px 14px', fontSize: 'var(--text-sm)', fontWeight: 600,
            cursor: 'pointer',
          }}
        >
          <Plus size={15} /> Nuevo Mimic
        </button>
      </div>

      {showCreate && (
        <div style={{
          background: 'var(--bg-surface)',
          border: '1px solid var(--border-subtle)',
          borderRadius: 'var(--radius-lg)',
          padding: 16, marginBottom: 16,
          display: 'flex', gap: 10, alignItems: 'center',
        }}>
          <input
            autoFocus
            value={newName}
            onChange={e => setNewName(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter') handleCreate(); if (e.key === 'Escape') setShowCreate(false) }}
            placeholder="Nombre del mimic…"
            style={{
              flex: 1, padding: '6px 10px', borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--border-subtle)', background: 'var(--bg-canvas)',
              color: 'var(--text-primary)', fontSize: 'var(--text-sm)',
            }}
          />
          <button
            onClick={handleCreate}
            disabled={creating || !newName.trim()}
            style={{
              background: 'var(--accent)', color: '#fff', border: 'none',
              borderRadius: 'var(--radius-sm)', padding: '6px 14px',
              fontSize: 'var(--text-sm)', fontWeight: 600, cursor: 'pointer',
              opacity: creating || !newName.trim() ? 0.6 : 1,
            }}
          >
            {creating ? 'Creando…' : 'Crear'}
          </button>
          <button
            onClick={() => setShowCreate(false)}
            style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', fontSize: 20, lineHeight: 1 }}
          >
            ×
          </button>
        </div>
      )}

      {loading ? (
        <div style={{ color: 'var(--text-muted)', fontSize: 'var(--text-sm)' }}>Cargando…</div>
      ) : mimics.length === 0 ? (
        <div style={{
          textAlign: 'center', padding: '48px 0',
          color: 'var(--text-muted)', fontSize: 'var(--text-sm)',
        }}>
          No hay mimics. Crea uno con el botón de arriba.
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {mimics.map(m => (
            <div
              key={m.id}
              style={{
                background: 'var(--bg-surface)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-lg)',
                padding: '12px 16px',
                display: 'flex', alignItems: 'center', gap: 12,
              }}
            >
              <LayoutTemplate size={18} color="var(--accent)" style={{ flexShrink: 0 }} />
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: 'var(--text-sm)' }}>
                  {m.name}
                </div>
                {m.description && (
                  <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', marginTop: 2 }}>
                    {m.description}
                  </div>
                )}
                <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 2 }}>
                  Actualizado: {new Date(m.updated_at).toLocaleString()}
                </div>
              </div>
              <button
                onClick={() => navigate(`/studio/mimics/${m.id}`)}
                title="Editar"
                style={{
                  background: 'var(--accent-subtle)', border: 'none', borderRadius: 'var(--radius-sm)',
                  padding: '5px 8px', cursor: 'pointer', color: 'var(--accent)',
                  display: 'flex', alignItems: 'center', gap: 4, fontSize: 'var(--text-xs)',
                }}
              >
                <Pencil size={13} /> Editar
              </button>
              <button
                onClick={() => navigate(`/mimics/${m.id}`)}
                title="Ver en tiempo real"
                style={{
                  background: 'var(--success-subtle)', border: 'none', borderRadius: 'var(--radius-sm)',
                  padding: '5px 8px', cursor: 'pointer', color: 'var(--success)',
                  display: 'flex', alignItems: 'center', gap: 4, fontSize: 'var(--text-xs)',
                }}
              >
                <LayoutTemplate size={13} /> Ver
              </button>
              <button
                onClick={() => handleDelete(m.id, m.name)}
                title="Eliminar"
                style={{
                  background: 'none', border: 'none', borderRadius: 'var(--radius-sm)',
                  padding: '5px 8px', cursor: 'pointer', color: 'var(--danger)',
                  display: 'flex', alignItems: 'center',
                }}
              >
                <Trash2 size={14} />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
