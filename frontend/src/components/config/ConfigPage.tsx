import { useState, useEffect } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { AreasTab } from './AreasTab'
import { DevicesTab } from './DevicesTab'
import { PointsTab } from './PointsTab'
import { UsersTab } from './UsersTab'
import { AIConfigForm } from '../ai/AIConfigForm'

type Tab = 'areas' | 'devices' | 'points' | 'users' | 'ia'

const TABS: { id: Tab; label: string }[] = [
  { id: 'areas', label: 'Áreas' },
  { id: 'devices', label: 'Dispositivos' },
  { id: 'points', label: 'Puntos' },
  { id: 'users', label: 'Usuarios' },
  { id: 'ia', label: 'IA' },
]

function tabFromPath(pathname: string): Tab {
  if (pathname.includes('/devices')) return 'devices'
  if (pathname.includes('/points')) return 'points'
  if (pathname.includes('/users')) return 'users'
  if (pathname.includes('/ia')) return 'ia'
  return 'areas'
}

export default function ConfigPage() {
  const location = useLocation()
  const navigate = useNavigate()
  const [tab, setTab] = useState<Tab>(() => tabFromPath(location.pathname))

  useEffect(() => {
    setTab(tabFromPath(location.pathname))
  }, [location.pathname])

  const handleTab = (t: Tab) => {
    setTab(t)
    navigate(`/config/${t === 'areas' ? '' : t}`, { replace: true })
  }

  return (
    <div>
      <h2 style={{ margin: '0 0 20px' }}>Configuración</h2>

      <div style={{ display: 'flex', gap: 4, marginBottom: 24, borderBottom: '1px solid var(--md-sys-color-outline-variant, #333)' }}>
        {TABS.map(t => (
          <button
            key={t.id}
            onClick={() => handleTab(t.id)}
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
      {tab === 'ia' && <AIConfigForm />}
    </div>
  )
}
