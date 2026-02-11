import { get, post } from '@/platform/http'

export type WorkItem = {
  work_id: string
  type: string
  title: string
  status: string
  priority: number
  scope_type: string
  scope_id: string
  source_card_id?: string | null
  created_at_ms: number
  updated_at_ms: number
  started_at_ms?: number | null
  finished_at_ms?: number | null
  summary: string
  detail_json: string
  evidence_ref_json: string
}

export const workItemsService = {
  async list(params?: { status?: string; limit?: number }) {
    return get('/api/work/items', { params })
  },
  async getItem(workId: string) {
    return get(`/api/work/items/${workId}`)
  },
  async cancel(workId: string) {
    return post(`/api/work/items/${workId}/cancel`, {})
  },
}

