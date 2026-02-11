import { get, post } from '@/platform/http'

export type InboxItem = {
  inbox_item_id: string
  card_id: string
  scope_type: string
  scope_id: string
  delivery_type: string
  status: string
  created_at_ms: number
  updated_at_ms: number
}

export const inboxService = {
  async listItems(params?: { status?: string; limit?: number; scope_type?: string; scope_id?: string }) {
    return get('/api/inbox/items', { params })
  },
  async getCard(cardId: string, params?: { limit?: number }) {
    return get(`/api/inbox/cards/${encodeURIComponent(cardId)}`, { params })
  },
  async badge() {
    return get('/api/inbox/badge')
  },
  async markRead(inboxItemId: string) {
    return post(`/api/inbox/items/${inboxItemId}/mark_read`, {})
  },
  async closeCard(cardId: string) {
    return post(`/api/inbox/cards/${cardId}/close`, {})
  },
}
