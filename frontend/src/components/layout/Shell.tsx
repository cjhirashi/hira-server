import { Outlet, NavLink } from 'react-router-dom'

const NAV_ITEMS = [
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/alarms', label: 'Alarmas' },
  { to: '/history', label: 'Históricos' },
  { to: '/config', label: 'Configuración' },
  { to: '/logic', label: 'Lógica' },
  { to: '/ai', label: 'IA' },
]

export default function Shell() {
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
        {NAV_ITEMS.map(({ to, label }) => (
          <NavLink
            key={to}
            to={to}
            style={({ isActive }) => ({
              display: 'block',
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
            {label}
          </NavLink>
        ))}
      </nav>
      <main style={{ flex: 1, overflow: 'auto', padding: '2rem' }}>
        <Outlet />
      </main>
    </div>
  )
}
