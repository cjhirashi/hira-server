import { useState, FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { login } from '../../services/api'
import { useAuthStore } from '../../store/authStore'

export default function LoginPage() {
  const navigate = useNavigate()
  const setToken = useAuthStore(s => s.setToken)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      const res = await login(email, password)
      setToken(res.access_token)
      navigate('/', { replace: true })
    } catch {
      setError('Credenciales incorrectas. Verifica tu email y contraseña.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'var(--md-sys-color-background, #0d0d1a)',
        fontFamily: 'sans-serif',
      }}
    >
      <form
        onSubmit={handleSubmit}
        style={{
          background: 'var(--md-sys-color-surface, #1a1a2e)',
          color: 'var(--md-sys-color-on-surface, #e0e0e0)',
          padding: '2.5rem',
          borderRadius: 16,
          width: 360,
          display: 'flex',
          flexDirection: 'column',
          gap: '1.2rem',
          boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
        }}
      >
        <h1 style={{ margin: 0, fontSize: '1.6rem', fontWeight: 700 }}>Hira</h1>
        <p style={{ margin: 0, color: 'var(--md-sys-color-on-surface-variant, #aaa)', fontSize: 14 }}>
          Plataforma SCADA — Iniciar sesión
        </p>

        <label style={{ display: 'flex', flexDirection: 'column', gap: 6, fontSize: 14 }}>
          Email
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoComplete="email"
            style={inputStyle}
          />
        </label>

        <label style={{ display: 'flex', flexDirection: 'column', gap: 6, fontSize: 14 }}>
          Contraseña
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            autoComplete="current-password"
            style={inputStyle}
          />
        </label>

        {error && (
          <p style={{ margin: 0, color: 'var(--hira-alarm-high, #F97316)', fontSize: 13 }}>
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={loading}
          style={{
            padding: '0.8rem',
            background: 'var(--md-sys-color-primary, #00b4d8)',
            color: 'var(--md-sys-color-on-primary, #000)',
            border: 'none',
            borderRadius: 8,
            fontSize: 15,
            fontWeight: 600,
            cursor: loading ? 'not-allowed' : 'pointer',
            opacity: loading ? 0.7 : 1,
          }}
        >
          {loading ? 'Ingresando…' : 'Ingresar'}
        </button>
      </form>
    </div>
  )
}

const inputStyle: React.CSSProperties = {
  padding: '0.6rem 0.8rem',
  background: 'var(--md-sys-color-surface-variant, #2a2a40)',
  color: 'var(--md-sys-color-on-surface, #e0e0e0)',
  border: '1px solid var(--md-sys-color-outline, #444)',
  borderRadius: 8,
  fontSize: 15,
  outline: 'none',
}
