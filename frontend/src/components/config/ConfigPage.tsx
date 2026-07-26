import { useState } from 'react'
import { AreasTab } from './AreasTab'
import { DevicesTab } from './DevicesTab'
import { PointsTab } from './PointsTab'
import { UsersTab } from './UsersTab'

type Tab = 'areas' | 'devices' | 'points' | 'users'

const TABS: { id: Tab; label: string }[] = [
  { id: 'areas', label: 'Áreas' },
  { id: 'devices', label: 'Dispositivos' },
  { id: 'points', label: 'Puntos' },
  { id: 'users', label: 'Usuarios' },
]

export default function ConfigPage() {
  const [tab, setTab] = useState<Tab>('areas')

  return (
    <div>
      <h2 style={{ margin: '0 0 20px' }}>Configuración</h2>

      <div style={{ display: 'flex', gap: 4, marginBottom: 24, borderBottom: '1px solid var(--md-sys-color-outline-variant, #333)' }}>
        {TABS.map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            style={{
              background: 'transparent',
              border: 'none',
              borderBottom: tab === t.id ? '2px solid var(--md-sys-color-primary, #00b4d8)' : '2px solid transparent',
              color: tab === t.id ? 'var(--md-sys-color-primary, #00b4d8)' : 'var(--md-sys-color-on-surface, #e0e0e0)',
              padding: '8px 16px',
              cursor: 'pointer',
              fontWeight: tab === t.id ? 600 : 400,
              fontSize: 14,
              marginBottom: -1,
            }}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'areas' && <AreasTab />}
      {tab === 'devices' && <DevicesTab />}
      {tab === 'points' && <PointsTab />}
      {tab === 'users' && <UsersTab />}
    </div>
  )
}
