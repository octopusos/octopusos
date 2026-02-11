import { httpClient } from '@platform/http'
import type { SessionState, SessionStateResponse } from '@/api/types'

const SESSION_STATE_VALUES: ReadonlySet<SessionState> = new Set([
  'active',
  'streaming',
  'interrupted',
  'completed',
  'failed',
  'cancelled',
])

class SessionsApiClient {
  private baseUrl = '/api/sessions'

  async getSessionState(sessionId: string): Promise<SessionStateResponse> {
    if (!sessionId) {
      throw new Error('sessionId is required')
    }

    const response = await httpClient.get<SessionStateResponse>(`${this.baseUrl}/${encodeURIComponent(sessionId)}`)
    const payload = response.data

    if (!payload || typeof payload !== 'object' || !SESSION_STATE_VALUES.has(payload.state as SessionState)) {
      throw new Error('Invalid session state payload')
    }

    return payload
  }
}

export const sessionsApi = new SessionsApiClient()
