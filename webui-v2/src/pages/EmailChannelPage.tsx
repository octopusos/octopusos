/**
 * EmailChannelPage - Email channel (instances are provider bindings configured via MCP)
 *
 * Minimal instance manager:
 * - list instances
 * - create instance (imap/smtp)
 * - test connectivity
 *
 * P0.5:
 * - unread (today) view with show-all toggle
 * - quick actions: allow/block sender, snooze 24h, mark as read (imap only)
 */

import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { usePageHeader, usePageActions } from '@/ui/layout'
import { t, K } from '@/ui/text'
import { toast } from '@/ui/feedback'
import {
  Box,
  Typography,
  Button,
  Chip,
  FormControlLabel,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Select,
  MenuItem,
  Checkbox,
  Divider,
} from '@/ui'
import { Switch } from '@mui/material'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { emailService, type EmailInstance } from '@services'
import { EmptyState } from '@/ui/layout'
import { EmailIcon } from '@/ui/icons'

const SIZE_SMALL = 'small' as const
const VARIANT_OUTLINED = 'outlined' as const
const VARIANT_CONTAINED = 'contained' as const

type CreateForm = {
  name: string
  provider_type: 'imap_smtp' | 'mock' | 'gmail_oauth' | 'outlook_oauth'
  username: string
  secret_ref: string
  imap_host: string
  imap_port: number
  imap_tls: boolean
  smtp_host: string
  smtp_port: number
  smtp_tls: boolean
  oauth_client_id: string
  oauth_client_secret_ref: string
  oauth_redirect_uri: string
  outlook_tenant: string
}

function defaultForm(): CreateForm {
  return {
    name: '',
    provider_type: 'imap_smtp',
    username: '',
    secret_ref: '',
    imap_host: '',
    imap_port: 993,
    imap_tls: true,
    smtp_host: '',
    smtp_port: 587,
    smtp_tls: true,
    oauth_client_id: '',
    oauth_client_secret_ref: '',
    oauth_redirect_uri: '',
    outlook_tenant: 'common',
  }
}

function formatTs(ms: number | null): string {
  if (!ms) return '-'
  try {
    return new Date(ms).toLocaleString()
  } catch {
    return String(ms)
  }
}

type EmailHeader = {
  message_id: string
  from_email: string
  from_name?: string | null
  subject: string
  date_ms: number
  snippet: string
  importance: 'important' | 'normal' | 'filtered'
}

function safeSenderEmail(raw: string): string {
  const v = String(raw || '').trim()
  const m = v.match(/([A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})/i)
  return (m?.[1] || v).toLowerCase()
}

function safeSenderDomain(fromEmail: string): string {
  const email = safeSenderEmail(fromEmail)
  const parts = email.split('@')
  return (parts[1] || '').trim().toLowerCase()
}

export default function EmailChannelPage() {
  const navigate = useNavigate()
  const [instances, setInstances] = useState<EmailInstance[]>([])
  const [loading, setLoading] = useState(false)
  const [createOpen, setCreateOpen] = useState(false)
  const [creating, setCreating] = useState(false)
  const [testingId, setTestingId] = useState<string | null>(null)
  const [form, setForm] = useState<CreateForm>(defaultForm())

  const [selectedInstanceId, setSelectedInstanceId] = useState<string>('')
  const [unreadLoading, setUnreadLoading] = useState(false)
  const [showAll, setShowAll] = useState(false)
  const [digestMd, setDigestMd] = useState<string>('')
  const [important, setImportant] = useState<EmailHeader[]>([])
  const [normal, setNormal] = useState<EmailHeader[]>([])
  const [filtered, setFiltered] = useState<EmailHeader[]>([])
  const [oauthConnected, setOauthConnected] = useState(false)
  const [oauthChecking, setOauthChecking] = useState(false)

  async function load() {
    setLoading(true)
    try {
      const res = await emailService.listInstances()
      setInstances(Array.isArray(res.instances) ? res.instances : [])
      const first = (Array.isArray(res.instances) ? res.instances : [])[0]
      if (!selectedInstanceId && first?.instance_id) setSelectedInstanceId(String(first.instance_id))
    } catch (err) {
      console.error('[email-channel] listInstances error', err)
      toast.error(t(K.common.error))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  usePageHeader({
    title: t(K.page.emailChannel.title),
    subtitle: t(K.page.emailChannel.subtitle),
  })

  usePageActions([
    {
      key: 'new',
      label: t(K.page.emailChannel.actionNewInstance),
      variant: 'contained',
      onClick: () => setCreateOpen(true),
    },
    {
      key: 'refresh',
      label: t(K.common.refresh),
      variant: 'outlined',
      onClick: load,
    },
  ])

  const rows = useMemo(() => instances || [], [instances])
  const selected = useMemo(() => rows.find((x) => x.instance_id === selectedInstanceId) || null, [rows, selectedInstanceId])
  const hasInstances = rows.length > 0
  const blockedDomains = useMemo(() => {
    try {
      const raw = String(selected?.config_json || '{}')
      const cfg = JSON.parse(raw)
      const items = Array.isArray(cfg?.block_domains) ? cfg.block_domains : []
      const out = items.map((x: any) => String(x || '').trim().toLowerCase()).filter((x: string) => x)
      return Array.from(new Set(out))
    } catch {
      return []
    }
  }, [selected?.config_json])

  async function loadUnread(instanceId: string) {
    if (!instanceId) return
    setUnreadLoading(true)
    try {
      const res: any = await emailService.unread(instanceId, { since: 'today', limit: 50 })
      setDigestMd(String(res?.digest_md || ''))
      setImportant(Array.isArray(res?.important) ? res.important : [])
      setNormal(Array.isArray(res?.normal) ? res.normal : [])
      setFiltered(Array.isArray(res?.filtered) ? res.filtered : [])
    } catch (err) {
      console.error('[email-channel] unread error', err)
      toast.error(t(K.common.error))
      setDigestMd('')
      setImportant([])
      setNormal([])
      setFiltered([])
    } finally {
      setUnreadLoading(false)
    }
  }

  async function onCreate() {
    setCreating(true)
    try {
      const payload =
        form.provider_type === 'imap_smtp'
          ? {
              name: form.name,
              provider_type: form.provider_type,
              secret_ref: form.secret_ref,
              config: {
                username: form.username,
                imap_host: form.imap_host,
                imap_port: form.imap_port,
                imap_tls: form.imap_tls,
                smtp_host: form.smtp_host,
                smtp_port: form.smtp_port,
                smtp_tls: form.smtp_tls,
              },
            }
          : form.provider_type === 'gmail_oauth'
          ? {
              name: form.name,
              provider_type: form.provider_type,
              secret_ref: '',
              config: {
                client_id: form.oauth_client_id,
                client_secret_ref: form.oauth_client_secret_ref,
                redirect_uri: form.oauth_redirect_uri,
                scopes: [
                  'https://www.googleapis.com/auth/gmail.readonly',
                  'https://www.googleapis.com/auth/gmail.send',
                  'https://www.googleapis.com/auth/gmail.modify',
                ],
              },
            }
          : form.provider_type === 'outlook_oauth'
          ? {
              name: form.name,
              provider_type: form.provider_type,
              secret_ref: '',
              config: {
                tenant: form.outlook_tenant || 'common',
                client_id: form.oauth_client_id,
                client_secret_ref: form.oauth_client_secret_ref,
                redirect_uri: form.oauth_redirect_uri,
                scopes: ['openid', 'profile', 'offline_access', 'User.Read', 'Mail.ReadWrite', 'Mail.Send'],
              },
            }
          : {
              name: form.name,
              provider_type: form.provider_type,
              secret_ref: '',
              config: {
                mock_messages: [],
              },
            }

      await emailService.createInstance(payload as any)
      toast.success(t(K.common.success))
      setCreateOpen(false)
      setForm(defaultForm())
      await load()
    } catch (err) {
      console.error('[email-channel] createInstance error', err)
      toast.error(t(K.common.error))
    } finally {
      setCreating(false)
    }
  }

  async function onTest(instanceId: string) {
    setTestingId(instanceId)
    try {
      const res = await emailService.testInstance(instanceId)
      if (res.test_ok) toast.success(t(K.page.emailChannel.lastTestOk))
      else toast.error(`${t(K.page.emailChannel.lastTestError)} ${res.error || ''}`)
      await load()
    } catch (err) {
      console.error('[email-channel] testInstance error', err)
      toast.error(t(K.common.error))
    } finally {
      setTestingId(null)
    }
  }

  async function refreshOauthStatus(instanceId: string) {
    const inst = rows.find((x) => x.instance_id === instanceId)
    if (!inst) return
    if (inst.provider_type !== 'gmail_oauth' && inst.provider_type !== 'outlook_oauth') {
      setOauthConnected(false)
      return
    }
    setOauthChecking(true)
    try {
      const res: any = await emailService.oauthStatus(instanceId)
      setOauthConnected(Boolean(res?.connected))
    } catch (err) {
      console.error('[email-channel] oauth status error', err)
      setOauthConnected(false)
    } finally {
      setOauthChecking(false)
    }
  }

  async function onOauthConnect() {
    if (!selectedInstanceId) return
    setOauthChecking(true)
    try {
      const res: any = await emailService.oauthStart(selectedInstanceId)
      const url = String(res?.auth_url || '')
      if (!url) throw new Error('missing auth_url')
      window.open(url, '_blank', 'noopener')
      const start = Date.now()
      while (Date.now() - start < 60_000) {
        await new Promise((r) => setTimeout(r, 1200))
        const st: any = await emailService.oauthStatus(selectedInstanceId)
        if (st?.connected) {
          setOauthConnected(true)
          toast.success(t(K.common.success))
          await load()
          return
        }
      }
      toast.info(t(K.common.info))
    } catch (err) {
      console.error('[email-channel] oauth connect error', err)
      toast.error(t(K.common.error))
    } finally {
      setOauthChecking(false)
    }
  }

  async function onOauthDisconnect() {
    if (!selectedInstanceId) return
    setOauthChecking(true)
    try {
      await emailService.oauthDisconnect(selectedInstanceId)
      setOauthConnected(false)
      toast.success(t(K.common.success))
      await load()
    } catch (err) {
      console.error('[email-channel] oauth disconnect error', err)
      toast.error(t(K.common.error))
    } finally {
      setOauthChecking(false)
    }
  }

  async function onAllowSender(h: EmailHeader) {
    if (!selectedInstanceId) return
    const sender = safeSenderEmail(h.from_email)
    try {
      await emailService.allowSender(selectedInstanceId, sender)
      toast.success(t(K.common.success))
      await loadUnread(selectedInstanceId)
    } catch (err) {
      console.error('[email-channel] allow sender error', err)
      toast.error(t(K.common.error))
    }
  }

  async function onBlockSender(h: EmailHeader) {
    if (!selectedInstanceId) return
    const sender = safeSenderEmail(h.from_email)
    try {
      await emailService.blockSender(selectedInstanceId, sender)
      toast.success(t(K.common.success))
      await loadUnread(selectedInstanceId)
    } catch (err) {
      console.error('[email-channel] block sender error', err)
      toast.error(t(K.common.error))
    }
  }

  async function onBlockDomain(domain: string) {
    if (!selectedInstanceId) return
    const d = String(domain || '').trim().toLowerCase()
    if (!d) return
    try {
      await emailService.blockDomain(selectedInstanceId, d)
      toast.success(t(K.common.success))
      await load()
      await loadUnread(selectedInstanceId)
    } catch (err) {
      console.error('[email-channel] block domain error', err)
      toast.error(t(K.common.error))
    }
  }

  async function onUnblockDomain(domain: string) {
    if (!selectedInstanceId) return
    const d = String(domain || '').trim().toLowerCase()
    if (!d) return
    try {
      await emailService.unblockDomain(selectedInstanceId, d)
      toast.success(t(K.common.success))
      await load()
      await loadUnread(selectedInstanceId)
    } catch (err) {
      console.error('[email-channel] unblock domain error', err)
      toast.error(t(K.common.error))
    }
  }

  async function onSnooze(h: EmailHeader) {
    if (!selectedInstanceId) return
    try {
      await emailService.snooze(selectedInstanceId, h.message_id, 24)
      toast.success(t(K.common.success))
      await loadUnread(selectedInstanceId)
    } catch (err) {
      console.error('[email-channel] snooze error', err)
      toast.error(t(K.common.error))
    }
  }

  async function onMarkRead(h: EmailHeader) {
    if (!selectedInstanceId) return
    try {
      await emailService.markRead(selectedInstanceId, h.message_id)
      toast.success(t(K.common.success))
      await loadUnread(selectedInstanceId)
    } catch (err) {
      console.error('[email-channel] mark-read error', err)
      toast.error(t(K.common.error))
    }
  }

  useEffect(() => {
    if (!selectedInstanceId) return
    void loadUnread(selectedInstanceId)
    void refreshOauthStatus(selectedInstanceId)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedInstanceId])

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
      {!loading && !hasInstances ? (
        <EmptyState
          icon={<EmailIcon sx={{ fontSize: 64 }} />}
          title={t(K.page.emailChannel.emptyTitle)}
          description={t(K.page.emailChannel.emptyDescription)}
          actions={[
            {
              label: t(K.page.emailChannel.actionGoMarketplace),
              variant: 'contained',
              onClick: () =>
                navigate(
                  `/mcp-marketplace?search=${encodeURIComponent('email')}&returnTo=${encodeURIComponent('/channels/email')}`
                ),
            },
            {
              label: t(K.page.emailChannel.actionNewInstance),
              variant: 'outlined',
              onClick: () => setCreateOpen(true),
            },
          ]}
        />
      ) : (
        <>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 2 }}>
            <Typography variant="h6">{t(K.page.emailChannel.unreadTitle)}</Typography>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, flexWrap: 'wrap' }}>
              <Select
                size={SIZE_SMALL}
                value={selectedInstanceId}
                onChange={(e) => setSelectedInstanceId(String(e.target.value))}
                sx={{ minWidth: 240 }}
                disabled={!hasInstances}
              >
                {rows.map((x) => (
                  <MenuItem key={x.instance_id} value={x.instance_id}>
                    {x.name}
                  </MenuItem>
                ))}
              </Select>
              <FormControlLabel
                control={<Switch checked={showAll} onChange={(_, checked) => setShowAll(checked)} />}
                label={t(K.page.emailChannel.actionShowAll)}
              />
              <Button
                size={SIZE_SMALL}
                variant={VARIANT_OUTLINED}
                onClick={() => void loadUnread(selectedInstanceId)}
                disabled={!selectedInstanceId || unreadLoading || !hasInstances}
              >
                {t(K.page.emailChannel.actionRefreshUnread)}
              </Button>
              {selected?.provider_type === 'gmail_oauth' || selected?.provider_type === 'outlook_oauth' ? (
                oauthConnected ? (
                  <Button
                    size={SIZE_SMALL}
                    variant={VARIANT_OUTLINED}
                    onClick={() => void onOauthDisconnect()}
                    disabled={oauthChecking}
                  >
                    {t(K.page.emailChannel.actionOauthDisconnect)}
                  </Button>
                ) : (
                  <Button
                    size={SIZE_SMALL}
                    variant={VARIANT_OUTLINED}
                    onClick={() => void onOauthConnect()}
                    disabled={oauthChecking}
                  >
                    {t(K.page.emailChannel.actionOauthConnect)}
                  </Button>
                )
              ) : null}
            </Box>
          </Box>
          <Divider />

          {unreadLoading ? (
            <Typography variant="body2">{t(K.common.loading)}</Typography>
          ) : digestMd ? (
            <Box sx={{ border: 1, borderColor: 'divider', borderRadius: 1, p: 2 }}>
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{digestMd}</ReactMarkdown>
            </Box>
          ) : (
            <Typography variant="body2" sx={{ opacity: 0.8 }}>
              {t(K.common.info)}
            </Typography>
          )}

      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
        <Typography variant="subtitle2">{t(K.page.emailChannel.sectionImportant, { count: important.length })}</Typography>
        {important.map((h) => (
          <Box
            key={h.message_id}
            sx={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: 2,
              border: '1px solid rgba(0,0,0,0.08)',
              borderRadius: 2,
              p: 1.5,
            }}
          >
            <Box sx={{ minWidth: 0 }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 600, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {h.subject || t(K.page.emailChannel.noSubject)}
              </Typography>
              <Typography variant="body2" sx={{ opacity: 0.8, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {`${h.from_email} • ${formatTs(h.date_ms)}`}
              </Typography>
            </Box>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap', justifyContent: 'flex-end' }}>
              <Button size={SIZE_SMALL} variant={VARIANT_OUTLINED} onClick={() => void onAllowSender(h)}>
                {t(K.page.emailChannel.actionAllowSender)}
              </Button>
              <Button size={SIZE_SMALL} variant={VARIANT_OUTLINED} onClick={() => void onBlockSender(h)}>
                {t(K.page.emailChannel.actionBlockSender)}
              </Button>
              <Button size={SIZE_SMALL} variant={VARIANT_OUTLINED} onClick={() => void onSnooze(h)}>
                {t(K.page.emailChannel.actionSnooze24h)}
              </Button>
              {selected?.provider_type === 'imap_smtp' ? (
                <Button size={SIZE_SMALL} variant={VARIANT_OUTLINED} onClick={() => void onMarkRead(h)}>
                  {t(K.page.emailChannel.actionMarkRead)}
                </Button>
              ) : null}
            </Box>
          </Box>
        ))}

        {showAll ? (
          <>
            <Typography variant="subtitle2" sx={{ mt: 1 }}>
              {t(K.page.emailChannel.sectionNormal, { count: normal.length })}
            </Typography>
            {normal.map((h) => (
              <Box key={h.message_id} sx={{ border: '1px solid rgba(0,0,0,0.08)', borderRadius: 2, p: 1.5 }}>
                <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                  {h.subject || t(K.page.emailChannel.noSubject)}
                </Typography>
                <Typography variant="body2" sx={{ opacity: 0.8 }}>
                  {`${h.from_email} • ${formatTs(h.date_ms)}`}
                </Typography>
              </Box>
            ))}

            <Typography variant="subtitle2" sx={{ mt: 1 }}>
              {t(K.page.emailChannel.sectionFiltered, { count: filtered.length })}
            </Typography>
            {filtered.map((h) => (
              <Box key={h.message_id} sx={{ border: '1px solid rgba(0,0,0,0.08)', borderRadius: 2, p: 1.5 }}>
                <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                  {h.subject || t(K.page.emailChannel.noSubject)}
                </Typography>
                <Typography variant="body2" sx={{ opacity: 0.8 }}>
                  {`${h.from_email} • ${formatTs(h.date_ms)}`}
                </Typography>
              </Box>
            ))}
          </>
        ) : null}
      </Box>

      {showAll ? (
        <>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 2, mt: 1 }}>
            <Typography variant="subtitle2">{t(K.page.emailChannel.sectionNormal, { count: normal.length })}</Typography>
          </Box>
          {normal.map((h) => {
            const dom = safeSenderDomain(h.from_email)
            const isBlocked = dom ? blockedDomains.includes(dom) : false
            return (
              <Box key={h.message_id} sx={{ border: '1px solid rgba(0,0,0,0.08)', borderRadius: 2, p: 1.5, display: 'flex', justifyContent: 'space-between', gap: 2 }}>
                <Box sx={{ minWidth: 0 }}>
                  <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                    {h.subject || t(K.page.emailChannel.noSubject)}
                  </Typography>
                  <Typography variant="body2" sx={{ opacity: 0.8 }}>
                    {`${h.from_email} • ${formatTs(h.date_ms)}`}
                  </Typography>
                </Box>
                {dom ? (
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap', justifyContent: 'flex-end' }}>
                    {isBlocked ? (
                      <Button size={SIZE_SMALL} variant={VARIANT_OUTLINED} onClick={() => void onUnblockDomain(dom)}>
                        {t(K.page.emailChannel.actionUnblockDomain)}
                      </Button>
                    ) : (
                      <Button size={SIZE_SMALL} variant={VARIANT_OUTLINED} onClick={() => void onBlockDomain(dom)}>
                        {t(K.page.emailChannel.actionBlockDomain)}
                      </Button>
                    )}
                  </Box>
                ) : null}
              </Box>
            )
          })}

          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 2, mt: 1 }}>
            <Typography variant="subtitle2">{t(K.page.emailChannel.sectionFiltered, { count: filtered.length })}</Typography>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap', justifyContent: 'flex-end' }}>
              {(() => {
                const counts = new Map<string, number>()
                for (const h of filtered) {
                  const dom = safeSenderDomain(h.from_email)
                  if (!dom) continue
                  counts.set(dom, (counts.get(dom) || 0) + 1)
                }
                const top = Array.from(counts.entries()).sort((a, b) => b[1] - a[1]).slice(0, 3)
                return top.map(([dom, cnt]) => {
                  const isBlocked = blockedDomains.includes(dom)
                  return (
                    <Chip
                      key={dom}
                      size={SIZE_SMALL}
                      variant={VARIANT_OUTLINED}
                      label={`${dom} (${cnt})`}
                      onClick={() => (isBlocked ? void onUnblockDomain(dom) : void onBlockDomain(dom))}
                      sx={{ cursor: 'pointer' }}
                    />
                  )
                })
              })()}
            </Box>
          </Box>
          {filtered.map((h) => {
            const dom = safeSenderDomain(h.from_email)
            const isBlocked = dom ? blockedDomains.includes(dom) : false
            return (
              <Box key={h.message_id} sx={{ border: '1px solid rgba(0,0,0,0.08)', borderRadius: 2, p: 1.5, display: 'flex', justifyContent: 'space-between', gap: 2 }}>
                <Box sx={{ minWidth: 0 }}>
                  <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                    {h.subject || t(K.page.emailChannel.noSubject)}
                  </Typography>
                  <Typography variant="body2" sx={{ opacity: 0.8 }}>
                    {`${h.from_email} • ${formatTs(h.date_ms)}`}
                  </Typography>
                </Box>
                {dom ? (
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap', justifyContent: 'flex-end' }}>
                    {isBlocked ? (
                      <Button size={SIZE_SMALL} variant={VARIANT_OUTLINED} onClick={() => void onUnblockDomain(dom)}>
                        {t(K.page.emailChannel.actionUnblockDomain)}
                      </Button>
                    ) : (
                      <Button size={SIZE_SMALL} variant={VARIANT_OUTLINED} onClick={() => void onBlockDomain(dom)}>
                        {t(K.page.emailChannel.actionBlockDomain)}
                      </Button>
                    )}
                  </Box>
                ) : null}
              </Box>
            )
          })}
        </>
      ) : null}

          <Typography variant="h6">{t(K.page.emailChannel.instancesTitle)}</Typography>
          <Divider />

          {loading ? (
            <Typography variant="body2">{t(K.common.loading)}</Typography>
          ) : (
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
              {rows.map((inst) => (
                <Box
                  key={inst.instance_id}
                  sx={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    gap: 2,
                    border: '1px solid rgba(0,0,0,0.08)',
                    borderRadius: 2,
                    p: 2,
                  }}
                >
                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                        {inst.name}
                      </Typography>
                      <Chip size={SIZE_SMALL} variant={VARIANT_OUTLINED} label={inst.provider_type} />
                      {inst.last_test_at_ms ? (
                        <Chip
                          size={SIZE_SMALL}
                          color={inst.last_test_ok ? 'success' : 'error'}
                          variant={VARIANT_OUTLINED}
                          label={inst.last_test_ok ? t(K.page.emailChannel.lastTestOk) : t(K.page.emailChannel.lastTestError)}
                        />
                      ) : null}
                    </Box>
                    <Typography variant="body2" sx={{ opacity: 0.7 }}>
                      {t(K.page.emailChannel.instanceMeta, {
                        id: String(inst.instance_id),
                        updated: formatTs(inst.updated_at_ms),
                        testAt: formatTs(inst.last_test_at_ms),
                      })}
                    </Typography>
                    {inst.last_test_error ? (
                      <Typography variant="body2" sx={{ opacity: 0.8 }}>
                        {inst.last_test_error}
                      </Typography>
                    ) : null}
                  </Box>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Button
                      variant={VARIANT_OUTLINED}
                      size={SIZE_SMALL}
                      onClick={() => onTest(inst.instance_id)}
                      disabled={testingId === inst.instance_id}
                    >
                      {t(K.page.emailChannel.actionTest)}
                    </Button>
                  </Box>
                </Box>
              ))}
            </Box>
          )}
        </>
      )}

      <Dialog open={createOpen} onClose={() => setCreateOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{t(K.page.emailChannel.createDialogTitle)}</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 1 }}>
            <Typography variant="body2" sx={{ opacity: 0.8 }}>
              {t(K.page.emailChannel.createDialogHelp)}
            </Typography>

            <TextField
              label={t(K.page.emailChannel.fieldName)}
              value={form.name}
              onChange={(e) => setForm((p) => ({ ...p, name: e.target.value }))}
              fullWidth
            />

            <Box sx={{ display: 'flex', gap: 2 }}>
              <Box sx={{ flex: 1 }}>
                <Typography variant="caption" sx={{ opacity: 0.8 }}>
                  {t(K.page.emailChannel.fieldProvider)}
                </Typography>
                <Select
                  value={form.provider_type}
                  onChange={(e) => setForm((p) => ({ ...p, provider_type: e.target.value as any }))}
                  fullWidth
                  size={SIZE_SMALL}
                >
                  <MenuItem value="imap_smtp">{t(K.page.emailChannel.providerImapSmtp)}</MenuItem>
                  <MenuItem value="mock">{t(K.page.emailChannel.providerMock)}</MenuItem>
                  <MenuItem value="gmail_oauth">{t(K.page.emailChannel.providerGmailOauth)}</MenuItem>
                  <MenuItem value="outlook_oauth">{t(K.page.emailChannel.providerOutlookOauth)}</MenuItem>
                </Select>
              </Box>
              <Box sx={{ flex: 1 }}>
                <TextField
                  label={t(K.page.emailChannel.fieldSecretRef)}
                  value={form.secret_ref}
                  onChange={(e) => setForm((p) => ({ ...p, secret_ref: e.target.value }))}
                  fullWidth
                />
              </Box>
            </Box>

            {form.provider_type === 'imap_smtp' ? (
              <>
                <TextField
                  label={t(K.page.emailChannel.fieldUsername)}
                  value={form.username}
                  onChange={(e) => setForm((p) => ({ ...p, username: e.target.value }))}
                  fullWidth
                />
                <Box sx={{ display: 'flex', gap: 2 }}>
                  <TextField
                    label={t(K.page.emailChannel.fieldImapHost)}
                    value={form.imap_host}
                    onChange={(e) => setForm((p) => ({ ...p, imap_host: e.target.value }))}
                    fullWidth
                  />
                  <TextField
                    label={t(K.page.emailChannel.fieldImapPort)}
                    type="number"
                    value={form.imap_port}
                    onChange={(e) => setForm((p) => ({ ...p, imap_port: Number(e.target.value || 0) }))}
                    fullWidth
                  />
                </Box>
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={form.imap_tls}
                      onChange={(e) => setForm((p) => ({ ...p, imap_tls: e.target.checked }))}
                    />
                  }
                  label={t(K.page.emailChannel.fieldImapTls)}
                />
                <Box sx={{ display: 'flex', gap: 2 }}>
                  <TextField
                    label={t(K.page.emailChannel.fieldSmtpHost)}
                    value={form.smtp_host}
                    onChange={(e) => setForm((p) => ({ ...p, smtp_host: e.target.value }))}
                    fullWidth
                  />
                  <TextField
                    label={t(K.page.emailChannel.fieldSmtpPort)}
                    type="number"
                    value={form.smtp_port}
                    onChange={(e) => setForm((p) => ({ ...p, smtp_port: Number(e.target.value || 0) }))}
                    fullWidth
                  />
                </Box>
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={form.smtp_tls}
                      onChange={(e) => setForm((p) => ({ ...p, smtp_tls: e.target.checked }))}
                    />
                  }
                  label={t(K.page.emailChannel.fieldSmtpTls)}
                />
              </>
            ) : null}

            {form.provider_type === 'gmail_oauth' || form.provider_type === 'outlook_oauth' ? (
              <>
                <TextField
                  label={t(K.page.emailChannel.fieldOauthClientId)}
                  value={form.oauth_client_id}
                  onChange={(e) => setForm((p) => ({ ...p, oauth_client_id: e.target.value }))}
                  fullWidth
                />
                <TextField
                  label={t(K.page.emailChannel.fieldOauthClientSecretRefOptional)}
                  value={form.oauth_client_secret_ref}
                  onChange={(e) => setForm((p) => ({ ...p, oauth_client_secret_ref: e.target.value }))}
                  fullWidth
                />
                <TextField
                  label={t(K.page.emailChannel.fieldOauthRedirectUri)}
                  value={form.oauth_redirect_uri}
                  onChange={(e) => setForm((p) => ({ ...p, oauth_redirect_uri: e.target.value }))}
                  fullWidth
                />
                {form.provider_type === 'outlook_oauth' ? (
                  <TextField
                    label={t(K.page.emailChannel.fieldOutlookTenant)}
                    value={form.outlook_tenant}
                    onChange={(e) => setForm((p) => ({ ...p, outlook_tenant: e.target.value }))}
                    fullWidth
                  />
                ) : null}
              </>
            ) : null}
          </Box>
        </DialogContent>
        <DialogActions>
          <Button variant={VARIANT_OUTLINED} onClick={() => setCreateOpen(false)}>
            {t(K.common.cancel)}
          </Button>
          <Button variant={VARIANT_CONTAINED} onClick={onCreate} disabled={creating || !form.name}>
            {t(K.common.create)}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
