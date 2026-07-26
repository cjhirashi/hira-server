import { create } from 'zustand'

interface AuthState {
  token: string | null
  roles: string[]
  email: string
  setToken: (token: string | null) => void
  logout: () => void
  hasRole: (role: string) => boolean
  isAdmin: () => boolean
  isOperador: () => boolean
}

function decodeJwtPayload(token: string): Record<string, unknown> {
  try {
    const base64 = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')
    return JSON.parse(atob(base64))
  } catch {
    return {}
  }
}

function extractFromToken(token: string): { roles: string[]; email: string } {
  const payload = decodeJwtPayload(token)
  const role = payload.role as string | undefined
  const roles = role ? [role] : (payload.roles as string[] | undefined) ?? []
  const email = (payload.email as string | undefined) ?? ''
  return { roles, email }
}

const storedToken = localStorage.getItem('hira-token')
const initialExtracted = storedToken ? extractFromToken(storedToken) : { roles: [], email: '' }

export const useAuthStore = create<AuthState>((set, get) => ({
  token: storedToken,
  roles: initialExtracted.roles,
  email: initialExtracted.email,

  setToken: (token) => {
    if (token) {
      localStorage.setItem('hira-token', token)
      const { roles, email } = extractFromToken(token)
      set({ token, roles, email })
    } else {
      localStorage.removeItem('hira-token')
      set({ token: null, roles: [], email: '' })
    }
  },

  logout: () => {
    localStorage.removeItem('hira-token')
    set({ token: null, roles: [], email: '' })
  },

  hasRole: (role) => get().roles.includes(role),
  isAdmin: () => get().roles.includes('Admin'),
  isOperador: () => get().roles.includes('Operador') || get().roles.includes('Admin'),
}))
