import { get, post } from '@/platform/http'

export type ExecTask = {
  task_id: string
  work_id?: string | null
  card_id?: string | null
  task_type: string
  status: string
  risk_level: string
  requires_confirmation: boolean
  created_at_ms: number
  updated_at_ms: number
  started_at_ms?: number | null
  finished_at_ms?: number | null
  input_json: string
  output_json: string
  error_json?: string | null
  evidence_paths_json: string
  idempotency_key: string
}

export const execTasksService = {
  async list(params?: { status?: string; limit?: number }) {
    return get('/api/tasks/items', { params })
  },
  async getItem(taskId: string) {
    return get(`/api/tasks/items/${taskId}`)
  },
  async cancel(taskId: string) {
    return post(`/api/tasks/items/${taskId}/cancel`, {})
  },
  async retry(taskId: string) {
    return post(`/api/tasks/items/${taskId}/retry`, {})
  },
}

