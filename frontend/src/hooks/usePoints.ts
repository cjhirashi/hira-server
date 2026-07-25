import { usePointsStore, type PointValue } from '../store/pointsStore'
import { useWebSocket, type WsMessage } from './useWebSocket'

export function usePoints() {
  const { points, updatePoint } = usePointsStore()

  const handleMessage = (msg: WsMessage) => {
    if (msg.event === 'point:update') {
      updatePoint(msg.data as PointValue)
    }
  }

  const { send } = useWebSocket({ onMessage: handleMessage })

  const subscribePoints = (pointIds: number[]) => {
    send({ event: 'subscribe:points', data: { point_ids: pointIds } })
  }

  const unsubscribePoints = (pointIds: number[]) => {
    send({ event: 'unsubscribe:points', data: { point_ids: pointIds } })
  }

  return { points, subscribePoints, unsubscribePoints }
}
