import { useEffect, useRef, useCallback } from 'react'

export interface WsMessage {
  event: string
  data: unknown
}

type MessageHandler = (msg: WsMessage) => void

interface UseWebSocketOptions {
  onMessage?: MessageHandler
  enabled?: boolean
}

const BASE_DELAY_MS = 1000
const MAX_DELAY_MS = 30000

export function useWebSocket({ onMessage, enabled = true }: UseWebSocketOptions = {}) {
  const wsRef = useRef<WebSocket | null>(null)
  const retryRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const delayRef = useRef(BASE_DELAY_MS)
  const mountedRef = useRef(true)
  const onMessageRef = useRef(onMessage)
  onMessageRef.current = onMessage

  const connect = useCallback(() => {
    if (!mountedRef.current) return
    const token = localStorage.getItem('hira-token')
    if (!token) return

    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const url = `${protocol}://${window.location.host}/ws?token=${token}`
    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => {
      delayRef.current = BASE_DELAY_MS
    }

    ws.onmessage = (ev) => {
      try {
        const msg: WsMessage = JSON.parse(ev.data as string)
        onMessageRef.current?.(msg)
      } catch {
        // ignore parse errors
      }
    }

    ws.onclose = () => {
      if (!mountedRef.current) return
      const delay = delayRef.current
      delayRef.current = Math.min(delay * 2, MAX_DELAY_MS)
      retryRef.current = setTimeout(connect, delay)
    }

    ws.onerror = () => {
      ws.close()
    }
  }, [])

  useEffect(() => {
    mountedRef.current = true
    if (enabled) connect()
    return () => {
      mountedRef.current = false
      if (retryRef.current) clearTimeout(retryRef.current)
      wsRef.current?.close()
    }
  }, [enabled, connect])

  const send = useCallback((msg: WsMessage) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(msg))
    }
  }, [])

  return { send }
}
