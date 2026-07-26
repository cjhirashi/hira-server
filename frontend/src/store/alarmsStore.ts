import { create } from 'zustand'

export interface AlarmEvent {
  id: number
  alarm_definition_id: number
  point_id: number
  point_name: string
  triggered_value: number
  priority: 'critical' | 'high' | 'medium' | 'low'
  message: string
  status: 'active' | 'acknowledged' | 'resolved'
  triggered_at: string
  acknowledged_at: string | null
  acknowledged_by: string | null
  resolved_at: string | null
}

interface AlarmsState {
  activeAlarms: Record<number, AlarmEvent>
  addAlarm: (alarm: AlarmEvent) => void
  acknowledgeAlarm: (id: number, by: string, at: string) => void
  resolveAlarm: (id: number, at: string) => void
  setActive: (alarms: AlarmEvent[]) => void
  unacknowledgedCount: () => number
}

export const useAlarmsStore = create<AlarmsState>((set, get) => ({
  activeAlarms: {},

  addAlarm: (alarm) =>
    set((s) => ({ activeAlarms: { ...s.activeAlarms, [alarm.id]: alarm } })),

  acknowledgeAlarm: (id, by, at) =>
    set((s) => {
      const existing = s.activeAlarms[id]
      if (!existing) return s
      return {
        activeAlarms: {
          ...s.activeAlarms,
          [id]: { ...existing, status: 'acknowledged', acknowledged_by: by, acknowledged_at: at },
        },
      }
    }),

  resolveAlarm: (id, at) =>
    set((s) => {
      const next = { ...s.activeAlarms }
      delete next[id]
      return { activeAlarms: next }
    }),

  setActive: (alarms) =>
    set(() => ({
      activeAlarms: Object.fromEntries(alarms.map((a) => [a.id, a])),
    })),

  unacknowledgedCount: () =>
    Object.values(get().activeAlarms).filter((a) => a.status === 'active').length,
}))
