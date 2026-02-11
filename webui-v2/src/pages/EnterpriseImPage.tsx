import { useCallback, useEffect, useState } from 'react'
import { Box, Grid, Typography, Select, MenuItem, TextField } from '@mui/material'
import { usePageHeader } from '@/ui/layout'
import { CardCollectionWrap, ItemCard, type ItemCardAction, type ItemCardMeta } from '@/ui'
import { DialogForm } from '@/ui/interaction'
import { K, useTextTranslation } from '@/ui/text'
import { httpClient } from '@platform/http'
import { getToken } from '@/platform/auth/adminToken'
import { systemService } from '@services'
import { providersApi } from '@/api/providers'

type PlatformStatus = {
  configured: boolean
  enabled: boolean
  status?: { state?: string; detail?: string }
}

function normalizeStateLabel(raw: string): string {
  const s = (raw || '').trim().toLowerCase()
  if (!s) return 'unknown'
  return s
}

export default function EnterpriseImPage() {
  const { t } = useTextTranslation()
  usePageHeader({
    title: t(K.nav.enterpriseIm),
    subtitle: 'Bridge enterprise IM (governed + audited)',
  })

  const [loading, setLoading] = useState(false)
  const [feishuStatus, setFeishuStatus] = useState<PlatformStatus>({ configured: false, enabled: false })
  const [events, setEvents] = useState<any[]>([])

  const [dialogOpen, setDialogOpen] = useState(false)
  const [config, setConfig] = useState<Record<string, any>>({
    app_id: '',
    app_secret: '',
    verification_token: '',
    encrypt_key: '',
    policy_mode: 'silent_allow',
    model_route: 'local',
    provider: '',
    model: '',
  })

  const [llmProviders, setLlmProviders] = useState<string[]>([])
  const [llmModels, setLlmModels] = useState<string[]>([])

  const loadStatus = useCallback(async () => {
    setLoading(true)
    try {
      const resp = await httpClient.get('/api/enterprise-im/feishu/status')
      const data = resp.data || {}
      setFeishuStatus({
        configured: Boolean(data.configured),
        enabled: Boolean(data.enabled),
        status: data.status || {},
      })
    } catch {
      setFeishuStatus({ configured: false, enabled: false })
    } finally {
      setLoading(false)
    }
  }, [])

  const loadEvents = useCallback(async () => {
    try {
      const resp = await httpClient.get('/api/enterprise-im/events', { params: { platform: 'feishu', limit: 50 } })
      const items = Array.isArray(resp.data?.items) ? resp.data.items : []
      setEvents(items)
    } catch {
      setEvents([])
    }
  }, [])

  const loadProvidersAndModels = useCallback(async () => {
    const modeRaw = String(config.model_route || 'local').trim()
    const mode = modeRaw === 'cloud' ? 'cloud' : 'local'
    const currentProvider = String(config.provider || '').trim()
    const currentModel = String(config.model || '').trim()

    try {
      // warm-up provider status cache (best-effort)
      try {
        await providersApi.getProvidersStatus()
      } catch {}

      const providersResp = await systemService.listProvidersApiProvidersGet()
      const local = Array.isArray(providersResp?.local) ? providersResp.local : []
      const cloud = Array.isArray(providersResp?.cloud) ? providersResp.cloud : []
      const filteredProviders =
        mode === 'local' ? local.map((p: any) => p?.id).filter(Boolean) : cloud.map((p: any) => p?.id).filter(Boolean)
      setLlmProviders(filteredProviders)

      const chooseProvider = async (providerId: string, modelId: string) => {
        if (!providerId) {
          setLlmModels([])
          setConfig((prev) => ({ ...prev, provider: '', model: '' }))
          return
        }
        try {
          const modelsResp = await providersApi.getProviderModels(providerId)
          const loadedModels = Array.isArray(modelsResp?.models)
            ? modelsResp.models.map((m: any) => m?.id || m?.name || m?.label).filter(Boolean)
            : []
          setLlmModels(loadedModels)
          if (loadedModels.length > 0 && !loadedModels.includes(modelId)) {
            setConfig((prev) => ({ ...prev, model: loadedModels[0] }))
          }
          return
        } catch {}

        // fallback: installed models
        try {
          const installedResp = await systemService.listModelsApiModelsListGet()
          const providerModels = Array.isArray(installedResp?.models)
            ? installedResp.models
                .filter((m: any) => m?.provider === providerId)
                .map((m: any) => m?.name)
                .filter(Boolean)
            : []
          setLlmModels(providerModels)
          if (providerModels.length > 0 && !providerModels.includes(modelId)) {
            setConfig((prev) => ({ ...prev, model: providerModels[0] }))
          }
        } catch {
          setLlmModels([])
        }
      }

      if (currentProvider && filteredProviders.includes(currentProvider)) {
        await chooseProvider(currentProvider, currentModel)
        return
      }
      if (filteredProviders.length > 0) {
        const first = filteredProviders[0]
        setConfig((prev) => ({ ...prev, provider: first, model: '' }))
        await chooseProvider(first, '')
        return
      }

      setLlmModels([])
    } catch {
      setLlmProviders([])
      setLlmModels([])
    }
  }, [config.model_route, config.provider, config.model])

  useEffect(() => {
    loadStatus()
    loadEvents()
  }, [loadStatus, loadEvents])

  useEffect(() => {
    if (!dialogOpen) return
    loadProvidersAndModels()
  }, [dialogOpen, loadProvidersAndModels])

  const connect = async () => {
    const token = getToken()
    if (!token) {
      throw new Error('Admin token required')
    }
    await httpClient.post(
      '/api/enterprise-im/feishu/connect',
      { config },
      { headers: { 'X-Admin-Token': token } }
    )
    setDialogOpen(false)
    await loadStatus()
    await loadEvents()
  }

  const disconnect = async () => {
    const token = getToken()
    if (!token) {
      throw new Error('Admin token required')
    }
    await httpClient.post('/api/enterprise-im/feishu/disconnect', {}, { headers: { 'X-Admin-Token': token } })
    await loadStatus()
  }

  const feishuMeta: ItemCardMeta[] = [
    {
      key: 'status',
      label: 'Status',
      value: normalizeStateLabel(String(feishuStatus?.status?.state || (feishuStatus.enabled ? 'enabled' : 'disabled'))),
    },
    { key: 'configured', label: 'Configured', value: feishuStatus.configured ? 'yes' : 'no' },
  ]

  const feishuActions: ItemCardAction[] = [
    {
      key: 'configure',
      label: feishuStatus.enabled ? 'Reconfigure' : 'Configure & Connect',
      onClick: () => {
        setDialogOpen(true)
      },
    },
    ...(feishuStatus.enabled
      ? [
          {
            key: 'disconnect',
            label: 'Disconnect',
            onClick: () => {
              void disconnect()
            },
          },
        ]
      : []),
  ]

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      <Box>
        <Typography variant="h6" sx={{ mb: 2 }}>
          {t(K.nav.enterpriseIm)}
        </Typography>
        <CardCollectionWrap loading={loading}>
          <ItemCard
            key="feishu"
            title="Feishu / Lark"
            description="Enterprise IM bridge (verified + decrypted + audited)."
            icon="chat"
            meta={feishuMeta}
            actions={feishuActions}
          />
        </CardCollectionWrap>
      </Box>

      <Box>
        <Typography variant="h6" sx={{ mb: 2 }}>
          Recent Events (Audit)
        </Typography>
        <CardCollectionWrap loading={false}>
          {events.length === 0 ? (
            <Typography variant="body2" color="text.secondary">
              No events yet.
            </Typography>
          ) : (
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
              {events.slice(0, 10).map((e, idx) => (
                <Typography key={idx} variant="body2" color="text.secondary">
                  {String(e.direction || '')} {String(e.user_key || '')} {String(e.message_id || '')}
                </Typography>
              ))}
            </Box>
          )}
        </CardCollectionWrap>
      </Box>

      <DialogForm
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        title="Configure Feishu"
        submitText="Connect"
        cancelText={t('common.cancel')}
        onSubmit={connect}
        submitDisabled={
          !String(config.app_id || '').trim() ||
          !String(config.app_secret || '').trim() ||
          !String(config.verification_token || '').trim() ||
          !String(config.provider || '').trim() ||
          !String(config.model || '').trim()
        }
      >
        <Grid container spacing={2}>
          <Grid item xs={12}>
            <TextField
              label="App ID"
              value={config.app_id}
              onChange={(e) => setConfig((p) => ({ ...p, app_id: e.target.value }))}
              fullWidth
              required
            />
          </Grid>
          <Grid item xs={12}>
            <TextField
              label="App Secret"
              value={config.app_secret}
              onChange={(e) => setConfig((p) => ({ ...p, app_secret: e.target.value }))}
              fullWidth
              required
              type="password"
            />
          </Grid>
          <Grid item xs={12}>
            <TextField
              label="Verification Token"
              value={config.verification_token}
              onChange={(e) => setConfig((p) => ({ ...p, verification_token: e.target.value }))}
              fullWidth
              required
              type="password"
            />
          </Grid>
          <Grid item xs={12}>
            <TextField
              label="Encrypt Key (optional)"
              value={config.encrypt_key}
              onChange={(e) => setConfig((p) => ({ ...p, encrypt_key: e.target.value }))}
              fullWidth
              type="password"
            />
          </Grid>

          <Grid item xs={12}>
            <Select
              fullWidth
              value={String(config.policy_mode || 'silent_allow')}
              onChange={(e) => setConfig((p) => ({ ...p, policy_mode: e.target.value }))}
            >
              <MenuItem value="silent_allow">silent_allow</MenuItem>
              <MenuItem value="explain_confirm">explain_confirm</MenuItem>
              <MenuItem value="block">block</MenuItem>
            </Select>
          </Grid>

          <Grid item xs={12}>
            <Select
              fullWidth
              value={String(config.model_route || 'local')}
              onChange={(e) => {
                setConfig((p) => ({ ...p, model_route: e.target.value, provider: '', model: '' }))
                // reload provider list on next tick
                setTimeout(() => loadProvidersAndModels(), 0)
              }}
            >
              <MenuItem value="local">local</MenuItem>
              <MenuItem value="cloud">cloud</MenuItem>
            </Select>
          </Grid>

          <Grid item xs={12}>
            <Select
              fullWidth
              value={String(config.provider || '')}
              onChange={(e) => {
                const nextProvider = String(e.target.value || '')
                setConfig((p) => ({ ...p, provider: nextProvider, model: '' }))
                setTimeout(() => loadProvidersAndModels(), 0)
              }}
            >
              {llmProviders.length === 0 ? (
                <MenuItem value="">
                  <em>{t('page.chat.noProviders')}</em>
                </MenuItem>
              ) : (
                llmProviders.map((p) => (
                  <MenuItem key={p} value={p}>
                    {p}
                  </MenuItem>
                ))
              )}
            </Select>
          </Grid>

          <Grid item xs={12}>
            <Select
              fullWidth
              value={String(config.model || '')}
              onChange={(e) => setConfig((p) => ({ ...p, model: e.target.value }))}
              disabled={!String(config.provider || '').trim()}
            >
              {llmModels.length === 0 ? (
                <MenuItem value="">
                  <em>{t('page.chat.noModels')}</em>
                </MenuItem>
              ) : (
                llmModels.map((m) => (
                  <MenuItem key={m} value={m}>
                    {m}
                  </MenuItem>
                ))
              )}
            </Select>
          </Grid>
        </Grid>
      </DialogForm>
    </Box>
  )
}
