import { Outlet, NavLink } from 'react-router-dom'
import { useAlarmsStore } from '../../store/alarmsStore'

const NAV_ITEMS = [
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/alarms', label: 'Alarmas', badge: true },
  { to: '/history', label: 'Históricos' },
  { to: '/config', label: 'Configuración' },
  { to: '/logic', label: 'Lógica' },
  { to: '/ai', label: 'IA' },
]

export default function Shell() {
  const unacknowledged = useAlarmsStore((s) => s.unacknowledgedCount())

  return (
    <div style={{ display: 'flex', height: '100vh', fontFamily: 'sans-serif' }}>
      <nav
        style={{
          width: 200,
          background: 'var(--md-sys-color-surface, #1a1a2e)',
          color: 'var(--md-sys-color-on-surface, #e0e0e0)',
          display: 'flex',
          flexDirection: 'column',
          padding: '1rem 0',
          gap: 4,
        }}
      >
        <div style={{ padding: '0 1rem 1rem', fontWeight: 700, fontSize: '1.2rem' }}>
          Hira
        </div>
        {NAV_ITEMS.map(({ to, label, badge }) => (
          <NavLink
            key={to}
            to={to}
            style={({ isActive }) => ({
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '0.6rem 1rem',
              textDecoration: 'none',
              color: isActive
                ? 'var(--md-sys-color-primary, #00b4d8)'
                : 'var(--md-sys-color-on-surface, #e0e0e0)',
              background: isActive ? 'rgba(0,180,216,0.12)' : 'transparent',
              borderRadius: 8,
              margin: '0 8px',
            })}
          >
            <span>{label}</span>
            {badge && unacknowledged > 0 && (
              <span style={{
                background: 'var(--hira-alarm-critical)',
                color: '#fff',
                borderRadius: 10,
                padding: '1px 6px',
                fontSize: 11,
                fontWeight: 700,
                minWidth: 18,
                textAlign: 'center',
              }}>
                {unacknowledged}
              </span>
            )}
          </NavLink>
        ))}
      </nav>
      <main style={{ flex: 1, overflow: 'auto', padding: '2rem' }}>
        <Outlet />
      </main>
    </div>
  )
}
