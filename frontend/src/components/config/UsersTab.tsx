import { useEffect, useState } from 'react'
import { api } from '../../services/api'

interface User {
  id: number
  email: string
  full_name: string | null
  role_id: number
  role_name: string
  is_active: boolean
  created_at: string
}

interface UserCreateForm {
  email: string
  full_name: string
  password: string
  role_id: string
}

interface UserEditForm {
  full_name: string
  role_id: string
}

const emptyCreate: UserCreateForm = { email: '', full_name: '', password: '', role_id: '2' }
const emptyEdit: UserEditForm = { full_name: '', role_id: '2' }

export function UsersTab() {
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [mode, setMode] = useState<'create' | 'edit' | null>(null)
  const [editId, setEditId] = useState<number | null>(null)
  const [createForm, setCreateForm] = useState<UserCreateForm>(emptyCreate)
  const [editForm, setEditForm] = useState<UserEditForm>(emptyEdit)
  const [saving, setSaving] = useState(false)

  const load = () => {
    setLoading(true)
    api.get<User[]>('/users')
      .then(r => setUsers(r.data))
      .catch(() => setError('Error al cargar usuarios'))
      .finally(() => setLoading(false))
  }

  useEffect(load, [])

  const openCreate = () => { setMode('create'); setCreateForm(emptyCreate); setError(null) }
  const openEdit = (u: User) => { setMode('edit'); setEditId(u.id); setEditForm({ full_name: u.full_name ?? '', role_id: u.role_id.toString() }); setError(null) }
  const close = () => { setMode(null); setEditId(null); setError(null) }

  const saveCreate = async () => {
    setSaving(true)
    try {
      await api.post('/users', { email: createForm.email, full_name: createForm.full_name || null, password: createForm.password, role_id: parseInt(createForm.role_id) })
      close(); load()
    } catch (e: unknown) {
      setError((e as { response?: { data?: { detail?: string } } }).response?.data?.detail ?? 'Error al crear')
    } finally { setSaving(false) }
  }

  const saveEdit = async () => {
    setSaving(true)
    try {
      await api.patch(`/users/${editId}`, { full_name: editForm.full_name || null, role_id: parseInt(editForm.role_id) })
      close(); load()
    } catch (e: unknown) {
      setError((e as { response?: { data?: { detail?: string } } }).response?.data?.detail ?? 'Error al actualizar')
    } finally { setSaving(false) }
  }

  const disable = async (u: User) => {
    if (!confirm(`¿Desactivar usuario "${u.email}"?`)) return
    try {
      await api.patch(`/users/${u.id}/disable`)
      load()
    } catch (e: unknown) {
      setError((e as { response?: { data?: { detail?: string } } }).response?.data?.detail ?? 'Error al desactivar')
    }
  }

  const ROLES = [{ id: 1, name: 'Admin' }, { id: 2, name: 'Operador' }, { id: 3, name: 'Visor' }]

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <h3 style={{ margin: 0 }}>Usuarios</h3>
        <button onClick={openCreate} style={btnStyle}>+ Nuevo usuario</button>
      </div>

      {error && !mode && <p style={{ color: 'var(--hira-alarm-critical)' }}>{error}</p>}

      {loading ? <p>Cargando...</p> : (
        <table style={tableStyle}>
          <thead>
            <tr>
              {['ID', 'Email', 'Nombre', 'Rol', 'Estado', 'Acciones'].map(h => (
                <th key={h} style={thStyle}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {users.map(u => (
              <tr key={u.id} style={{ opacity: u.is_active ? 1 : 0.5 }}>
                <td style={tdStyle}>{u.id}</td>
                <td style={tdStyle}>{u.email}</td>
                <td style={tdStyle}>{u.full_name || '—'}</td>
                <td style={tdStyle}>{u.role_name}</td>
                <td style={tdStyle}>
                  <span style={{ color: u.is_active ? 'var(--hira-status-ok)' : 'var(--hira-status-offline)' }}>
                    {u.is_active ? 'Activo' : 'Inactivo'}
                  </span>
                </td>
                <td style={tdStyle}>
                  <button onClick={() => openEdit(u)} style={smallBtnStyle}>Editar</button>
                  {u.is_active && (
                    <button onClick={() => disable(u)} style={{ ...smallBtnStyle, marginLeft: 8, color: 'var(--hira-alarm-medium)' }}>Desactivar</button>
                  )}
                </td>
              </tr>
            ))}
            {users.length === 0 && (
              <tr><td colSpan={6} style={{ ...tdStyle, textAlign: 'center' }}>Sin usuarios</td></tr>
            )}
          </tbody>
        </table>
      )}

      {mode === 'create' && (
        <div style={overlayStyle}>
          <div style={dialogStyle}>
            <h4 style={{ margin: '0 0 16px' }}>Nuevo usuario</h4>
            {error && <p style={{ color: 'var(--hira-alarm-critical)', marginTop: 0 }}>{error}</p>}

            <label style={labelStyle}>Email *</label>
            <input style={inputStyle} type="email" value={createForm.email} onChange={e => setCreateForm(f => ({ ...f, email: e.target.value }))} />

            <label style={labelStyle}>Nombre completo</label>
            <input style={inputStyle} value={createForm.full_name} onChange={e => setCreateForm(f => ({ ...f, full_name: e.target.value }))} />

            <label style={labelStyle}>Contraseña *</label>
            <input style={inputStyle} type="password" value={createForm.password} onChange={e => setCreateForm(f => ({ ...f, password: e.target.value }))} />

            <label style={labelStyle}>Rol *</label>
            <select style={inputStyle} value={createForm.role_id} onChange={e => setCreateForm(f => ({ ...f, role_id: e.target.value }))}>
              {ROLES.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}
            </select>

            <div style={{ display: 'flex', gap: 8, marginTop: 16, justifyContent: 'flex-end' }}>
              <button onClick={close} style={smallBtnStyle}>Cancelar</button>
              <button onClick={saveCreate} disabled={saving || !createForm.email.trim() || createForm.password.length < 8} style={btnStyle}>
                {saving ? 'Creando...' : 'Crear'}
              </button>
            </div>
          </div>
        </div>
      )}

      {mode === 'edit' && (
        <div style={overlayStyle}>
          <div style={dialogStyle}>
            <h4 style={{ margin: '0 0 16px' }}>Editar usuario</h4>
            {error && <p style={{ color: 'var(--hira-alarm-critical)', marginTop: 0 }}>{error}</p>}

            <label style={labelStyle}>Nombre completo</label>
            <input style={inputStyle} value={editForm.full_name} onChange={e => setEditForm(f => ({ ...f, full_name: e.target.value }))} />

            <label style={labelStyle}>Rol</label>
            <select style={inputStyle} value={editForm.role_id} onChange={e => setEditForm(f => ({ ...f, role_id: e.target.value }))}>
              {ROLES.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}
            </select>

            <div style={{ display: 'flex', gap: 8, marginTop: 16, justifyContent: 'flex-end' }}>
              <button onClick={close} style={smallBtnStyle}>Cancelar</button>
              <button onClick={saveEdit} disabled={saving} style={btnStyle}>
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
