import { get, post } from '@platform/http'

export type DispatchProposalStatus = 'pending' | 'approved' | 'rejected' | 'cancelled' | 'executed' | 'failed'

export interface DispatchProposal {
  proposal_id: string
  source: string
  proposal_type: string
  status: DispatchProposalStatus
  risk_level: string
  scope: Record<string, any>
  payload: Record<string, any>
  reason: string
  evidence_refs: string[]
  requested_by: string
  requested_at: string
  reviewed_by?: string | null
  reviewed_at?: string | null
  review_comment?: string | null
  execution_ref?: string | null
  created_at: string
  updated_at: string
  auto_execute_eligible?: number
  auto_execute_policy?: string
  approved_then_auto_execute?: number
}

export interface DispatchProposalCreateRequest {
  source: string
  proposal_type: string
  risk_level: string
  scope: Record<string, any>
  payload: Record<string, any>
  reason: string
  evidence_refs: string[]
  requested_by?: string
}

class DispatchService {
  async createProposal(payload: DispatchProposalCreateRequest): Promise<{ proposal_id: string; status: string; risk_level: string }> {
    return post('/api/dispatch/proposals', payload)
  }

  async listProposals(status?: string, limit = 50): Promise<{ proposals: DispatchProposal[] }> {
    return get('/api/dispatch/proposals', { params: { status, limit } })
  }

  async getProposal(proposalId: string): Promise<{ proposal: DispatchProposal }> {
    return get(`/api/dispatch/proposals/${proposalId}`)
  }

  async approveProposal(
    proposalId: string,
    comment: string | null,
    adminToken: string
  ): Promise<{ proposal_id: string; status: string; auto_execute_scheduled: boolean; job_id?: string | null; job_status?: string | null }> {
    return post(
      `/api/dispatch/proposals/${proposalId}/approve`,
      { comment },
      { headers: { 'X-Admin-Token': adminToken } }
    )
  }

  async rejectProposal(proposalId: string, comment: string | null, adminToken: string): Promise<{ proposal_id: string; status: string }> {
    return post(
      `/api/dispatch/proposals/${proposalId}/reject`,
      { comment },
      { headers: { 'X-Admin-Token': adminToken } }
    )
  }

  async executeProposal(
    proposalId: string,
    adminToken: string
  ): Promise<{ proposal_id: string; status: string; job_id: string; execution_state: string }> {
    return post(
      `/api/dispatch/proposals/${proposalId}/execute`,
      {},
      { headers: { 'X-Admin-Token': adminToken } }
    )
  }

  async listJobs(params: { status?: string; proposal_id?: string; limit?: number }): Promise<{ jobs: DispatchJob[] }> {
    return get('/api/dispatch/jobs', { params })
  }

  async getJob(jobId: string): Promise<{ job: DispatchJob }> {
    return get(`/api/dispatch/jobs/${jobId}`)
  }

  async cancelJob(jobId: string, adminToken: string): Promise<{ job_id: string; status: string }> {
    return post(`/api/dispatch/jobs/${jobId}/cancel`, {}, { headers: { 'X-Admin-Token': adminToken } })
  }

  async retryJob(jobId: string, adminToken: string): Promise<{ job_id: string; status: string; execution_state: string }> {
    return post(`/api/dispatch/jobs/${jobId}/retry`, {}, { headers: { 'X-Admin-Token': adminToken } })
  }

  async rollbackJob(jobId: string, adminToken: string): Promise<{ job_id: string; status: string }> {
    return post(`/api/dispatch/jobs/${jobId}/rollback`, {}, { headers: { 'X-Admin-Token': adminToken } })
  }
}

export const dispatchService = new DispatchService()

export interface DispatchJob {
  job_id: string
  proposal_id: string
  status: string
  idempotency_key: string
  resource_key: string
  execution_mode: string
  started_at?: string | null
  ended_at?: string | null
  attempt: number
  max_attempts: number
  last_error_code?: string | null
  last_error_message?: string | null
  evidence: Record<string, any>
  created_at: string
  updated_at: string
}
