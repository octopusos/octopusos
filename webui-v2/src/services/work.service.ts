import { get, post, put } from '@platform/http'

export type WorkArtifactType = 'markdown' | 'docx' | 'xlsx' | 'pptx'
export type WorkRightTab = 'preview' | 'outline' | 'edits' | 'assets'

export interface WorkArtifactHistoryEntry {
  id: string
  created_at: string
  actor: string
  summary: string
  operation: string
  version: number
}

export interface WorkArtifact {
  artifact_id: string
  type: WorkArtifactType
  title: string
  content: string
  version: number
  history: WorkArtifactHistoryEntry[]
}

export interface WorkUiState {
  right_tab: WorkRightTab
  left_width?: number
  selection?: {
    start: number
    end: number
    text?: string
  } | null
}

export interface WorkSessionMessage {
  id: string
  role: 'user' | 'assistant' | 'system' | 'tool'
  content: string
  timestamp: string
  metadata?: Record<string, unknown>
}

export interface WorkSessionState {
  session_id: string
  title: string
  work_mode: boolean
  created_at?: string
  updated_at?: string
  messages: WorkSessionMessage[]
  artifacts: WorkArtifact[]
  active_artifact_id: string
  ui_state: WorkUiState
}

export interface WorkSessionListItem {
  session_id: string
  title: string
  updated_at?: string
  created_at?: string
  last_message?: string
  message_count?: number
  artifacts?: WorkArtifact[]
  active_artifact_id?: string
}

export interface ListWorkSessionsResponse {
  sessions: WorkSessionListItem[]
}

export const workService = {
  async listSessions(params?: { recent?: number; query?: string }): Promise<ListWorkSessionsResponse> {
    return get('/api/work/sessions', { params })
  },

  async createSession(payload?: { title?: string; metadata?: Record<string, unknown> }): Promise<WorkSessionState> {
    return post('/api/work/sessions', payload || {})
  },

  async getSession(sessionId: string): Promise<WorkSessionState> {
    return get(`/api/work/sessions/${sessionId}`)
  },

  async updateSession(
    sessionId: string,
    payload: Partial<Pick<WorkSessionState, 'title' | 'messages' | 'artifacts' | 'active_artifact_id' | 'ui_state'>>
  ): Promise<WorkSessionState> {
    return put(`/api/work/sessions/${sessionId}`, payload)
  },
}

