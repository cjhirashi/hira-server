import { useState } from 'react'
import { useAuthStore } from '../store/authStore'
import { useEngineeringSession } from '../hooks/useEngineeringSession'

export default function EngineeringSessionBanner() {
  const session = useEngineeringSession()
  const isAdmin = useAuthStore((s) => s.isAdmin())
  const token = useAuthStore((s) => s.token)
  const [closing, setClosing] = useState(false)

  if (!session) return null

  const handleClose = async () => {
    if (!token || closing) return
    setClosing(true)
    try {
      await fetch(`/api/v1/engineering-sessions/${session.session_id}/close`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      })
      // El hook se actualizará en el próximo polling (máx 30s)
      // Forzamos recarga inmediata disparando un re-render
      window.dispatchEvent(new Event('engineering-session-closed'))
    } catch {
      // silencioso
    } finally {
      setClosing(false)
    }
  }

  const expiresAt = new Date(session.expires_at).toLocaleTimeString()
  const startedAt = new Date(session.started_at).toLocaleTimeString()

  return (
    <div style={{
      position: 'sticky',
      top: 0,
      zIndex: 1000,
      background: '#d97706',
      color: '#ffffff',
      padding: '8px 16px',
      display: 'flex',
      alignItems: 'center',
      gap: 12,
      flexWrap: 'wrap',
      fontSize: 'var(--text-sm)',
      fontWeight: 500,
      boxShadow: '0 2px 4px rgba(0,0,0,0.3)',
    }}>
      <span style={{ fontSize: 16 }}>⚠️</span>
      <span style={{ flex: 1, minWidth: 200 }}>
        <strong>SESIÓN DE INGENIERÍA ACTIVA</strong>
        {' — '}
        Ingeniero: <strong>{session.engineer_name}</strong>
        {' | '}
        Iniciada: {startedAt}
        {' | '}
        Expira: {expiresAt}
      </span>
      {isAdmin && (
        <button
          onClick={handleClose}
          disabled={closing}
          style={{
            padding: '4px 12px',
            borderRadius: 4,
            border: '1px solid rgba(255,255,255,0.6)',
            background: 'rgba(255,255,255,0.15)',
            color: '#ffffff',
            cursor: closing ? 'not-allowed' : 'pointer',
            fontSize: 'var(--text-xs)',
            fontWeight: 600,
            whiteSpace: 'nowrap',
          }}
        >
          {closing ? 'Cerrando…' : 'Cerrar Sesión'}
        </button>
      )}
    </div>
  )
}
