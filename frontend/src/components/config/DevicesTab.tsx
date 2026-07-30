import { useEffect, useState } from 'react'
import { api } from '../../services/api'

interface Device {
  id: number
  name: string
  protocol: string
  address: string
  port: number | null
  area: string | null
  status: string
  is_simulator: boolean
  auto_start: boolean
  modbus_unit_id: number | null
  modbus_transport: string | null
  modbus_baudrate: number | null
}

interface DeviceForm {
  name: string
  protocol: string
  address: string
  port: string
  area: string
  auto_start: boolean
  modbus_unit_id: string
  modbus_transport: string
  modbus_baudrate: string
}

const emptyForm: DeviceForm = {
  name: '', protocol: 'bacnet', address: '', port: '', area: '', auto_start: false,
  modbus_unit_id: '1', modbus_transport: 'tcp', modbus_baudrate: '9600',
}

export function DevicesTab() {
  const [devices, setDevices] = useState<Device[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showForm, setShowForm] = useState(false)
  const [editId, setEditId] = useState<number | null>(null)
  const [editProtocol, setEditProtocol] = useState<string>('bacnet')
  const [form, setForm] = useState<DeviceForm>(emptyForm)
  const [saving, setSaving] = useState(false)

  const load = () => {
    setLoading(true)
    api.get<Device[]>('/devices')
      .then(r => setDevices(r.data))
      .catch(() => setError('Error al cargar dispositivos'))
      .finally(() => setLoading(false))
  }

  useEffect(load, [])

  const openCreate = () => { setEditId(null); setEditProtocol('bacnet'); setForm(emptyForm); setError(null); setShowForm(true) }
  const openEdit = (d: Device) => {
    setEditId(d.id)
    setEditProtocol(d.protocol)
    setForm({
      name: d.name, protocol: d.protocol, address: d.address,
      port: d.port?.toString() ?? '', area: d.area ?? '', auto_start: d.auto_start,
      modbus_unit_id: d.modbus_unit_id?.toString() ?? '1',
      modbus_transport: d.modbus_transport ?? 'tcp',
      modbus_baudrate: d.modbus_baudrate?.toString() ?? '9600',
    })
    setError(null)
    setShowForm(true)
  }
  const close = () => { setShowForm(false); setError(null) }

  const currentProtocol = editId !== null ? editProtocol : form.protocol
  const isModbus = currentProtocol === 'modbus'
  const isRtu = isModbus && form.modbus_transport === 'rtu'

  const save = async () => {
    setSaving(true)
    const payload: Record<string, unknown> = {
      name: form.name,
      protocol: form.protocol,
      address: form.address,
      port: form.port ? parseInt(form.port) : null,
      area: form.area || null,
      auto_start: form.auto_start,
    }
    if (isModbus) {
      payload.modbus_unit_id = parseInt(form.modbus_unit_id) || 1
      payload.modbus_transport = form.modbus_transport || 'tcp'
      payload.modbus_baudrate = isRtu ? (parseInt(form.modbus_baudrate) || 9600) : null
    }
    try {
      if (editId === null) {
        await api.post('/devices', payload)
      } else {
        await api.put(`/devices/${editId}`, payload)
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
    if (devices.find(d => d.id === id)?.is_simulator) {
      setError('No se puede eliminar un simulador desde el Configurador')
      return
    }
    if (!confirm(`¿Eliminar dispositivo "${name}" y todos sus puntos?`)) return
    try {
      await api.delete(`/devices/${id}?force=true`)
      load()
    } catch (e: unknown) {
      setError((e as { response?: { data?: { detail?: string } } }).response?.data?.detail ?? 'Error al eliminar')
    }
  }

  const statusColor = (s: string) => {
    if (s === 'online') return 'var(--hira-status-ok)'
    if (s === 'offline') return 'var(--hira-status-offline)'
    return 'var(--hira-alarm-medium)'
  }

  const addressLabel = isModbus
    ? (isRtu ? 'Puerto serial *' : 'Dirección IP:puerto *')
    : 'Dirección *'

  const addressPlaceholder = isModbus
    ? (isRtu ? '/dev/ttyUSB0' : '192.168.1.100:502')
    : '192.168.1.100'

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <h3 style={{ margin: 0 }}>Dispositivos</h3>
        <button onClick={openCreate} style={btnStyle}>+ Nuevo dispositivo</button>
      </div>

      {error && !showForm && <p style={{ color: 'var(--hira-alarm-critical)' }}>{error}</p>}

      {loading ? <p>Cargando...</p> : (
        <table style={tableStyle}>
          <thead>
            <tr>
              {['ID', 'Nombre', 'Protocolo', 'Dirección', 'Estado', 'Área', 'Acciones'].map(h => (
                <th key={h} style={thStyle}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {devices.map(d => (
              <tr key={d.id}>
                <td style={tdStyle}>{d.id}</td>
                <td style={tdStyle}>{d.name}{d.is_simulator && <span style={{ fontSize: 11, marginLeft: 6, color: 'var(--md-sys-color-tertiary, #a78bfa)' }}>SIM</span>}</td>
                <td style={tdStyle}>{d.protocol}</td>
                <td style={tdStyle}>{d.address}{d.port ? `:${d.port}` : ''}</td>
                <td style={tdStyle}><span style={{ color: statusColor(d.status) }}>{d.status}</span></td>
                <td style={tdStyle}>{d.area || '—'}</td>
                <td style={tdStyle}>
                  <button onClick={() => openEdit(d)} style={smallBtnStyle}>Editar</button>
                  {!d.is_simulator && (
                    <button onClick={() => remove(d.id, d.name)} style={{ ...smallBtnStyle, marginLeft: 8, color: 'var(--hira-alarm-critical)' }}>Eliminar</button>
                  )}
                </td>
              </tr>
            ))}
            {devices.length === 0 && (
              <tr><td colSpan={7} style={{ ...tdStyle, textAlign: 'center' }}>Sin dispositivos registrados</td></tr>
            )}
          </tbody>
        </table>
      )}

      {showForm && (
        <div style={overlayStyle}>
          <div style={dialogStyle}>
            <h4 style={{ margin: '0 0 16px' }}>{editId ? 'Editar dispositivo' : 'Nuevo dispositivo'}</h4>
            {error && <p style={{ color: 'var(--hira-alarm-critical)', marginTop: 0 }}>{error}</p>}

            <label style={labelStyle}>Nombre *</label>
            <input style={inputStyle} value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} />

            {editId === null && (
              <>
                <label style={labelStyle}>Protocolo *</label>
                <select style={inputStyle} value={form.protocol} onChange={e => setForm(f => ({ ...f, protocol: e.target.value }))}>
                  <option value="bacnet">BACnet</option>
                  <option value="modbus">Modbus</option>
                  <option value="mqtt">MQTT</option>
                </select>
              </>
            )}

            {isModbus && (
              <>
                <label style={labelStyle}>Transporte *</label>
                <select style={inputStyle} value={form.modbus_transport} onChange={e => setForm(f => ({ ...f, modbus_transport: e.target.value }))}>
                  <option value="tcp">TCP</option>
                  <option value="rtu">RTU (serial)</option>
                </select>
              </>
            )}

            <label style={labelStyle}>{addressLabel}</label>
            <input style={inputStyle} value={form.address} onChange={e => setForm(f => ({ ...f, address: e.target.value }))} placeholder={addressPlaceholder} />

            {!isModbus && (
              <>
                <label style={labelStyle}>Puerto</label>
                <input style={inputStyle} type="number" value={form.port} onChange={e => setForm(f => ({ ...f, port: e.target.value }))} placeholder="Opcional" />
              </>
            )}

            {isModbus && (
              <>
                <label style={labelStyle}>Unit ID (1–247) *</label>
                <input style={inputStyle} type="number" min="1" max="247" value={form.modbus_unit_id} onChange={e => setForm(f => ({ ...f, modbus_unit_id: e.target.value }))} />

                {isRtu && (
                  <>
                    <label style={labelStyle}>Baudrate</label>
                    <select style={inputStyle} value={form.modbus_baudrate} onChange={e => setForm(f => ({ ...f, modbus_baudrate: e.target.value }))}>
                      {['1200', '2400', '4800', '9600', '19200', '38400', '57600', '115200'].map(b => (
                        <option key={b} value={b}>{b}</option>
                      ))}
                    </select>
                  </>
                )}
              </>
            )}

            <label style={labelStyle}>Área</label>
            <input style={inputStyle} value={form.area} onChange={e => setForm(f => ({ ...f, area: e.target.value }))} placeholder="Piso 3 — Sala de máquinas" />

            <label style={{ ...labelStyle, display: 'flex', alignItems: 'center', gap: 8, marginBottom: 0 }}>
              <input type="checkbox" checked={form.auto_start} onChange={e => setForm(f => ({ ...f, auto_start: e.target.checked }))} />
              Auto-start al arrancar servidor
            </label>

            <div style={{ display: 'flex', gap: 8, marginTop: 20, justifyContent: 'flex-end' }}>
              <button onClick={close} style={smallBtnStyle}>Cancelar</button>
              <button onClick={save} disabled={saving || !form.name.trim() || !form.address.trim()} style={btnStyle}>
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
const dialogStyle: React.CSSProperties = { background: 'var(--md-sys-color-surface, #1e1e2e)', borderRadius: 12, padding: 24, minWidth: 380, boxShadow: '0 8px 32px rgba(0,0,0,0.4)', maxHeight: '90vh', overflowY: 'auto' }
const labelStyle: React.CSSProperties = { display: 'block', fontSize: 13, marginBottom: 4, color: 'var(--md-sys-color-on-surface-variant, #aaa)' }
const inputStyle: React.CSSProperties = { display: 'block', width: '100%', marginBottom: 12, padding: '8px 10px', background: 'var(--md-sys-color-surface-variant, #2a2a3a)', border: '1px solid var(--md-sys-color-outline, #444)', borderRadius: 6, color: 'var(--md-sys-color-on-surface, #e0e0e0)', fontSize: 14, boxSizing: 'border-box' }
