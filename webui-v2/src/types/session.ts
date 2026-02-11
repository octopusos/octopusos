export type SessionState =
  | 'active'
  | 'streaming'
  | 'interrupted'
  | 'completed'
  | 'failed'
  | 'cancelled'

export type ResumeStatus = 'ok' | 'required_retry'

export interface SessionResumeInfo {
  supported: boolean
  status: ResumeStatus
  reason?: string | null
}

export interface SessionStateResponse {
  session_id: string

  // Typed self-healing fields
  state: SessionState
  current_run_id?: string | null
  last_seq?: number | null
  updated_at?: string | null
  resume?: SessionResumeInfo

  // Backward-compatible fields from existing session payload
  metadata?: Record<string, unknown>
  [k: string]: unknown
}
