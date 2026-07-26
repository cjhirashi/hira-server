import { useEffect, useState } from 'react'
import { api } from '../../services/api'

interface Area {
  id: number
  name: string
  description: string
  created_at: string
}

interface AreaForm {
  name: string
  description: string
}

const emptyForm: AreaForm = { name: '', description: '' }

export function AreasTab() {
  const [areas, setAreas] = useState<Area[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showForm, setShowForm] = useState(false)
  const [editId, setEditId] = useState<number | null>(null)
  const [form, setForm] = useState<AreaForm>(emptyForm)
  const [saving, setSaving] = useState(false)

  const load = () => {
    setLoading(true)
    api.get<Area[]>('/areas')
      .then(r => setAreas(r.data))
      .catch(() => setError('Error al cargar áreas'))
      .finally(() => setLoading(false))
  }

  useEffect(load, [])

  const openCreate = () => { setEditId(null); setForm(emptyForm); setShowForm(true) }
  const openEdit = (a: Area) => { setEditId(a.id); setForm({ name: a.name, description: a.description }); setShowForm(true) }
  const close = () => { setShowForm(false); setError(null) }

  const save = async () => {
    setSaving(true)
    try {
      if (editId === null) {
        await api.post('/areas', form)
      } else {
        await api.put(`/areas/${editId}`, form)
      }
      close()
      load()
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } }).response?.data?.detail ?? 'Error al guardar'
      setError(msg)
    } finally {
      setSaving(false)
    }
  }

  const remove = async (id: number, name: string) => {
    if (!confirm(`¿Eliminar área "${name}"? Los dispositivos y puntos asociados quedarán sin área.`)) return
    try {
      await api.delete(`/areas/${id}`)
      load()
    } catch {
      setError('Error al eliminar área')
    }
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <h3 style={{ margin: 0 }}>Áreas</h3>
        <button onClick={openCreate} style={btnStyle}>+ Nueva área</button>
      </div>

      {error && <p style={{ color: 'var(--hira-alarm-critical)' }}>{error}</p>}

      {loading ? <p>Cargando...</p> : (
        <table style={tableStyle}>
          <thead>
            <tr>
              <th style={thStyle}>ID</th>
              <th style={thStyle}>Nombre</th>
              <th style={thStyle}>Descripción</th>
              <th style={thStyle}>Acciones</th>
            </tr>
          </thead>
          <tbody>
            {areas.map(a => (
              <tr key={a.id}>
                <td style={tdStyle}>{a.id}</td>
                <td style={tdStyle}>{a.name}</td>
                <td style={tdStyle}>{a.description || '—'}</td>
                <td style={tdStyle}>
                  <button onClick={() => openEdit(a)} style={smallBtnStyle}>Editar</button>
                  <button onClick={() => remove(a.id, a.name)} style={{ ...smallBtnStyle, marginLeft: 8, color: 'var(--hira-alarm-critical)' }}>Eliminar</button>
                </td>
              </tr>
            ))}
            {areas.length === 0 && (
              <tr><td colSpan={4} style={{ ...tdStyle, textAlign: 'center', color: 'var(--md-sys-color-on-surface-variant)' }}>Sin áreas registradas</td></tr>
            )}
          </tbody>
        </table>
      )}

      {showForm && (
        <div style={overlayStyle}>
          <div style={dialogStyle}>
            <h4 style={{ margin: '0 0 16px' }}>{editId ? 'Editar área' : 'Nueva área'}</h4>
            {error && <p style={{ color: 'var(--hira-alarm-critical)', marginTop: 0 }}>{error}</p>}
            <label style={labelStyle}>Nombre *</label>
            <input style={inputStyle} value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} />
            <label style={labelStyle}>Descripción</label>
            <input style={inputStyle} value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} />
            <div style={{ display: 'flex', gap: 8, marginTop: 20, justifyContent: 'flex-end' }}>
              <button onClick={close} style={smallBtnStyle}>Cancelar</button>
              <button onClick={save} disabled={saving || !form.name.trim()} style={btnStyle}>
                {saving ? 'Guardando...' : 'Guardar'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

const tableStyle: React.CSSProperties = { width: '100%', borderCollapse: 'collapse' }
const thStyle: React.CSSProperties = { textAlign: 'left', padding: '8px 12px', borderBottom: '1px solid var(--md-sys-color-outline-variant, #333)', fontWeight: 600, fontSize: 13 }
const tdStyle: React.CSSProperties = { padding: '8px 12px', borderBottom: '1px solid var(--md-sys-color-outline-variant, #2a2a3a)', fontSize: 14 }
const btnStyle: React.CSSProperties = { background: 'var(--md-sys-color-primary, #00b4d8)', color: 'var(--md-sys-color-on-primary, #fff)', border: 'none', borderRadius: 8, padding: '8px 16px', cursor: 'pointer', fontWeight: 600 }
const smallBtnStyle: React.CSSProperties = { background: 'transparent', border: '1px solid var(--md-sys-color-outline, #444)', borderRadius: 6, padding: '4px 10px', cursor: 'pointer', color: 'var(--md-sys-color-on-surface, #e0e0e0)', fontSize: 13 }
const overlayStyle: React.CSSProperties = { position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100 }
const dialogStyle: React.CSSProperties = { background: 'var(--md-sys-color-surface, #1e1e2e)', borderRadius: 12, padding: 24, minWidth: 360, boxShadow: '0 8px 32px rgba(0,0,0,0.4)' }
const labelStyle: React.CSSProperties = { display: 'block', fontSize: 13, marginBottom: 4, color: 'var(--md-sys-color-on-surface-variant, #aaa)' }
const inputStyle: React.CSSProperties = { display: 'block', width: '100%', marginBottom: 12, padding: '8px 10px', background: 'var(--md-sys-color-surface-variant, #2a2a3a)', border: '1px solid var(--md-sys-color-outline, #444)', borderRadius: 6, color: 'var(--md-sys-color-on-surface, #e0e0e0)', fontSize: 14, boxSizing: 'border-box' }
