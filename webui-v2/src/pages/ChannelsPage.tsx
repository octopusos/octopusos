/**
 * ChannelsPage - Communication Channels
 *
 * Phase 6.1 Batch 9: API Integration
 * - Integrated with /api/communication/status API
 * - Removed mock data
 * - Real-time channel management
 */

import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { usePageHeader, usePageActions } from '@/ui/layout'
import { CardCollectionWrap, ItemCard, type ItemCardMeta, type ItemCardAction } from '@/ui'
import { K, useTextTranslation } from '@/ui/text'
import { DialogForm } from '@/ui/interaction'
import { RefreshIcon, ChatBubbleIcon, ErrorIcon, CancelIcon, CheckCircleIcon, EmailIcon } from '@/ui/icons'
import { TextField, Select, MenuItem } from '@/ui'
import { Box, Typography, Grid } from '@mui/material'
import { httpClient } from '@platform/http'
import { systemService } from '@services'
import { providersApi } from '@/api/providers'

// ===================================
// Types
// ===================================

interface Channel {
  id: string
  name: string
  icon: string
  description: string
  provider?: string
  capabilities: string[]
  status: string
  enabled: boolean
  security_mode: string
  last_heartbeat_at?: number
  privacy_badges: string[]
  required_config_fields?: Array<any>
  metadata?: Record<string, any>
}

export default function ChannelsPage() {
  // ===================================
  // i18n Hook - Subscribe to language changes
  // ===================================
  const { t } = useTextTranslation()
  const navigate = useNavigate()

  // Channel manifest field i18n overrides.
  // Manifests are currently English-first; for key fields we provide UI translations here.
  // This keeps dialogs multilingual without requiring manifest schema changes.
  const fieldI18nOverride: Record<
    string,
    { labelKey?: string; placeholderKey?: string; helpKey?: string }
  > = {
    model_route: {
      labelKey: K.page.channels.fieldModelRouteLabel,
      helpKey: K.page.channels.fieldModelRouteHelp,
    },
    provider: {
      labelKey: K.page.channels.fieldLlmProviderLabel,
      placeholderKey: K.page.channels.fieldLlmProviderPlaceholder,
      helpKey: K.page.channels.fieldLlmProviderHelp,
    },
    model: {
      labelKey: K.page.channels.fieldLlmModelLabel,
      placeholderKey: K.page.channels.fieldLlmModelPlaceholder,
      helpKey: K.page.channels.fieldLlmModelHelp,
    },
    state_dir: {
      labelKey: K.page.channels.fieldStateDirLabel,
      placeholderKey: K.page.channels.fieldStateDirPlaceholder,
      helpKey: K.page.channels.fieldStateDirHelp,
    },
    chrome_path: {
      labelKey: K.page.channels.fieldChromePathLabel,
      placeholderKey: K.page.channels.fieldChromePathPlaceholder,
      helpKey: K.page.channels.fieldChromePathHelp,
    },
  }

  const [loading, setLoading] = useState(false)
  const [enabledChannels, setEnabledChannels] = useState<Channel[]>([])
  const [availableChannels, setAvailableChannels] = useState<Channel[]>([])

  // Setup / Connect Dialog
  const [setupDialogOpen, setSetupDialogOpen] = useState(false)
  const [setupChannel, setSetupChannel] = useState<Channel | null>(null)
  const [setupConfig, setSetupConfig] = useState<Record<string, any>>({})
  const [llmProviders, setLlmProviders] = useState<string[]>([])
  const [llmModels, setLlmModels] = useState<string[]>([])

  // QR Dialog
  const [qrDialogOpen, setQrDialogOpen] = useState(false)
  const [qrChannelId, setQrChannelId] = useState<string>('')
  const [qrDataUrl, setQrDataUrl] = useState<string>('')
  const [qrState, setQrState] = useState<string>('idle')

  // Bindings Dialog
  const [bindingsDialogOpen, setBindingsDialogOpen] = useState(false)
  const [bindingsChannel, setBindingsChannel] = useState<Channel | null>(null)
  const [bindingsLoading, setBindingsLoading] = useState(false)
  const [bindings, setBindings] = useState<Array<Record<string, any>>>([])
  const [bindingPatch, setBindingPatch] = useState<Record<string, any>>({})
  const [selectedBindingId, setSelectedBindingId] = useState<string>('')

  const localizeChannelName = (ch: Channel): string => {
    if (ch.id === 'whatsapp_web') return t(K.page.channels.channelNameWhatsappWeb)
    if (ch.id === 'whatsapp_twilio') return t(K.page.channels.channelNameWhatsappTwilio)
    if (ch.id === 'telegram') return t(K.page.channels.channelNameTelegram)
    if (ch.id === 'slack') return t(K.page.channels.channelNameSlack)
    return ch.name
  }

  const localizeChannelNameById = (id: string, fallbackName: string): string => {
    const ch: Channel = {
      id,
      name: fallbackName,
      icon: '',
      description: '',
      capabilities: [],
      status: '',
      enabled: false,
      security_mode: '',
      privacy_badges: [],
    }
    return localizeChannelName(ch)
  }

  const localizeChannelDescription = (ch: Channel): string => {
    if (ch.id === 'whatsapp_web') return t(K.page.channels.channelDescWhatsappWeb)
    if (ch.id === 'whatsapp_twilio') return t(K.page.channels.channelDescWhatsappTwilio)
    if (ch.id === 'telegram') return t(K.page.channels.channelDescTelegram)
    if (ch.id === 'slack') return t(K.page.channels.channelDescSlack)
    return ch.description
  }

  const localizeChannelState = (stateRaw: string): string => {
    const s = (stateRaw || '').trim()
    if (!s) return t(K.page.channels.stateUnknown)
    if (s === 'enabled') return t(K.page.channels.stateEnabled)
    if (s === 'disabled') return t(K.page.channels.stateDisabled)
    if (s === 'error') return t(K.page.channels.stateError)
    if (s === 'needs_setup') return t(K.page.channels.stateNeedsSetup)
    if (s === 'starting') return t(K.page.channels.stateStarting)
    if (s === 'needs_qr') return t(K.page.channels.stateNeedsQr)
    if (s === 'ready') return t(K.page.channels.stateReady)
    return s
  }

  // ===================================
  // LLM Provider/Model Options (reuse ChatPage logic)
  // ===================================

  const loadModelsForProvider = useCallback(async (targetProvider: string, currentModel: string) => {
    if (!targetProvider) {
      setLlmModels([])
      setSetupConfig((prev) => ({ ...prev, model: '' }))
      return
    }
    try {
      const modelsResp = await providersApi.getProviderModels(targetProvider)
      const loadedModels = Array.isArray(modelsResp?.models)
        ? modelsResp.models
            .map((m: any) => m?.id || m?.name || m?.label)
            .filter((v: any) => typeof v === 'string' && v.trim().length > 0)
        : []
      setLlmModels(loadedModels)
      if (loadedModels.length > 0 && !loadedModels.includes(currentModel)) {
        setSetupConfig((prev) => ({ ...prev, model: loadedModels[0] }))
      }
      return
    } catch (e) {
      console.warn(`[ChannelsPage] Failed to load models for provider=${targetProvider}, falling back to installed models`, e)
    }

    try {
      const installedResp = await systemService.listModelsApiModelsListGet()
      const providerModels = Array.isArray(installedResp?.models)
        ? installedResp.models
            .filter((m: any) => m?.provider === targetProvider)
            .map((m: any) => m?.name)
            .filter((v: any) => typeof v === 'string' && v.trim().length > 0)
        : []
      setLlmModels(providerModels)
      if (providerModels.length > 0 && !providerModels.includes(currentModel)) {
        setSetupConfig((prev) => ({ ...prev, model: providerModels[0] }))
      }
    } catch (installedError) {
      console.warn('[ChannelsPage] Failed to load installed models fallback:', installedError)
      setLlmModels([])
      setSetupConfig((prev) => ({ ...prev, model: '' }))
    }
  }, [])

  const loadProvidersAndModelsForSetup = useCallback(async () => {
    if (!setupDialogOpen) return
    const modeRaw = String(setupConfig?.model_route || 'local').trim()
    const mode = modeRaw === 'cloud' ? 'cloud' : 'local'
    const currentProvider = String(setupConfig?.provider || '').trim()
    const currentModel = String(setupConfig?.model || '').trim()

    try {
      // Read-only warm-up for provider status cache (best-effort)
      try {
        await providersApi.getProvidersStatus()
      } catch (statusError) {
        console.warn('[ChannelsPage] Failed to read provider status:', statusError)
      }

      const providersResp = await systemService.listProvidersApiProvidersGet()
      const local = Array.isArray(providersResp?.local) ? providersResp.local : []
      const cloud = Array.isArray(providersResp?.cloud) ? providersResp.cloud : []
      const filteredProviders =
        mode === 'local'
          ? local.map((p: any) => p?.id).filter(Boolean)
          : cloud.map((p: any) => p?.id).filter(Boolean)

      setLlmProviders(filteredProviders)

      if (currentProvider && filteredProviders.includes(currentProvider)) {
        await loadModelsForProvider(currentProvider, currentModel)
        return
      }

      if (filteredProviders.length > 0) {
        const firstProvider = filteredProviders[0]
        setSetupConfig((prev) => ({ ...prev, provider: firstProvider, model: '' }))
        await loadModelsForProvider(firstProvider, '')
        return
      }

      // no providers
      setLlmModels([])
      setSetupConfig((prev) => ({ ...prev, provider: '', model: '' }))
    } catch (error) {
      console.warn('[ChannelsPage] Failed to load providers/models:', error)
      setLlmProviders([])
      setLlmModels([])
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [setupDialogOpen, setupConfig?.model_route])

  useEffect(() => {
    // Load provider/model options only when the setup dialog is open.
    if (!setupDialogOpen) return
    loadProvidersAndModelsForSetup()
  }, [setupDialogOpen, loadProvidersAndModelsForSetup])

  // ===================================
  // Data Loading
  // ===================================

  const loadChannels = async () => {
    setLoading(true)
    try {
      const response = await httpClient.get<{ items?: Array<Record<string, any>> }>('/api/channels-marketplace')
      const rawItems = Array.isArray(response.data?.items) ? response.data.items : []
      const normalized: Channel[] = rawItems.map((ch, idx) => ({
        id: String(ch?.id || `channel-${idx}`),
        name: String(ch?.name || ch?.id || `Channel ${idx + 1}`),
        icon: String(ch?.icon || 'chat'),
        description: String(ch?.description || ''),
        provider: typeof ch?.provider === 'string' ? ch.provider : undefined,
        capabilities: Array.isArray(ch?.capabilities) ? ch.capabilities.map(String) : [],
        status: String(ch?.status || (ch?.enabled ? 'enabled' : 'disabled')),
        enabled: Boolean(ch?.enabled ?? ch?.status === 'enabled'),
        security_mode: String(ch?.security_mode || 'chat_only'),
        last_heartbeat_at: typeof ch?.last_heartbeat_at === 'number' ? ch.last_heartbeat_at : undefined,
        privacy_badges: Array.isArray(ch?.privacy_badges) ? ch.privacy_badges.map(String) : [],
        required_config_fields: Array.isArray(ch?.required_config_fields) ? ch.required_config_fields : [],
        metadata: typeof ch?.metadata === 'object' && ch?.metadata ? ch.metadata : {},
      }))
      setEnabledChannels(normalized.filter((c) => c.enabled))
      setAvailableChannels(normalized.filter((c) => !c.enabled))
    } catch (error) {
      console.error('Failed to load channels:', error)
      setEnabledChannels([])
      setAvailableChannels([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadChannels()
  }, [])

  // ===================================
  // Page Header
  // ===================================
  usePageHeader({
    title: t(K.page.channels.title),
    subtitle: t(K.page.channels.subtitle),
  })

  usePageActions([
    {
      key: 'refresh',
      label: t('common.refresh'),
      icon: <RefreshIcon />,
      variant: 'outlined',
      onClick: loadChannels,
    },
  ])

  // ===================================
  // Dialog Handlers
  // ===================================
  const openSetup = (channel: Channel) => {
    setSetupChannel(channel)
    const defaults: Record<string, any> = {}
    for (const f of channel.required_config_fields || []) {
      const name = String(f?.name || '')
      if (!name) continue
      if (f?.default !== undefined && f?.default !== null && f?.default !== '') defaults[name] = f.default
    }
    setSetupConfig(defaults)
    setSetupDialogOpen(true)
  }

  const submitSetupAndConnect = async () => {
    const ch = setupChannel
    if (!ch) return
    setQrState('configuring')
    try {
      await httpClient.post(`/api/channels/${encodeURIComponent(ch.id)}/configure`, { config: setupConfig })
      await httpClient.post(`/api/channels/${encodeURIComponent(ch.id)}/enable`, {})
      const connect = await httpClient.post<{ state?: string }>(`/api/channels/${encodeURIComponent(ch.id)}/connect`, {})
      const state = String(connect.data?.state || '')
      setSetupDialogOpen(false)
      if (ch.id === 'whatsapp_web' && state !== 'ready') {
        setQrChannelId(ch.id)
        setQrDialogOpen(true)
        setQrState(state || 'starting')
      } else if (state === 'needs_qr') {
        setQrChannelId(ch.id)
        setQrDialogOpen(true)
        setQrState('needs_qr')
      } else {
        setQrState(state || 'ready')
      }
      await loadChannels()
    } catch (e) {
      console.error('Failed to setup/connect channel:', e)
      setQrState('error')
    }
  }

  const refreshQrAndStatus = async (channelId: string) => {
    try {
      const st = await httpClient.get(`/api/channels/${encodeURIComponent(channelId)}/status`)
      const state = String(st.data?.status?.state || '')
      setQrState(state || 'unknown')
      if (state === 'needs_qr') {
        const qr = await httpClient.get(`/api/channels/${encodeURIComponent(channelId)}/qr`)
        const dataUrl = String(qr.data?.qr?.qr_data_url || '')
        setQrDataUrl(dataUrl)
      }
      if (state === 'ready') {
        setQrDialogOpen(false)
        await loadChannels()
      }
    } catch (e) {
      console.error('Failed to refresh QR/status:', e)
    }
  }

  useEffect(() => {
    if (!qrDialogOpen || !qrChannelId) return
    refreshQrAndStatus(qrChannelId)
    const timer = window.setInterval(() => refreshQrAndStatus(qrChannelId), 2500)
    return () => window.clearInterval(timer)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [qrDialogOpen, qrChannelId])

  const openBindings = async (channel: Channel) => {
    setBindingsChannel(channel)
    setBindingsDialogOpen(true)
    setBindingsLoading(true)
    try {
      const resp = await httpClient.get(`/api/channels/${encodeURIComponent(channel.id)}/bindings`)
      const items = Array.isArray(resp.data?.bindings) ? resp.data.bindings : []
      setBindings(items)
      const first = String(items[0]?.binding_id || '')
      setSelectedBindingId(first)
      if (items[0]) {
        setBindingPatch({
          model_route: items[0].model_route,
          provider: items[0].provider,
          model: items[0].model,
        })
      } else {
        setBindingPatch({})
      }
    } catch (e) {
      console.error('Failed to load bindings:', e)
      setBindings([])
    } finally {
      setBindingsLoading(false)
    }
  }

  const switchSelectedBinding = async () => {
    const ch = bindingsChannel
    const bid = selectedBindingId
    if (!ch || !bid) return
    try {
      await httpClient.post(`/api/channels/${encodeURIComponent(ch.id)}/bindings/${encodeURIComponent(bid)}/switch`, {
        model_route: bindingPatch.model_route,
        provider: bindingPatch.provider,
        model: bindingPatch.model,
      })
      await openBindings(ch)
    } catch (e) {
      console.error('Failed to switch binding:', e)
    }
  }

  // ===================================
  // Transform Channels to Cards
  // ===================================
  const getChannelIcon = (status: string) => {
    if (status === 'enabled') return <CheckCircleIcon />
    if (status === 'error') return <ErrorIcon />
    if (status === 'disabled') return <CancelIcon />
    return <ChatBubbleIcon />
  }

  const getStatusColor = (status: string): 'success' | 'error' | 'warning' | 'default' => {
    if (status === 'enabled') return 'success'
    if (status === 'error') return 'error'
    if (status === 'disabled' || status === 'needs_setup') return 'default'
    return 'warning'
  }

  const transformedEnabledChannels = enabledChannels.map((channel) => ({
    id: channel.id,
    title: localizeChannelName(channel),
    description: localizeChannelDescription(channel),
    icon: getChannelIcon(channel.status),
    meta: [
      { key: 'provider', label: t(K.page.channels.type), value: channel.provider || 'N/A' },
      {
        key: 'status',
        label: t(K.page.channels.status),
        value: localizeChannelState(channel.status),
        color: getStatusColor(channel.status),
      },
      { key: 'capabilities', label: t(K.page.channels.capabilities), value: channel.capabilities.join(', ') },
    ] as ItemCardMeta[],
    actions: [
      { key: 'configure', label: t(K.page.channels.configure), onClick: () => openSetup(channel) },
      { key: 'bindings', label: t(K.page.channels.bindings), onClick: () => openBindings(channel) },
    ] as ItemCardAction[],
  }))

  const transformedAvailableChannels = availableChannels.map((channel) => ({
    id: channel.id,
    title: localizeChannelName(channel),
    description: localizeChannelDescription(channel),
    icon: getChannelIcon(channel.status),
    meta: [
      { key: 'provider', label: t(K.page.channels.type), value: channel.provider || 'N/A' },
      {
        key: 'status',
        label: t(K.page.channels.status),
        value: localizeChannelState(channel.status),
        color: getStatusColor(channel.status),
      },
    ] as ItemCardMeta[],
    actions: [
      { key: 'setup', label: t(K.page.channels.setup), onClick: () => openSetup(channel) },
    ] as ItemCardAction[],
  }))

  // ===================================
  // Render: Two Sections
  // ===================================
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      {/* Built-in / Work Channels */}
      <Box>
        <Typography variant="h6" sx={{ mb: 2 }}>
          {t(K.nav.channels)}
        </Typography>
        <CardCollectionWrap loading={false}>
          <ItemCard
            key="email"
            title={t(K.page.emailChannel.title)}
            description={t(K.page.emailChannel.subtitle)}
            icon={<EmailIcon />}
            meta={[]}
            actions={[
              {
                key: 'view',
                label: t(K.common.view),
                onClick: () => navigate('/channels/email'),
              },
            ]}
          />
        </CardCollectionWrap>
      </Box>

      {/* Your Channels Section */}
      <Box>
        <Typography variant="h6" sx={{ mb: 2 }}>
          {t(K.page.channels.yourChannels)}
        </Typography>
        <CardCollectionWrap loading={loading}>
          {transformedEnabledChannels.length > 0 ? (
            transformedEnabledChannels.map((channel) => (
              <ItemCard
                key={channel.id}
                title={channel.title}
                description={channel.description}
                icon={channel.icon}
                meta={channel.meta}
                actions={channel.actions}
              />
            ))
          ) : (
            <Typography variant="body2" color="text.secondary">
              {t(K.page.channels.noEnabledChannels)}
            </Typography>
          )}
        </CardCollectionWrap>
      </Box>

      {/* Available Channels Section */}
      <Box>
        <Typography variant="h6" sx={{ mb: 2 }}>
          {t(K.page.channels.availableChannels)}
        </Typography>
        <CardCollectionWrap loading={loading}>
          {transformedAvailableChannels.length > 0 ? (
            transformedAvailableChannels.map((channel) => (
              <ItemCard
                key={channel.id}
                title={channel.title}
                description={channel.description}
                icon={channel.icon}
                meta={channel.meta}
                actions={channel.actions}
              />
            ))
          ) : (
            <Typography variant="body2" color="text.secondary">
              {t(K.page.channels.allChannelsEnabled)}
            </Typography>
          )}
        </CardCollectionWrap>
      </Box>

      {/* Create Channel Dialog */}
      <DialogForm
        open={setupDialogOpen}
        onClose={() => setSetupDialogOpen(false)}
        title={
          setupChannel
            ? `${t(K.page.channels.configure)}: ${localizeChannelName(setupChannel)}`
            : t(K.page.channels.configure)
        }
        submitText={t(K.page.channels.connect)}
        cancelText={t('common.cancel')}
        onSubmit={submitSetupAndConnect}
        submitDisabled={
          !setupChannel ||
          (setupChannel.required_config_fields || []).some((f) => {
            if (!f?.required) return false
            const key = String(f?.name || '')
            if (!key) return false
            const v = setupConfig[key]
            return v === undefined || v === null || String(v).trim() === ''
          })
        }
      >
        <Grid container spacing={2}>
          {(setupChannel?.required_config_fields || []).map((f) => {
            const key = String(f?.name || '')
            if (!key) return null
            const type = String(f?.type || 'text')
            const override = fieldI18nOverride[key]
            const label = override?.labelKey ? t(override.labelKey) : String(f?.label || key)
            const required = Boolean(f?.required)
            const placeholder = override?.placeholderKey
              ? t(override.placeholderKey)
              : String(f?.placeholder || '')
            const help = override?.helpKey ? t(override.helpKey) : String(f?.help_text || '')
            const value = setupConfig[key] ?? ''
            // Provider/Model: prefer dropdown selection (Chat-like ModelBar) over free text.
            // Fall back to TextField if provider/model options are unavailable.
            if (key === 'provider' && llmProviders.length > 0) {
              return (
                <Grid item xs={12} key={key}>
                  <Select
                    label={label}
                    fullWidth
                    value={String(value)}
                    onChange={async (e) => {
                      const nextProvider = String(e.target.value || '')
                      setSetupConfig((prev) => ({ ...prev, provider: nextProvider, model: '' }))
                      await loadModelsForProvider(nextProvider, '')
                    }}
                    required={required}
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
                  {help ? (
                    <Typography variant="caption" color="text.secondary">
                      {help}
                    </Typography>
                  ) : null}
                </Grid>
              )
            }
            if (key === 'model' && llmProviders.length > 0) {
              const selectedProvider = String(setupConfig?.provider || '').trim()
              if (llmModels.length > 0) {
                return (
                  <Grid item xs={12} key={key}>
                    <Select
                      label={label}
                      fullWidth
                      value={String(value)}
                      onChange={(e) => setSetupConfig((prev) => ({ ...prev, model: e.target.value }))}
                      required={required}
                      disabled={!selectedProvider}
                    >
                      {llmModels.map((m) => (
                        <MenuItem key={m} value={m}>
                          {m}
                        </MenuItem>
                      ))}
                    </Select>
                    {help ? (
                      <Typography variant="caption" color="text.secondary">
                        {help}
                      </Typography>
                    ) : null}
                  </Grid>
                )
              }
              // Provider dropdown is available but models list is empty: keep a dropdown shell to signal state.
              return (
                <Grid item xs={12} key={key}>
                  <Select
                    label={label}
                    fullWidth
                    value={String(value)}
                    onChange={(e) => setSetupConfig((prev) => ({ ...prev, model: e.target.value }))}
                    required={required}
                    disabled={!selectedProvider}
                  >
                    <MenuItem value="">
                      <em>{t('page.chat.noModels')}</em>
                    </MenuItem>
                  </Select>
                  {help ? (
                    <Typography variant="caption" color="text.secondary">
                      {help}
                    </Typography>
                  ) : null}
                </Grid>
              )
            }
            if (type === 'select') {
              const options = Array.isArray(f?.options) ? f.options : []
              return (
                <Grid item xs={12} key={key}>
                  <Select
                    label={label}
                    fullWidth
                    value={String(value)}
                    onChange={async (e) => {
                      setSetupConfig((prev) => ({ ...prev, [key]: e.target.value }))
                      // If switching local/cloud mode in the setup dialog, refresh providers/models.
                      if (key === 'model_route') {
                        // Defer to the next tick so setupConfig updates land first.
                        setTimeout(() => {
                          loadProvidersAndModelsForSetup()
                        }, 0)
                      }
                    }}
                    required={required}
                  >
                    {options.map((opt: any) => (
                      <MenuItem key={String(opt)} value={String(opt)}>
                        {String(opt)}
                      </MenuItem>
                    ))}
                  </Select>
                  {help ? (
                    <Typography variant="caption" color="text.secondary">
                      {help}
                    </Typography>
                  ) : null}
                </Grid>
              )
            }
            return (
              <Grid item xs={12} key={key}>
                <TextField
                  label={label}
                  placeholder={placeholder}
                  value={String(value)}
                  onChange={(e) => setSetupConfig((prev) => ({ ...prev, [key]: e.target.value }))}
                  fullWidth
                  required={required}
                  type={type === 'password' ? 'password' : 'text'}
                />
                {help ? (
                  <Typography variant="caption" color="text.secondary">
                    {help}
                  </Typography>
                ) : null}
              </Grid>
            )
          })}
        </Grid>
      </DialogForm>

      {/* QR Dialog */}
      <DialogForm
        open={qrDialogOpen}
        onClose={() => setQrDialogOpen(false)}
        title={t(K.page.channels.qrDialogTitle, { name: localizeChannelNameById(qrChannelId, qrChannelId) })}
        submitText={t('common.refresh')}
        cancelText={t('common.close')}
        onSubmit={() => refreshQrAndStatus(qrChannelId)}
        submitDisabled={!qrChannelId}
      >
        <Grid container spacing={2}>
          <Grid item xs={12}>
            <Typography variant="body2" color="text.secondary">
              {t(K.page.channels.qrStatusLine, { state: localizeChannelState(qrState) })}
            </Typography>
          </Grid>
          <Grid item xs={12}>
            {qrDataUrl ? (
              <Box sx={{ display: 'flex', justifyContent: 'center' }}>
                <img
                  src={qrDataUrl}
                  alt={t(K.page.channels.qrAlt)}
                  style={{ maxWidth: 320, width: '100%' }}
                />
              </Box>
            ) : (
              <Typography variant="body2" color="text.secondary">
                {t(K.page.channels.qrNotAvailable)}
              </Typography>
            )}
          </Grid>
        </Grid>
      </DialogForm>

      {/* Bindings Dialog */}
      <DialogForm
        open={bindingsDialogOpen}
        onClose={() => setBindingsDialogOpen(false)}
        title={
          bindingsChannel
            ? t(K.page.channels.bindingsTitle, {
                name: localizeChannelName(bindingsChannel),
              })
            : t(K.page.channels.bindings)
        }
        submitText={t(K.page.channels.switch)}
        cancelText={t('common.close')}
        onSubmit={switchSelectedBinding}
        submitDisabled={!selectedBindingId || bindingsLoading}
      >
        <Grid container spacing={2}>
          <Grid item xs={12}>
            <Typography variant="body2" color="text.secondary">
              {t(K.page.channels.bindingsHint)}
            </Typography>
          </Grid>
          <Grid item xs={12}>
            <Select
              label={t(K.page.channels.binding)}
              fullWidth
              value={selectedBindingId}
              onChange={(e) => {
                const bid = String(e.target.value)
                setSelectedBindingId(bid)
                const b = bindings.find((x) => String(x.binding_id) === bid)
                if (b) {
                  setBindingPatch({ model_route: b.model_route, provider: b.provider, model: b.model })
                }
              }}
              disabled={bindingsLoading || bindings.length === 0}
            >
              {bindings.map((b) => (
                <MenuItem key={String(b.binding_id)} value={String(b.binding_id)}>
                  {String(b.user_key)} ({String(b.model_route)} / {String(b.provider)} / {String(b.model)})
                </MenuItem>
              ))}
            </Select>
          </Grid>
          <Grid item xs={12}>
            <Select
              label={t(K.page.channels.modeLocalCloud)}
              fullWidth
              value={String(bindingPatch.model_route || '')}
              onChange={(e) => setBindingPatch((p) => ({ ...p, model_route: e.target.value }))}
              disabled={bindingsLoading || !selectedBindingId}
            >
              <MenuItem value="local">{t(K.page.channels.valueLocal)}</MenuItem>
              <MenuItem value="cloud">{t(K.page.channels.valueCloud)}</MenuItem>
            </Select>
          </Grid>
          <Grid item xs={12}>
            <TextField
              label={t(K.page.channels.provider)}
              fullWidth
              value={String(bindingPatch.provider || '')}
              onChange={(e) => setBindingPatch((p) => ({ ...p, provider: e.target.value }))}
              disabled={bindingsLoading || !selectedBindingId}
            />
          </Grid>
          <Grid item xs={12}>
            <TextField
              label={t(K.page.channels.model)}
              fullWidth
              value={String(bindingPatch.model || '')}
              onChange={(e) => setBindingPatch((p) => ({ ...p, model: e.target.value }))}
              disabled={bindingsLoading || !selectedBindingId}
            />
          </Grid>
        </Grid>
      </DialogForm>
    </Box>
  )
}
