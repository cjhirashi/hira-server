import { useEffect, useState } from 'react'
import { api } from '../../services/api'

interface Device { id: number; name: string; protocol: string }
interface Area { id: number; name: string }

interface Point {
  id: number
  device_id: number
  name: string
  description: string
  object_type: string
  address: string
  unit: string
  writable: boolean
  log_enabled: boolean
  history_interval_seconds: number
  area_id: number | null
  area_name: string | null
  modbus_register_type: string | null
  modbus_data_type: string | null
}

interface PointForm {
  device_id: string
  name: string
  description: string
  object_type: string
  address: string
  unit: string
  writable: boolean
  log_enabled: boolean
  history_interval_seconds: string
  area_id: string
  modbus_register_type: string
  modbus_data_type: string
}

const emptyForm: PointForm = {
  device_id: '', name: '', description: '', object_type: '', address: '',
  unit: '', writable: false, log_enabled: false, history_interval_seconds: '60', area_id: '',
  modbus_register_type: 'holding_register', modbus_data_type: 'uint16',
}

export function PointsTab() {
  const [points, setPoints] = useState<Point[]>([])
  const [devices, setDevices] = useState<Device[]>([])
  const [areas, setAreas] = useState<Area[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showForm, setShowForm] = useState(false)
  const [editId, setEditId] = useState<number | null>(null)
  const [editDeviceProtocol, setEditDeviceProtocol] = useState<string>('')
  const [form, setForm] = useState<PointForm>(emptyForm)
  const [saving, setSaving] = useState(false)
  const [deviceFilter, setDeviceFilter] = useState<string>('')

  const loadAll = async () => {
    setLoading(true)
    try {
      const [dRes, aRes] = await Promise.all([
        api.get<Device[]>('/devices'),
        api.get<Area[]>('/areas'),
      ])
      setDevices(dRes.data)
      setAreas(aRes.data)

      const allPoints: Point[] = []
      for (const d of dRes.data) {
        const ptsRes = await api.get<{ id: number; name: string; unit: string | null }[]>(`/devices/${d.id}/points`)
        for (const p of ptsRes.data) {
          try {
            const full = await api.get<Point>(`/points/${p.id}`)
            allPoints.push(full.data)
          } catch {
            // skip if no full endpoint yet
          }
        }
      }
      setPoints(allPoints)
    } catch {
      setError('Error al cargar puntos')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadAll() }, [])

  const selectedDeviceProtocol = (deviceId: string) =>
    devices.find(d => d.id.toString() === deviceId)?.protocol ?? ''

  const openCreate = () => { setEditId(null); setEditDeviceProtocol(''); setForm(emptyForm); setError(null); setShowForm(true) }
  const openEdit = (p: Point) => {
    const proto = devices.find(d => d.id === p.device_id)?.protocol ?? ''
    setEditId(p.id)
    setEditDeviceProtocol(proto)
    setForm({
      device_id: p.device_id.toString(),
      name: p.name, description: p.description,
      object_type: p.object_type, address: p.address, unit: p.unit,
      writable: p.writable, log_enabled: p.log_enabled,
      history_interval_seconds: p.history_interval_seconds.toString(),
      area_id: p.area_id?.toString() ?? '',
      modbus_register_type: p.modbus_register_type ?? 'holding_register',
      modbus_data_type: p.modbus_data_type ?? 'uint16',
    })
    setError(null)
    setShowForm(true)
  }
  const close = () => { setShowForm(false); setError(null) }

  const currentProtocol = editId !== null
    ? editDeviceProtocol
    : selectedDeviceProtocol(form.device_id)
  const isModbus = currentProtocol === 'modbus'

  const save = async () => {
    setSaving(true)
    const base = {
      name: form.name, description: form.description,
      unit: form.unit, writable: form.writable, log_enabled: form.log_enabled,
      history_interval_seconds: parseInt(form.history_interval_seconds) || 60,
      area_id: form.area_id ? parseInt(form.area_id) : null,
    }
    const modbusFields = isModbus ? {
      modbus_register_type: form.modbus_register_type || null,
      modbus_data_type: form.modbus_data_type || null,
    } : {}

    try {
      if (editId === null) {
        await api.post('/points', {
          ...base,
          ...modbusFields,
          device_id: parseInt(form.device_id),
          object_type: form.object_type,
          address: form.address,
        })
      } else {
        await api.put(`/points/${editId}`, { ...base, ...modbusFields })
      }
      close()
      loadAll()
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } }).response?.data?.detail ?? 'Error al guardar'
      setError(msg)
    } finally {
      setSaving(false)
    }
  }

  const remove = async (id: number, name: string) => {
    if (!confirm(`¿Eliminar punto "${name}" y su historial?`)) return
    try {
      await api.delete(`/points/${id}`)
      loadAll()
    } catch {
      setError('Error al eliminar punto')
    }
  }

  const filtered = deviceFilter
    ? points.filter(p => p.device_id.toString() === deviceFilter)
    : points

  const deviceName = (id: number) => devices.find(d => d.id === id)?.name ?? `#${id}`

  const addressLabel = isModbus ? 'Dirección de Registro *' : 'Dirección *'
  const addressPlaceholder = isModbus ? '0, 1, 100, ...' : 'AI:0, 400001, ...'

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <h3 style={{ margin: 0 }}>Puntos</h3>
          <select style={{ ...inputStyle, marginBottom: 0, width: 'auto', minWidth: 160 }} value={deviceFilter} onChange={e => setDeviceFilter(e.target.value)}>
            <option value="">Todos los dispositivos</option>
            {devices.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
          </select>
        </div>
        <button onClick={openCreate} style={btnStyle}>+ Nuevo punto</button>
      </div>

      {error && !showForm && <p style={{ color: 'var(--hira-alarm-critical)' }}>{error}</p>}

      {loading ? <p>Cargando...</p> : (
        <div style={{ overflowX: 'auto' }}>
          <table style={tableStyle}>
            <thead>
              <tr>
                {['ID', 'Dispositivo', 'Nombre', 'Tipo', 'Dirección', 'Unidad', 'Área', 'Acciones'].map(h => (
                  <th key={h} style={thStyle}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map(p => (
                <tr key={p.id}>
                  <td style={tdStyle}>{p.id}</td>
                  <td style={tdStyle}>{deviceName(p.device_id)}</td>
                  <td style={tdStyle}>{p.name}</td>
                  <td style={tdStyle}>{p.object_type}</td>
                  <td style={tdStyle}>{p.address}</td>
                  <td style={tdStyle}>{p.unit || '—'}</td>
                  <td style={tdStyle}>{p.area_name || '—'}</td>
                  <td style={tdStyle}>
                    <button onClick={() => openEdit(p)} style={smallBtnStyle}>Editar</button>
                    <button onClick={() => remove(p.id, p.name)} style={{ ...smallBtnStyle, marginLeft: 8, color: 'var(--hira-alarm-critical)' }}>Eliminar</button>
                  </td>
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr><td colSpan={8} style={{ ...tdStyle, textAlign: 'center' }}>Sin puntos registrados</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {showForm && (
        <div style={overlayStyle}>
          <div style={dialogStyle}>
            <h4 style={{ margin: '0 0 16px' }}>{editId ? 'Editar punto' : 'Nuevo punto'}</h4>
            {error && <p style={{ color: 'var(--hira-alarm-critical)', marginTop: 0 }}>{error}</p>}

            {editId === null && (
              <>
                <label style={labelStyle}>Dispositivo *</label>
                <select style={inputStyle} value={form.device_id} onChange={e => setForm(f => ({ ...f, device_id: e.target.value }))}>
                  <option value="">Seleccionar...</option>
                  {devices.map(d => <option key={d.id} value={d.id}>{d.name} ({d.protocol})</option>)}
                </select>
              </>
            )}

            <label style={labelStyle}>Nombre *</label>
            <input style={inputStyle} value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} />

            <label style={labelStyle}>Descripción</label>
            <input style={inputStyle} value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} />

            {editId === null && (
              <>
                {!isModbus && (
                  <>
                    <label style={labelStyle}>Tipo de objeto *</label>
                    <input style={inputStyle} value={form.object_type} onChange={e => setForm(f => ({ ...f, object_type: e.target.value }))} placeholder="analogInput, binaryOutput, ..." />
                  </>
                )}

                <label style={labelStyle}>{addressLabel}</label>
                <input style={inputStyle} value={form.address} onChange={e => setForm(f => ({ ...f, address: e.target.value }))} placeholder={addressPlaceholder} />

                {isModbus && (
                  <>
                    <label style={labelStyle}>Tipo de Registro *</label>
                    <select style={inputStyle} value={form.modbus_register_type} onChange={e => setForm(f => ({ ...f, modbus_register_type: e.target.value }))}>
                      <option value="holding_register">Holding Register (FC03/FC06)</option>
                      <option value="input_register">Input Register (FC04, solo lectura)</option>
                      <option value="coil">Coil (FC01/FC05)</option>
                      <option value="discrete_input">Discrete Input (FC02, solo lectura)</option>
                    </select>

                    <label style={labelStyle}>Tipo de Dato *</label>
                    <select style={inputStyle} value={form.modbus_data_type} onChange={e => setForm(f => ({ ...f, modbus_data_type: e.target.value }))}>
                      <option value="uint16">uint16 (entero sin signo)</option>
                      <option value="int16">int16 (entero con signo)</option>
                      <option value="float32">float32 (IEEE 754, 2 registros)</option>
                      <option value="bool">bool</option>
                    </select>
                  </>
                )}
              </>
            )}

            {editId !== null && isModbus && (
              <>
                <label style={labelStyle}>Tipo de Registro</label>
                <select style={inputStyle} value={form.modbus_register_type} onChange={e => setForm(f => ({ ...f, modbus_register_type: e.target.value }))}>
                  <option value="holding_register">Holding Register (FC03/FC06)</option>
                  <option value="input_register">Input Register (FC04, solo lectura)</option>
                  <option value="coil">Coil (FC01/FC05)</option>
                  <option value="discrete_input">Discrete Input (FC02, solo lectura)</option>
                </select>

                <label style={labelStyle}>Tipo de Dato</label>
                <select style={inputStyle} value={form.modbus_data_type} onChange={e => setForm(f => ({ ...f, modbus_data_type: e.target.value }))}>
                  <option value="uint16">uint16 (entero sin signo)</option>
                  <option value="int16">int16 (entero con signo)</option>
                  <option value="float32">float32 (IEEE 754, 2 registros)</option>
                  <option value="bool">bool</option>
                </select>
              </>
            )}

            <label style={labelStyle}>Unidad</label>
            <input style={inputStyle} value={form.unit} onChange={e => setForm(f => ({ ...f, unit: e.target.value }))} placeholder="°C, %, kWh, ..." />

            <label style={labelStyle}>Intervalo histórico (segundos)</label>
            <input style={inputStyle} type="number" min="1" value={form.history_interval_seconds} onChange={e => setForm(f => ({ ...f, history_interval_seconds: e.target.value }))} />

            <label style={labelStyle}>Área</label>
            <select style={inputStyle} value={form.area_id} onChange={e => setForm(f => ({ ...f, area_id: e.target.value }))}>
              <option value="">Sin área</option>
              {areas.map(a => <option key={a.id} value={a.id}>{a.name}</option>)}
            </select>

            <div style={{ display: 'flex', gap: 16, marginBottom: 12 }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13 }}>
                <input type="checkbox" checked={form.writable} onChange={e => setForm(f => ({ ...f, writable: e.target.checked }))} />
                Escribible
              </label>
              <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13 }}>
                <input type="checkbox" checked={form.log_enabled} onChange={e => setForm(f => ({ ...f, log_enabled: e.target.checked }))} />
                Habilitar log
              </label>
            </div>

            <div style={{ display: 'flex', gap: 8, marginTop: 16, justifyContent: 'flex-end' }}>
              <button onClick={close} style={smallBtnStyle}>Cancelar</button>
              <button
                onClick={save}
                disabled={saving || !form.name.trim() || (editId === null && (!form.device_id || (!isModbus && !form.object_type.trim()) || !form.address.trim()))}
                style={btnStyle}
              >
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
const thStyle: React.CSSProperties = { textAlign: 'left', padding: '8px 12px', borderBottom: '1px solid var(--md-sys-color-outline-variant, #333)', fontWeight: 600, fontSize: 13, whiteSpace: 'nowrap' }
const tdStyle: React.CSSProperties = { padding: '8px 12px', borderBottom: '1px solid var(--md-sys-color-outline-variant, #2a2a3a)', fontSize: 14 }
const btnStyle: React.CSSProperties = { background: 'var(--md-sys-color-primary, #00b4d8)', color: 'var(--md-sys-color-on-primary, #fff)', border: 'none', borderRadius: 8, padding: '8px 16px', cursor: 'pointer', fontWeight: 600 }
const smallBtnStyle: React.CSSProperties = { background: 'transparent', border: '1px solid var(--md-sys-color-outline, #444)', borderRadius: 6, padding: '4px 10px', cursor: 'pointer', color: 'var(--md-sys-color-on-surface, #e0e0e0)', fontSize: 13 }
const overlayStyle: React.CSSProperties = { position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100 }
const dialogStyle: React.CSSProperties = { background: 'var(--md-sys-color-surface, #1e1e2e)', borderRadius: 12, padding: 24, minWidth: 400, maxWidth: 480, boxShadow: '0 8px 32px rgba(0,0,0,0.4)', maxHeight: '90vh', overflowY: 'auto' }
const labelStyle: React.CSSProperties = { display: 'block', fontSize: 13, marginBottom: 4, color: 'var(--md-sys-color-on-surface-variant, #aaa)' }
const inputStyle: React.CSSProperties = { display: 'block', width: '100%', marginBottom: 12, padding: '8px 10px', background: 'var(--md-sys-color-surface-variant, #2a2a3a)', border: '1px solid var(--md-sys-color-outline, #444)', borderRadius: 6, color: 'var(--md-sys-color-on-surface, #e0e0e0)', fontSize: 14, boxSizing: 'border-box' }
