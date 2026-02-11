import { get, post } from '@/platform/http'

export type EmailInstance = {
  instance_id: string
  name: string
  provider_type: string
  config_json: string
  secret_ref: string
  created_at_ms: number
  updated_at_ms: number
  last_test_ok: boolean
  last_test_at_ms: number | null
  last_test_error: string | null
}

export type CreateEmailInstanceRequest = {
  name: string
  provider_type: 'imap_smtp' | 'mock'
  config: Record<string, any>
  secret_ref: string
}

export const emailService = {
  async listInstances(): Promise<{ ok: boolean; instances: EmailInstance[] }> {
    return get('/api/channels/email/instances')
  },
  async createInstance(payload: CreateEmailInstanceRequest): Promise<{ ok: boolean; instance_id: string }> {
    return post('/api/channels/email/instances', payload)
  },
  async testInstance(instanceId: string): Promise<{ ok: boolean; test_ok: boolean; error: string | null }> {
    return post(`/api/channels/email/instances/${encodeURIComponent(instanceId)}/test`, {})
  },
  async unread(instanceId: string, params: { since?: string; limit?: number; tz?: string } = {}): Promise<any> {
    return get(`/api/channels/email/${encodeURIComponent(instanceId)}/unread`, { params })
  },
  async allowSender(instanceId: string, sender: string): Promise<{ ok: boolean }> {
    return post(`/api/channels/email/instances/${encodeURIComponent(instanceId)}/rules/allow_sender`, { sender })
  },
  async blockSender(instanceId: string, sender: string): Promise<{ ok: boolean }> {
    return post(`/api/channels/email/instances/${encodeURIComponent(instanceId)}/rules/block_sender`, { sender })
  },
  async blockDomain(instanceId: string, domain: string): Promise<{ ok: boolean; block_domains?: string[] }> {
    return post(`/api/channels/email/instances/${encodeURIComponent(instanceId)}/rules/block_domain`, { domain })
  },
  async unblockDomain(instanceId: string, domain: string): Promise<{ ok: boolean; block_domains?: string[] }> {
    return post(`/api/channels/email/instances/${encodeURIComponent(instanceId)}/rules/unblock_domain`, { domain })
  },
  async snooze(instanceId: string, message_id: string, hours: number = 24): Promise<any> {
    return post(`/api/channels/email/${encodeURIComponent(instanceId)}/snooze`, { message_id, hours })
  },
  async markRead(instanceId: string, message_id: string): Promise<any> {
    return post(`/api/channels/email/${encodeURIComponent(instanceId)}/mark-read`, { message_id })
  },
  async oauthStart(instanceId: string): Promise<any> {
    return get(`/api/channels/email/${encodeURIComponent(instanceId)}/oauth/start`)
  },
  async oauthStatus(instanceId: string): Promise<any> {
    return get(`/api/channels/email/${encodeURIComponent(instanceId)}/oauth/status`)
  },
  async oauthDisconnect(instanceId: string): Promise<any> {
    return post(`/api/channels/email/${encodeURIComponent(instanceId)}/oauth/disconnect`, {})
  },
}
