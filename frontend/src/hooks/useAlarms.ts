import { useEffect } from 'react'
import { api } from '../services/api'
import { useAlarmsStore, type AlarmEvent } from '../store/alarmsStore'
import { useWebSocket, type WsMessage } from './useWebSocket'

export function useAlarms() {
  const { addAlarm, acknowledgeAlarm, resolveAlarm, setActive } = useAlarmsStore()

  useEffect(() => {
    api.get<AlarmEvent[]>('/alarms').then((r) => setActive(r.data)).catch(() => {})
  }, [setActive])

  const handleMessage = (msg: WsMessage) => {
    if (msg.event === 'alarm:new') {
      addAlarm(msg.data as AlarmEvent)
    } else if (msg.event === 'alarm:resolved') {
      const d = msg.data as { alarm_id: number; resolved_at: string }
      resolveAlarm(d.alarm_id, d.resolved_at)
    } else if (msg.event === 'alarm:acknowledged') {
      const d = msg.data as { alarm_id: number; acknowledged_by: string; acknowledged_at: string }
      acknowledgeAlarm(d.alarm_id, d.acknowledged_by, d.acknowledged_at)
    }
  }

  useWebSocket({ onMessage: handleMessage })

  const activeAlarms = useAlarmsStore((s) => s.activeAlarms)
  const unacknowledgedCount = useAlarmsStore((s) => s.unacknowledgedCount())

  async function acknowledge(id: number) {
    await api.post(`/alarms/${id}/acknowledge`)
  }

  return { activeAlarms, unacknowledgedCount, acknowledge }
}
