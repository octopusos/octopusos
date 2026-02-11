/**
 * useWebSocket - WebSocket Hook for Real-time Chat
 *
 * Provides WebSocket connection management with:
 * - Auto-connect/disconnect lifecycle
 * - Message streaming support
 * - Reconnection handling
 * - Error recovery
 */

import { useEffect, useRef, useState, useCallback } from 'react'

export interface WebSocketMessage {
  type: string
  content?: string
  messageId?: string
  run_id?: string
  seq?: number
  command_id?: string
  metadata?: Record<string, unknown>
  [key: string]: unknown
}

export interface WebSocketOptions {
  sessionId: string
  onMessage?: (message: WebSocketMessage) => void
  onError?: (error: Event) => void
  onConnect?: () => void
  onDisconnect?: () => void
  autoConnect?: boolean
}

export interface UseWebSocketReturn {
  isConnected: boolean
  isConnecting: boolean
  error: string | null
  sendMessage: (content: string, metadata?: Record<string, unknown>) => boolean
  sendControlStop: (runId: string, commandId: string, reason?: string) => boolean
  sendEditResend: (
    targetMessageId: string,
    newContent: string,
    commandId: string,
    reason?: string,
    metadata?: Record<string, unknown>
  ) => boolean
  connect: () => void
  disconnect: () => void
}

/**
 * useWebSocket Hook
 *
 * Manages WebSocket connection for real-time chat
 *
 * @param options WebSocket connection options
 * @returns WebSocket state and control methods
 *
 * @example
 * ```tsx
 * const { isConnected, sendMessage } = useWebSocket({
 *   sessionId: 'session-1',
 *   onMessage: (msg) => {
 *     if (msg.type === 'token') {
 *       appendToken(msg.content)
 *     } else if (msg.type === 'complete') {
 *       finalizeMessage()
 *     }
 *   }
 * })
 * ```
 */
export function useWebSocket({
  sessionId,
  onMessage,
  onError,
  onConnect,
  onDisconnect,
  autoConnect = true,
}: WebSocketOptions): UseWebSocketReturn {
  const [isConnected, setIsConnected] = useState(false)
  const [isConnecting, setIsConnecting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<number | null>(null)
  const reconnectAttemptsRef = useRef(0)
  const manualCloseRef = useRef(false)
  const heartbeatTimerRef = useRef<number | null>(null)
  const pongTimeoutRef = useRef<number | null>(null)
  const lastRunIdRef = useRef<string | null>(null)
  const lastSeqRef = useRef(0)

  const MAX_RECONNECT_ATTEMPTS = 8
  const RECONNECT_BASE_DELAY = 800
  const RECONNECT_MAX_DELAY = 10000
  const HEARTBEAT_INTERVAL_MS = 15000
  const PONG_TIMEOUT_MS = 10000

  // Cleanup function
  const clearHeartbeatTimers = useCallback(() => {
    if (heartbeatTimerRef.current) {
      clearInterval(heartbeatTimerRef.current)
      heartbeatTimerRef.current = null
    }
    if (pongTimeoutRef.current) {
      clearTimeout(pongTimeoutRef.current)
      pongTimeoutRef.current = null
    }
  }, [])

  const cleanup = useCallback((manual = true) => {
    if (manual) {
      manualCloseRef.current = true
    }
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }
    clearHeartbeatTimers()
    if (wsRef.current) {
      const current = wsRef.current
      if (current.readyState === WebSocket.CONNECTING) {
        // Avoid browser warning: "WebSocket is closed before the connection is established."
        current.onopen = () => current.close()
        current.onclose = null
        current.onerror = null
        current.onmessage = null
      } else {
        current.close()
      }
      wsRef.current = null
    }
  }, [clearHeartbeatTimers])

  // Connect function
  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return
    }

    cleanup(false)
    setIsConnecting(true)
    setError(null)
    manualCloseRef.current = false

    try {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const wsUrl = `${protocol}//${window.location.host}/ws/chat/${sessionId}`

      console.log('[WebSocket] Connecting to:', wsUrl)
      const ws = new WebSocket(wsUrl)
      wsRef.current = ws

      ws.onopen = () => {
        setIsConnected(true)
        setIsConnecting(false)
        setError(null)
        reconnectAttemptsRef.current = 0
        clearHeartbeatTimers()
        heartbeatTimerRef.current = window.setInterval(() => {
          const current = wsRef.current
          if (!current || current.readyState !== WebSocket.OPEN) {
            return
          }
          try {
            current.send('ping')
            if (pongTimeoutRef.current) {
              clearTimeout(pongTimeoutRef.current)
            }
            pongTimeoutRef.current = window.setTimeout(() => {
              const stale = wsRef.current
              if (stale && stale.readyState === WebSocket.OPEN) {
                stale.close()
              }
            }, PONG_TIMEOUT_MS)
          } catch {
            current.close()
          }
        }, HEARTBEAT_INTERVAL_MS)
        const knownRunId = lastRunIdRef.current
        if (knownRunId) {
          ws.send(JSON.stringify({ type: 'resume', run_id: knownRunId, last_seq: Math.max(0, lastSeqRef.current) }))
        }
        onConnect?.()
      }

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data) as WebSocketMessage
          if (message.type === 'pong') {
            if (pongTimeoutRef.current) {
              clearTimeout(pongTimeoutRef.current)
              pongTimeoutRef.current = null
            }
          }
          if (typeof message.run_id === 'string' && message.run_id) {
            lastRunIdRef.current = message.run_id
          }
          if (typeof message.seq === 'number' && Number.isFinite(message.seq) && message.seq > lastSeqRef.current) {
            lastSeqRef.current = message.seq
          }
          if (message.type === 'message.end' || message.type === 'message.cancelled' || message.type === 'message.error') {
            if (typeof message.run_id === 'string' && message.run_id) {
              lastRunIdRef.current = message.run_id
            }
          }
          onMessage?.(message)
        } catch (err) {
          console.error('Failed to parse WebSocket message:', err)
        }
      }

      ws.onerror = (event) => {
        setError('WebSocket connection error')
        onError?.(event)
      }

      ws.onclose = () => {
        setIsConnected(false)
        setIsConnecting(false)
        clearHeartbeatTimers()
        onDisconnect?.()

        if (manualCloseRef.current) {
          return
        }

        // Auto-reconnect if not manually closed
        if (reconnectAttemptsRef.current < MAX_RECONNECT_ATTEMPTS) {
          reconnectAttemptsRef.current += 1
          const attempt = reconnectAttemptsRef.current
          const expDelay = Math.min(RECONNECT_MAX_DELAY, RECONNECT_BASE_DELAY * (2 ** (attempt - 1)))
          const jitter = Math.floor(Math.random() * Math.max(300, expDelay * 0.35))
          const reconnectDelay = expDelay + jitter
          reconnectTimeoutRef.current = window.setTimeout(() => {
            connect()
          }, reconnectDelay)
        } else {
          setError('Connection lost. Please refresh the page.')
        }
      }
    } catch (err) {
      setError('Failed to create WebSocket connection')
      setIsConnecting(false)
    }
  }, [sessionId, onMessage, onError, onConnect, onDisconnect, cleanup, clearHeartbeatTimers])

  // Disconnect function
  const disconnect = useCallback(() => {
    reconnectAttemptsRef.current = MAX_RECONNECT_ATTEMPTS // Prevent auto-reconnect
    cleanup(true)
    setIsConnected(false)
    setIsConnecting(false)
  }, [cleanup])

  // Send message function
  const sendMessage = useCallback(
    (content: string, metadata?: Record<string, unknown>) => {
      if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
        setError('Not connected to server')
        return false
      }

      try {
        const commandId = (() => {
          try {
            return typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function'
              ? crypto.randomUUID()
              : `cmd-${Date.now()}-${Math.random().toString(16).slice(2)}`
          } catch {
            return `cmd-${Date.now()}-${Math.random().toString(16).slice(2)}`
          }
        })()
        const message = {
          type: 'user_message',  // ✅ Backend expects 'user_message', not 'message'
          command_id: commandId,
          content,
          metadata: metadata || {},
        }
        wsRef.current.send(JSON.stringify(message))
        return true
      } catch (err) {
        setError('Failed to send message')
        console.error('WebSocket send error:', err)
        return false
      }
    },
    []
  )

  const sendControlStop = useCallback(
    (runId: string, commandId: string, reason = 'user_clicked_stop') => {
      if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
        setError('Not connected to server')
        return false
      }
      try {
        wsRef.current.send(
          JSON.stringify({
            type: 'control.stop',
            session_id: sessionId,
            run_id: runId,
            command_id: commandId,
            reason,
          })
        )
        return true
      } catch (err) {
        setError('Failed to send stop command')
        console.error('WebSocket stop send error:', err)
        return false
      }
    },
    [sessionId]
  )

  const sendEditResend = useCallback(
    (
      targetMessageId: string,
      newContent: string,
      commandId: string,
      reason = 'typo_fix',
      metadata?: Record<string, unknown>
    ) => {
      if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
        setError('Not connected to server')
        return false
      }
      try {
        wsRef.current.send(
          JSON.stringify({
            type: 'control.edit_resend',
            session_id: sessionId,
            target_message_id: targetMessageId,
            new_content: newContent,
            command_id: commandId,
            reason,
            metadata: metadata || {},
          })
        )
        return true
      } catch (err) {
        setError('Failed to send edit-resend command')
        console.error('WebSocket edit-resend send error:', err)
        return false
      }
    },
    [sessionId]
  )

  // Auto-connect on mount
  useEffect(() => {
    lastRunIdRef.current = null
    lastSeqRef.current = 0
  }, [sessionId])

  // Auto-connect is session-scoped; avoid tying cleanup to callback identity changes.
  useEffect(() => {
    if (autoConnect) {
      connect()
    }
    // connect callback may change when message handlers close over state.
    // Reconnecting on every callback identity change causes false manual closes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoConnect, sessionId])

  // Unmount cleanup
  useEffect(() => () => {
    cleanup(true)
  }, [cleanup])

  return {
    isConnected,
    isConnecting,
    error,
    sendMessage,
    sendControlStop,
    sendEditResend,
    connect,
    disconnect,
  }
}
