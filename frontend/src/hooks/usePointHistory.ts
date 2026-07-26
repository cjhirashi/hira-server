import { useEffect, useState } from 'react'
import { api } from '../services/api'

export interface PointHistoryRecord {
  timestamp: string
  value: number
  quality: 'good' | 'bad' | 'uncertain'
}

export interface PointHistoryResponse {
  point_id: number
  point_name: string
  unit: string | null
  from_dt: string
  to_dt: string
  interval: string
  records: PointHistoryRecord[]
  count: number
}

export type HistoryInterval = 'raw' | '1min' | '5min' | '1hour' | '1day'

interface UsePointHistoryParams {
  pointId: number | null
  fromDt: string
  toDt: string
  interval: HistoryInterval
  limit?: number
}

export function usePointHistory({ pointId, fromDt, toDt, interval, limit = 1000 }: UsePointHistoryParams) {
  const [data, setData] = useState<PointHistoryResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!pointId) {
      setData(null)
      return
    }

    let cancelled = false
    setLoading(true)
    setError(null)

    api
      .get<PointHistoryResponse>(`/points/${pointId}/history`, {
        params: { from_dt: fromDt, to_dt: toDt, interval, limit, format: 'json' },
      })
      .then((res) => {
        if (!cancelled) setData(res.data)
      })
      .catch((err) => {
        if (!cancelled) setError(err.response?.data?.detail ?? 'Error al cargar histórico')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [pointId, fromDt, toDt, interval, limit])

  return { data, loading, error }
}
