import { useEffect } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import {
  LayoutDashboard, Bell, BarChart2, Settings,
  Code2, Sparkles, LogOut, Zap, Wrench, Activity, FlaskConical, type LucideIcon,
} from 'lucide-react'
import { useAlarmsStore } from '../../store/alarmsStore'
import { useAuthStore } from '../../store/authStore'
import { useSystemStore } from '../../store/systemStore'

const navItemBase: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 10,
  padding: '7px 12px',
  borderRadius: 'var(--radius-md)',
  margin: '1px 8px',
  textDecoration: 'none',
  fontSize: 'var(--text-sm)',
  fontWeight: 500,
  cursor: 'pointer',
  transition: 'background 120ms, color 120ms',
  border: 'none',
  width: 'calc(100% - 16px)',
  background: 'transparent',
}

function NavItem({ to, label, Icon, badge }: { to: string; label: string; Icon: LucideIcon; badge?: boolean }) {
  const unacknowledged = useAlarmsStore(s => s.unacknowledgedCount())
  return (
    <NavLink
      to={to}
      style={({ isActive }) => ({
        ...navItemBase,
        color: isActive ? 'var(--accent)' : 'var(--text-secondary)',
        background: isActive ? 'var(--accent-subtle)' : 'transparent',
        borderLeft: isActive ? '2px solid var(--accent)' : '2px solid transparent',
        paddingLeft: isActive ? 10 : 12,
      })}
      onMouseEnter={e => {
        const el = e.currentTarget
        if (!el.getAttribute('aria-current')) {
          el.style.background = 'var(--bg-hover)'
          el.style.color = 'var(--text-primary)'
        }
      }}
      onMouseLeave={e => {
        const el = e.currentTarget
        if (!el.getAttribute('aria-current')) {
          el.style.background = ''
          el.style.color = 'var(--text-secondary)'
        }
      }}
    >
      <Icon size={16} strokeWidth={1.8} style={{ flexShrink: 0 }} />
      <span style={{ flex: 1 }}>{label}</span>
      {badge && unacknowledged > 0 && (
        <span style={{
          background: 'var(--danger)',
          color: '#fff',
          borderRadius: 10,
          padding: '1px 6px',
          fontSize: 10,
          fontWeight: 700,
          minWidth: 18,
          textAlign: 'center',
          lineHeight: '16px',
        }}>
          {unacknowledged}
        </span>
      )}
    </NavLink>
  )
}

function SectionLabel({ label, icon: Icon }: { label: string; icon?: LucideIcon }) {
  return (
    <div style={{
      padding: '8px 16px 4px',
      fontSize: 10,
      fontWeight: 600,
      color: 'var(--text-muted)',
      letterSpacing: '0.1em',
      textTransform: 'uppercase',
      display: 'flex',
      alignItems: 'center',
      gap: 5,
    }}>
      {Icon && <Icon size={11} color="var(--accent)" />}
      {label}
    </div>
  )
}

export default function Sidebar() {
  const navigate = useNavigate()
  const { email, isAdmin, isOperador, logout } = useAuthStore()
  const { mode, dbType, fetchMode } = useSystemStore()

  useEffect(() => { fetchMode() }, [fetchMode])

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const adminUser = isAdmin()
  const operadorOrAdmin = isOperador()

  return (
    <nav style={{
      width: 'var(--sidebar-width)',
      minWidth: 'var(--sidebar-width)',
      height: '100vh',
      background: 'var(--bg-surface)',
      borderRight: '1px solid var(--border-subtle)',
      display: 'flex',
      flexDirection: 'column',
      flexShrink: 0,
      overflow: 'hidden',
    }}>
      {/* Logo */}
      <div style={{
        padding: '14px 16px 12px',
        borderBottom: '1px solid var(--border-subtle)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{
            width: 30,
            height: 30,
            borderRadius: 'var(--radius-md)',
            background: 'var(--accent-subtle)',
            border: '1px solid var(--accent)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
          }}>
            <Zap size={16} color="var(--accent)" strokeWidth={2.5} />
          </div>
          <div>
            <div style={{ fontSize: 'var(--text-base)', fontWeight: 700, color: 'var(--accent)', lineHeight: 1.1 }}>
              Hira
            </div>
            <div style={{ fontSize: 10, color: 'var(--text-muted)', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
              SCADA
            </div>
          </div>
        </div>
        {/* Studio / Server mode badge */}
        {mode === 'studio' && (
          <div style={{
            marginTop: 8,
            display: 'inline-flex',
            alignItems: 'center',
            gap: 4,
            background: 'rgba(234,179,8,0.12)',
            color: '#d29922',
            borderRadius: 10,
            padding: '2px 8px',
            fontSize: 10,
            fontWeight: 600,
          }}>
            Studio · SQLite
          </div>
        )}
        {mode === 'server' && (
          <div style={{
            marginTop: 8,
            display: 'inline-flex',
            alignItems: 'center',
            gap: 4,
            background: 'var(--success-subtle)',
            color: 'var(--success)',
            borderRadius: 10,
            padding: '2px 8px',
            fontSize: 10,
            fontWeight: 600,
          }}>
            Server · {dbType === 'postgresql' ? 'PostgreSQL' : dbType}
          </div>
        )}
      </div>

      {/* Nav */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '8px 0' }}>
        {/* SCADA Operativo — visible para todos */}
        <SectionLabel label="SCADA Operativo" />
        <NavItem to="/dashboard" label="Dashboard" Icon={LayoutDashboard} />
        <NavItem to="/alarms" label="Alarmas" Icon={Bell} badge />
        <NavItem to="/history" label="Históricos" Icon={BarChart2} />
        {operadorOrAdmin && (
          <NavItem to="/ai/cliente" label="AI Asistente" Icon={Sparkles} />
        )}
        {operadorOrAdmin && (
          <NavItem to="/system/status" label="Estado del Sistema" Icon={Activity} />
        )}

        {/* Hira Studio — solo Admin */}
        {adminUser && (
          <>
            <div style={{ borderTop: '1px solid var(--border-subtle)', margin: '8px 0 4px' }} />
            <SectionLabel label="Hira Studio" icon={Wrench} />
            <NavItem to="/config" label="Configuración" Icon={Settings} />
            <NavItem to="/logic" label="Lógica" Icon={Code2} />
            <NavItem to="/ai/integrador" label="AI Integrador" Icon={Sparkles} />
            <NavItem to="/studio/notifications" label="Notificaciones" Icon={Bell} />
            <NavItem to="/tests" label="Pruebas" Icon={FlaskConical} />
          </>
        )}
      </div>

      {/* Footer */}
      <div style={{
        borderTop: '1px solid var(--border-subtle)',
        padding: '10px 8px',
        display: 'flex',
        flexDirection: 'column',
        gap: 4,
      }}>
        {email && (
          <div style={{
            padding: '4px 8px',
            fontSize: 'var(--text-xs)',
            color: 'var(--text-muted)',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}>
            {email}
          </div>
        )}
        <button
          onClick={handleLogout}
          style={{ ...navItemBase, margin: 0, width: '100%', color: 'var(--text-secondary)' }}
          onMouseEnter={e => {
            e.currentTarget.style.background = 'var(--danger-subtle)'
            e.currentTarget.style.color = 'var(--danger)'
          }}
          onMouseLeave={e => {
            e.currentTarget.style.background = ''
            e.currentTarget.style.color = 'var(--text-secondary)'
          }}
        >
          <LogOut size={15} strokeWidth={1.8} />
          <span>Salir</span>
        </button>
      </div>
    </nav>
  )
}
