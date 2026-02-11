import { useCallback, useEffect, useMemo, useState } from 'react'
import { Box, Button, Divider, TextField, Typography } from '@mui/material'
import { usePageHeader } from '@/ui/layout'
import { CardCollectionWrap, ItemCard, type ItemCardAction, type ItemCardMeta } from '@/ui'
import { DialogForm } from '@/ui/interaction'
import { K, useTextTranslation } from '@/ui/text'
import { httpClient } from '@platform/http'
import { getToken } from '@/platform/auth/adminToken'

type CapabilityRequest = {
  id: string
  capability: string
  params: Record<string, any>
  decision: string
  status: string
  updated_at: number
}

type ResolvedItem = { key: string; value: any; source: string }

type DaemonStatus = {
  state: string
  installed: boolean
  service_installed: boolean
  autostart_enabled: boolean
  credentials_present: boolean
  pid?: number | null
  last_error?: string | null
  logs_tail?: string | null
  platform?: string | null
  service_type?: string | null
  tunnel_name?: string | null
}

function pickLatest(requests: CapabilityRequest[]): CapabilityRequest | null {
  if (!Array.isArray(requests) || requests.length === 0) return null
  return [...requests].sort((a, b) => Number(b.updated_at || 0) - Number(a.updated_at || 0))[0]
}

export default function NetworkAccessPage() {
  const { t } = useTextTranslation()
  usePageHeader({
    title: t(K.nav.networkAccess),
    subtitle: t(K.page.networkAccess.subtitle),
  })

  const [loading, setLoading] = useState(false)
  const [requests, setRequests] = useState<CapabilityRequest[]>([])
  const [enableDialogOpen, setEnableDialogOpen] = useState(false)
  const latest = useMemo(() => pickLatest(requests), [requests])

  const [cfg, setCfg] = useState<Record<string, ResolvedItem>>({})
  const [hostname, setHostname] = useState('')
  const [accountId, setAccountId] = useState('')
  const [enforceAccess, setEnforceAccess] = useState('true')
  const [healthPath, setHealthPath] = useState('/api/health')
  const [error, setError] = useState('')
  const [daemon, setDaemon] = useState<DaemonStatus | null>(null)

  const refresh = useCallback(async () => {
    setLoading(true)
    try {
      const resp = await httpClient.get('/api/network/capabilities/status')
      const items = Array.isArray(resp.data?.requests) ? resp.data.requests : []
      setRequests(items)
      const cfgResp = await httpClient.get('/api/network/config')
      const items2 = (cfgResp.data?.items || {}) as Record<string, ResolvedItem>
      setCfg(items2)
      setHostname(String(items2['network.cloudflare.hostname']?.value || ''))
      setAccountId(String(items2['network.cloudflare.account_id']?.value || ''))
      setHealthPath(String(items2['network.cloudflare.health_path']?.value || '/api/health'))
      setEnforceAccess(String(items2['network.cloudflare.enforce_access']?.value ?? true))

      // Daemon status is read-only; logs tail is only returned in debug mode (admin-gated).
      const token = getToken()
      const dResp = await httpClient.get('/api/network/cloudflare/daemon/status', {
        params: token ? { debug: 1 } : undefined,
        headers: token ? { 'X-Admin-Token': token } : undefined,
      })
      setDaemon((dResp.data?.status || null) as DaemonStatus | null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  const requestEnable = async () => {
    const token = getToken()
    if (!token) throw new Error('Admin token required')
    await httpClient.post(
      '/api/network/capabilities/request',
      {
        capability: 'network.tunnel.enable',
        params: {
          scope: '/personal/',
          duration: '2h',
          // execution params (minimal)
          tunnel_name: 'octopusos',
          local_target: 'http://127.0.0.1:8080',
          tunnel_token_ref: 'secret://networkos/cloudflare/tunnel_token',
          access_client_id_ref: 'secret://networkos/cloudflare/access_client_id',
          access_client_secret_ref: 'secret://networkos/cloudflare/access_client_secret',
        },
      },
      { headers: { 'X-Admin-Token': token } }
    )
    setEnableDialogOpen(false)
    await refresh()
  }

  const saveSettings = async () => {
    const token = getToken()
    if (!token) {
      setError(t(K.page.networkAccess.adminTokenRequired))
      return
    }
    setError('')
    await httpClient.post(
      '/api/network/config',
      {
        items: {
          'network.cloudflare.hostname': hostname.trim(),
          'network.cloudflare.account_id': accountId.trim(),
          'network.cloudflare.enforce_access': String(enforceAccess).trim(),
          'network.cloudflare.health_path': healthPath.trim() || '/api/health',
        },
      },
      { headers: { 'X-Admin-Token': token } }
    )
    await refresh()
  }

  const provisionAccess = async () => {
    const token = getToken()
    if (!token) {
      setError(t(K.page.networkAccess.adminTokenRequired))
      return
    }
    setError('')
    await httpClient.post(
      '/api/network/cloudflare/access/provision',
      { params: { scope: '/personal/', hostname: hostname.trim(), account_id: accountId.trim(), probe_path: healthPath.trim() || '/api/health' } },
      { headers: { 'X-Admin-Token': token } }
    )
    await refresh()
  }

  const revokeAccess = async () => {
    const token = getToken()
    if (!token) {
      setError(t(K.page.networkAccess.adminTokenRequired))
      return
    }
    setError('')
    await httpClient.post(
      '/api/network/cloudflare/access/revoke',
      { params: { scope: '/personal/', hostname: hostname.trim(), account_id: accountId.trim() } },
      { headers: { 'X-Admin-Token': token } }
    )
    await refresh()
  }

  const approve = async () => {
    if (!latest?.id) return
    const token = getToken()
    if (!token) throw new Error('Admin token required')
    await httpClient.post(`/api/network/capabilities/${latest.id}/approve`, {}, { headers: { 'X-Admin-Token': token } })
    await refresh()
  }

  const approveDaemon = async (requestId: string) => {
    const token = getToken()
    if (!token) throw new Error('Admin token required')
    await httpClient.post(`/api/network/capabilities/${requestId}/approve`, {}, { headers: { 'X-Admin-Token': token } })
    await refresh()
  }

  const revoke = async () => {
    if (!latest?.id) return
    const token = getToken()
    if (!token) throw new Error('Admin token required')
    await httpClient.post(`/api/network/capabilities/${latest.id}/revoke`, {}, { headers: { 'X-Admin-Token': token } })
    await refresh()
  }

  const daemonAction = async (path: string) => {
    const token = getToken()
    if (!token) {
      setError(t(K.page.networkAccess.adminTokenRequired))
      return
    }
    setError('')
    await httpClient.post(path, { params: {} }, { headers: { 'X-Admin-Token': token } })
    await refresh()
  }

  const meta: ItemCardMeta[] = [
    { key: 'status', label: t(K.page.networkAccess.metaStatus), value: latest ? String(latest.status) : t(K.common.inactive) },
    { key: 'decision', label: t(K.page.networkAccess.metaGate), value: latest ? String(latest.decision) : '-' },
    { key: 'scope', label: t(K.page.networkAccess.metaScope), value: latest?.params?.scope ? String(latest.params.scope) : '/personal/' },
  ]

  const actions: ItemCardAction[] = [
    { key: 'refresh', label: t('common.refresh'), onClick: () => void refresh(), variant: 'outlined' },
    { key: 'enable', label: t(K.page.networkAccess.enableDialogTitle), onClick: () => setEnableDialogOpen(true), variant: 'contained' },
    ...(latest?.decision === 'explain_confirm' && latest?.status === 'pending'
      ? [{ key: 'approve', label: t(K.common.approve), onClick: () => void approve(), variant: 'contained' } as ItemCardAction]
      : []),
    ...(latest && latest.status !== 'revoked'
      ? [{ key: 'revoke', label: t(K.common.revoke), onClick: () => void revoke(), variant: 'outlined' } as ItemCardAction]
      : []),
  ]

  const daemonLatest = useMemo(() => {
    const daemonReqs = requests.filter((r) => String(r.capability || '').startsWith('network.cloudflare.daemon.'))
    return pickLatest(daemonReqs)
  }, [requests])

  const daemonMeta: ItemCardMeta[] = [
    { key: 'daemon_state', label: t(K.page.networkAccess.daemonMetaState), value: daemon ? String(daemon.state || '-') : '-' },
    { key: 'daemon_installed', label: t(K.page.networkAccess.daemonMetaInstalled), value: daemon ? String(Boolean(daemon.installed)) : '-' },
    { key: 'daemon_service', label: t(K.page.networkAccess.daemonMetaServiceInstalled), value: daemon ? String(Boolean(daemon.service_installed)) : '-' },
    { key: 'daemon_autostart', label: t(K.page.networkAccess.daemonMetaAutostart), value: daemon ? String(Boolean(daemon.autostart_enabled)) : '-' },
    { key: 'daemon_creds', label: t(K.page.networkAccess.daemonMetaCredentials), value: daemon ? String(Boolean(daemon.credentials_present)) : '-' },
    { key: 'daemon_tunnel', label: t(K.page.networkAccess.daemonMetaTunnel), value: daemon?.tunnel_name ? String(daemon.tunnel_name) : '-' },
    { key: 'daemon_req_status', label: t(K.page.networkAccess.daemonMetaRequestStatus), value: daemonLatest ? String(daemonLatest.status) : '-' },
    { key: 'daemon_gate', label: t(K.page.networkAccess.daemonMetaGate), value: daemonLatest ? String(daemonLatest.decision) : '-' },
    { key: 'daemon_err', label: t(K.page.networkAccess.daemonMetaLastError), value: daemon?.last_error ? String(daemon.last_error) : '-' },
  ]

  const daemonActions: ItemCardAction[] = [
    { key: 'daemon_refresh', label: t(K.common.refresh), onClick: () => void refresh(), variant: 'outlined' },
    { key: 'daemon_install', label: t(K.common.install), onClick: () => void daemonAction('/api/network/cloudflare/daemon/install'), variant: 'outlined' },
    { key: 'daemon_uninstall', label: t(K.common.remove), onClick: () => void daemonAction('/api/network/cloudflare/daemon/uninstall'), variant: 'outlined' },
    { key: 'daemon_start', label: t(K.common.start), onClick: () => void daemonAction('/api/network/cloudflare/daemon/start'), variant: 'contained' },
    { key: 'daemon_stop', label: t(K.common.stop), onClick: () => void daemonAction('/api/network/cloudflare/daemon/stop'), variant: 'outlined' },
    { key: 'daemon_restart', label: t(K.common.restart), onClick: () => void daemonAction('/api/network/cloudflare/daemon/restart'), variant: 'outlined' },
    { key: 'daemon_autostart_on', label: t(K.common.enabled), onClick: () => void daemonAction('/api/network/cloudflare/daemon/autostart/enable'), variant: 'outlined' },
    { key: 'daemon_autostart_off', label: t(K.common.disabled), onClick: () => void daemonAction('/api/network/cloudflare/daemon/autostart/disable'), variant: 'outlined' },
    ...(daemonLatest?.decision === 'explain_confirm' && daemonLatest?.status === 'pending'
      ? [
          {
            key: 'daemon_approve',
            label: t(K.common.approve),
            onClick: () => void approveDaemon(daemonLatest.id),
            variant: 'contained',
          } as ItemCardAction,
        ]
      : []),
  ]

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      <Typography variant="body2" color="text.secondary">
        {t(K.page.networkAccess.detailsHidden)}
      </Typography>
      <CardCollectionWrap loading={loading}>
        <ItemCard title={t(K.page.networkAccess.cardTitle)} description={t(K.page.networkAccess.cardDesc)} icon="cloud" meta={meta} actions={actions} />
      </CardCollectionWrap>

      <CardCollectionWrap loading={loading}>
        <ItemCard
          title={t(K.page.networkAccess.daemonCardTitle)}
          description={t(K.page.networkAccess.daemonCardDesc)}
          icon="cloud"
          meta={daemonMeta}
          actions={daemonActions}
        />
      </CardCollectionWrap>

      {daemon?.logs_tail ? (
        <Box sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 1, p: 1.5, backgroundColor: 'background.paper' }}>
          <Typography variant="subtitle2" sx={{ mb: 1 }}>
            {t(K.page.networkAccess.daemonLogsTitle)}
          </Typography>
          <Typography
            variant="body2"
            component="pre"
            sx={{ m: 0, whiteSpace: 'pre-wrap', fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace' }}
          >
            {daemon.logs_tail}
          </Typography>
        </Box>
      ) : null}

      {error ? (
        <Typography variant="body2" color="error">
          {error}
        </Typography>
      ) : null}

      <Divider />

      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
        <Typography variant="h6">{t(K.page.networkAccess.settingsTitle)}</Typography>
        <Typography variant="body2" color="text.secondary">
          {t(K.page.networkAccess.settingsHint)}
        </Typography>
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 2 }}>
          <TextField label={t(K.page.networkAccess.hostname)} value={hostname} onChange={(e) => setHostname(e.target.value)} size="small" />
          <TextField label={t(K.page.networkAccess.accountId)} value={accountId} onChange={(e) => setAccountId(e.target.value)} size="small" />
          <TextField label={t(K.page.networkAccess.enforceAccess)} value={enforceAccess} onChange={(e) => setEnforceAccess(e.target.value)} size="small" />
          <TextField label={t(K.page.networkAccess.healthPath)} value={healthPath} onChange={(e) => setHealthPath(e.target.value)} size="small" />
        </Box>
        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
          <Button variant="outlined" onClick={() => void saveSettings()}>
            {t(K.common.save)}
          </Button>
          <Button variant="contained" onClick={() => void provisionAccess()}>
            {t(K.page.networkAccess.provisionAccess)}
          </Button>
          <Button variant="outlined" onClick={() => void revokeAccess()}>
            {t(K.page.networkAccess.revokeAccess)}
          </Button>
        </Box>

        <Typography variant="caption" color="text.secondary">
          {t(K.page.networkAccess.valueSources)}{' '}
          {Object.keys(cfg)
            .filter((k) => k.startsWith('network.cloudflare.'))
            .map((k) => `${k}=${cfg[k]?.source || 'missing'}`)
            .join(' | ')}
        </Typography>
      </Box>

      <DialogForm
        open={enableDialogOpen}
        onClose={() => setEnableDialogOpen(false)}
        title={t(K.page.networkAccess.enableDialogTitle)}
        submitText={t(K.page.networkAccess.enableDialogSubmit)}
        cancelText={t('common.cancel')}
        onSubmit={requestEnable}
      >
        <Typography variant="body2" color="text.secondary">
          {t(K.page.networkAccess.enableDialogHint)}
        </Typography>
      </DialogForm>
    </Box>
  )
}
