/**
 * Execution Plans API Client
 *
 * Handles all execution plan-related API calls
 */

import { httpClient } from '@platform/http'

// ============================================
// DTOs
// ============================================

export interface ExecutionPlanStep {
  step_id: string
  description: string
  status: string
  started_at?: string
  completed_at?: string
}

export interface ExecutionPlan {
  id: string
  name: string
  description?: string
  status: string
  priority: string
  steps: number
  created_at: string
  estimated_time?: string
  executed_at?: string
}

export interface ExecutionPlansListResponse {
  plans: ExecutionPlan[]
  total: number
  limit: number
  offset: number
}

export interface ExecutionPlanDetailResponse {
  plan: ExecutionPlan
  steps: ExecutionPlanStep[]
}

export interface ExecutionPlanListFilters {
  status?: string
  priority?: string
  limit?: number
  offset?: number
  sort?: string
}

// ============================================
// API Client
// ============================================

class ExecutionPlansApiClient {
  private baseUrl = '/api/dispatch/jobs'

  /**
   * List execution plans with optional filters
   * GET /api/dispatch/jobs
   */
  async listPlans(filters?: ExecutionPlanListFilters): Promise<ExecutionPlansListResponse> {
    const limit = typeof filters?.limit === 'number' ? filters.limit : 25
    const offset = typeof filters?.offset === 'number' ? filters.offset : 0
    const backendLimit = Math.min(200, Math.max(1, offset + limit))

    const response = await httpClient.get<{ jobs?: Array<Record<string, any>> }>(this.baseUrl, {
      params: {
        status: filters?.status,
        limit: backendLimit,
      }
    })

    const jobs = Array.isArray(response.data?.jobs) ? response.data.jobs : []
    const sortedJobs = jobs.sort((a, b) => String(b?.created_at || '').localeCompare(String(a?.created_at || '')))
    const pagedJobs = sortedJobs.slice(offset, offset + limit)

    const plans = pagedJobs.map((job) => ({
      id: String(job?.job_id || ''),
      name: `Dispatch ${String(job?.job_id || '').slice(0, 8)}`,
      description: job?.proposal_id ? `Proposal: ${String(job.proposal_id)}` : undefined,
      status: String(job?.status || 'queued'),
      priority: 'medium',
      steps: Array.isArray(job?.evidence?.steps) ? job.evidence.steps.length : 0,
      created_at: String(job?.created_at || ''),
      estimated_time: undefined,
      executed_at: typeof job?.ended_at === 'string' ? job.ended_at : undefined,
    }))

    return {
      plans,
      total: sortedJobs.length,
      limit,
      offset,
    }
  }

  /**
   * Get execution plan details by ID
   * GET /api/dispatch/jobs/{job_id}
   */
  async getPlan(planId: string): Promise<ExecutionPlanDetailResponse> {
    const response = await httpClient.get<{ job?: Record<string, any> }>(`${this.baseUrl}/${encodeURIComponent(planId)}`)
    const job = response.data?.job || {}

    return {
      plan: {
        id: String(job?.job_id || planId),
        name: `Dispatch ${String(job?.job_id || planId).slice(0, 8)}`,
        description: job?.proposal_id ? `Proposal: ${String(job.proposal_id)}` : undefined,
        status: String(job?.status || 'queued'),
        priority: 'medium',
        steps: Array.isArray(job?.evidence?.steps) ? job.evidence.steps.length : 0,
        created_at: String(job?.created_at || ''),
        estimated_time: undefined,
        executed_at: typeof job?.ended_at === 'string' ? job.ended_at : undefined,
      },
      steps: [],
    }
  }
}

// Singleton instance
export const executionPlansApi = new ExecutionPlansApiClient()
