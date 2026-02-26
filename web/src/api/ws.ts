import { ref, onUnmounted } from 'vue'
import type { Ref } from 'vue'
import type { WsMessage, WsChatRequest } from '@/types'

const BASE_RECONNECT_DELAY_MS = 1000
const MAX_RECONNECT_DELAY_MS = 30_000

type MessageHandler = (msg: WsMessage) => void

export interface UseWebSocket {
  connected: Ref<boolean>
  lastMessage: Ref<WsMessage | null>
  send: (msg: WsChatRequest | WsMessage) => void
  onMessage: (handler: MessageHandler) => () => void
  close: () => void
}

function buildWsUrl(): string {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}/ws`
}

export function useWebSocket(): UseWebSocket {
  const connected = ref(false)
  const lastMessage = ref<WsMessage | null>(null)
  const handlers = new Set<MessageHandler>()

  let ws: WebSocket | null = null
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null
  let reconnectDelay = BASE_RECONNECT_DELAY_MS
  let manualClose = false

  function clearReconnectTimer() {
    if (reconnectTimer !== null) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
  }

  function connect() {
    clearReconnectTimer()
    manualClose = false

    const url = buildWsUrl()
    ws = new WebSocket(url)

    ws.addEventListener('open', () => {
      connected.value = true
      reconnectDelay = BASE_RECONNECT_DELAY_MS
    })

    ws.addEventListener('message', (event: MessageEvent) => {
      try {
        const msg: WsMessage = JSON.parse(event.data as string)
        lastMessage.value = msg
        handlers.forEach((h) => h(msg))
      } catch {
        // ignore malformed messages
      }
    })

    ws.addEventListener('close', () => {
      connected.value = false
      ws = null

      if (!manualClose) {
        reconnectTimer = setTimeout(() => {
          reconnectDelay = Math.min(reconnectDelay * 2, MAX_RECONNECT_DELAY_MS)
          connect()
        }, reconnectDelay)
      }
    })

    ws.addEventListener('error', () => {
      // close event will fire after error, triggering reconnect
    })
  }

  function send(msg: WsChatRequest | WsMessage) {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(msg))
    }
  }

  function onMessageHandler(handler: MessageHandler): () => void {
    handlers.add(handler)
    return () => {
      handlers.delete(handler)
    }
  }

  function close() {
    manualClose = true
    clearReconnectTimer()
    if (ws) {
      ws.close()
      ws = null
    }
    connected.value = false
  }

  connect()

  onUnmounted(() => {
    handlers.clear()
    close()
  })

  return { connected, lastMessage, send, onMessage: onMessageHandler, close }
}
