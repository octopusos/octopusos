import { useState } from 'react'
import { callService, type CreateCallSessionRequest, type CreateCallSessionResponse } from '@/services/callService'

export function useCallSession() {
  const [creating, setCreating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const createSession = async (
    payload: CreateCallSessionRequest,
    idempotencyKey?: string
  ): Promise<CreateCallSessionResponse> => {
    setCreating(true)
    setError(null)
    try {
      const session = await callService.createSession(payload, idempotencyKey)
      return session
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to create call session'
      setError(message)
      throw err
    } finally {
      setCreating(false)
    }
  }

  return {
    createSession,
    creating,
    error,
  }
}
