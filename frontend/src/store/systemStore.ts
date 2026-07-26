import { create } from 'zustand'

interface SystemState {
  mode: 'server' | 'studio' | null
  dbType: 'postgresql' | 'sqlite' | null
  version: string
  fetchMode: () => Promise<void>
}

export const useSystemStore = create<SystemState>((set) => ({
  mode: null,
  dbType: null,
  version: '',

  fetchMode: async () => {
    try {
      const res = await fetch('/api/v1/system/mode')
      if (res.ok) {
        const data = await res.json()
        set({ mode: data.mode, dbType: data.db_type, version: data.version ?? '' })
      }
    } catch {
      // silencioso — no crítico
    }
  },
}))
