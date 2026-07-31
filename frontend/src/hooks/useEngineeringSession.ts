import { useEffect, useState } from 'react'
import { useAuthStore } from '../store/authStore'

export interface ActiveSession {
  session_id: number
  engineer_user_id: number
  engineer_name: string
  started_at: string
  expires_at: string
  last_heartbeat_at: string
}

export function useEngineeringSession(): ActiveSession | null {
  const [session, setSession] = useState<ActiveSession | null>(null)
  const token = useAuthStore((s) => s.token)

  useEffect(() => {
    if (!token) return

    const fetchSession = async () => {
      try {
        const res = await fetch('/api/v1/engineering-sessions/active', {
          headers: { Authorization: `Bearer ${token}` },
        })
        if (res.ok) {
          setSession(await res.json())
        } else {
          setSession(null)
        }
      } catch {
        // silencioso — no romper UI si el backend no responde
      }
    }

    fetchSession()
    const interval = setInterval(fetchSession, 30_000)
    window.addEventListener('engineering-session-closed', fetchSession)
    return () => {
      clearInterval(interval)
      window.removeEventListener('engineering-session-closed', fetchSession)
    }
  }, [token])

  return session
}
