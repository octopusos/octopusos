import { get, post } from '@platform/http'
import type { FrontdeskScope } from '@/features/frontdesk'

export interface FrontdeskChatRequest {
  text: string
  scope: FrontdeskScope
  mentions?: string[]
}

export interface FrontdeskChatResponse {
  message_id: string
  assistant_text: string
  evidence_refs: string[]
  meta: Record<string, any>
  agent_resolution?: 'resolved' | 'unresolved' | 'partial' | 'none'
  reason_code?: 'AGENT_FOUND' | 'AGENT_NOT_FOUND' | 'AGENT_PARTIAL_FOUND' | 'NO_MENTION' | string
  created_at?: string
}

export interface FrontdeskHistoryResponse {
  messages: Array<{
    id: string
    role: 'user' | 'assistant' | 'system'
    text: string
    created_at: string
    evidence_refs?: string[]
    meta?: Record<string, any>
  }>
}

export interface FrontdeskOverviewResponse {
  agents: Array<{ agent_id: string; status: string }>
  tasks_summary: { done: number; in_progress: number; blocked: number }
  top_blockers: Array<Record<string, any>>
}

export interface FrontdeskAgent {
  agent_id: string
  title: string
  category: string
  version: string
  lifecycle: string
  responsibilities: string[]
}

export interface FrontdeskAgentsResponse {
  source: string
  total: number
  agents: FrontdeskAgent[]
}

class FrontdeskService {
  async sendFrontdeskChat(payload: FrontdeskChatRequest): Promise<FrontdeskChatResponse> {
    return post('/api/frontdesk/chat', payload)
  }

  async getFrontdeskHistory(limit = 200): Promise<FrontdeskHistoryResponse> {
    return get('/api/frontdesk/history', { params: { limit } })
  }

  async getFrontdeskOverview(): Promise<FrontdeskOverviewResponse> {
    return get('/api/frontdesk/overview')
  }

  async getAgents(status?: string, limit = 200): Promise<FrontdeskAgentsResponse> {
    return get('/api/agents', { params: { status, limit } })
  }
}

export const frontdeskService = new FrontdeskService()
