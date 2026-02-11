import { get, post, put, del } from '@platform/http'

export type CallRuntime = 'local' | 'cloud'

export interface CreateCallSessionRequest {
  runtime: CallRuntime
  provider_id?: string
  model_id?: string
  voice_profile_id?: string
}

export interface CallSession {
  id: string
  runtime: CallRuntime
  provider_id?: string | null
  model_id?: string | null
  voice_profile_id?: string | null
  status: string
  created_at: string
  connected_at?: string | null
  ended_at?: string | null
  error_message?: string | null
}

export interface CreateCallSessionResponse {
  call_session_id: string
  ws_url: string
  protocol_version: number
  session: CallSession
}

export interface VoiceContact {
  id: string
  display_name: string
  runtime: CallRuntime
  provider_id?: string | null
  model_id?: string | null
  voice_profile_id?: string | null
  prefs_json: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface VoiceContactPayload {
  display_name: string
  runtime: CallRuntime
  provider_id?: string
  model_id?: string
  voice_profile_id?: string
  prefs_json?: Record<string, unknown>
}

export interface CallEvent {
  id: number
  call_session_id: string
  event_type: string
  payload: Record<string, unknown>
  created_at: string
}

export interface CallTranscript {
  id: number
  call_session_id: string
  speaker: string
  text: string
  created_at: string
}

export const callService = {
  async createSession(payload: CreateCallSessionRequest, idempotencyKey?: string): Promise<CreateCallSessionResponse> {
    const response = await post<CreateCallSessionResponse | { detail?: string; error?: string }>(
      '/api/calls/sessions',
      payload,
      idempotencyKey
        ? {
            headers: {
              'Idempotency-Key': idempotencyKey,
            },
          }
        : undefined
    )
    if ('call_session_id' in response && 'ws_url' in response) {
      return response
    }
    const message = ('detail' in response && response.detail) || ('error' in response && response.error) || 'Failed to create call session'
    throw new Error(message)
  },

  async getSession(sessionId: string): Promise<{ session: CallSession }> {
    return get(`/api/calls/sessions/${sessionId}`)
  },

  async getEvents(sessionId: string): Promise<{ events: CallEvent[] }> {
    return get(`/api/calls/sessions/${sessionId}/events`)
  },

  async getTranscripts(sessionId: string): Promise<{ transcripts: CallTranscript[] }> {
    return get(`/api/calls/sessions/${sessionId}/transcripts`)
  },

  async listVoiceContacts(): Promise<{ contacts: VoiceContact[] }> {
    return get('/api/voice-contacts')
  },

  async createVoiceContact(payload: VoiceContactPayload): Promise<{ contact: VoiceContact }> {
    return post('/api/voice-contacts', payload)
  },

  async updateVoiceContact(contactId: string, payload: VoiceContactPayload): Promise<{ contact: VoiceContact }> {
    return put(`/api/voice-contacts/${contactId}`, payload)
  },

  async deleteVoiceContact(contactId: string): Promise<{ ok: boolean }> {
    return del(`/api/voice-contacts/${contactId}`)
  },
}
