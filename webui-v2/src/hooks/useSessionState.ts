import { useCallback, useEffect, useState } from 'react'
import { sessionsApi } from '@/api/sessions'
import type { SessionStateResponse } from '@/api/types'

export function useSessionState(sessionId: string) {
  const [sessionState, setSessionState] = useState<SessionStateResponse | null>(null)
  const [loading, setLoading] = useState(false)

  const refreshSessionState = useCallback(async () => {
    if (!sessionId) {
      setSessionState(null)
      return null
    }

    setLoading(true)
    try {
      const payload = await sessionsApi.getSessionState(sessionId)
      setSessionState(payload)
      return payload
    } catch {
      setSessionState(null)
      return null
    } finally {
      setLoading(false)
    }
  }, [sessionId])

  useEffect(() => {
    void refreshSessionState()
  }, [refreshSessionState])

  return {
    sessionState,
    loading,
    refreshSessionState,
  }
}
