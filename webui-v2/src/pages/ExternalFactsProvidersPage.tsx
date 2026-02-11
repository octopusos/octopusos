import { useEffect, useMemo, useState } from 'react'
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  Grid,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Stack,
  Switch,
  TextField,
  Typography,
} from '@mui/material'
import ExpandMoreIcon from '@mui/icons-material/ExpandMore'

import { del, get, post } from '@platform/http/httpClient'
import { clearToken, getToken, setToken } from '@platform/auth/adminToken'
import { usePageHeader } from '@/ui/layout'
import { K, useTextTranslation } from '@/ui/text'

type FactKind =
  | 'weather' | 'fx' | 'stock' | 'crypto' | 'index' | 'etf' | 'bond_yield' | 'commodity'
  | 'flight' | 'train' | 'hotel' | 'shipping' | 'package' | 'fuel_price' | 'news' | 'sports'
  | 'calendar' | 'traffic' | 'air_quality' | 'earthquake' | 'power_outage'

type ProviderItem = {
  provider_id: string
  kind: FactKind
  name: string
  endpoint_url: string
  api_key: string
  has_api_key: boolean
  api_key_header: string
  priority: number
  enabled: boolean
  config: Record<string, unknown>
  supported_items?: Record<string, string[]>
  endpoint_map?: Record<string, unknown>
  endpoint_map_schema_valid?: boolean
  last_validation_error?: string
  created_at: string
  updated_at: string
}

type ProviderListResponse = { ok: boolean; data: ProviderItem[] }

type TestResponse = {
  ok: boolean
  data: {
    provider_id: string
    query: string
    result: {
      status: string
      fallback_text: string
    }
  }
}

type RegistryItem = {
  item_id: string
  output_kind: 'point' | 'series' | 'table'
  placeholders: string[]
  required: string[]
}

type RegistryCapability = {
  capability_id: string
  items: RegistryItem[]
}

type RegistryResponse = { ok: boolean; data: RegistryCapability[] }

type InferMappingResponse = {
  ok: boolean
  data: {
    provider_id: string
    endpoint_key: string
    sample_id: string
    proposal_id: string
    proposal: Record<string, unknown>
    confidence: number
    validation_report: Record<string, unknown>
    can_apply: boolean
    endpoint: { url: string; method: string }
  }
}

type ApplyMappingResponse = {
  ok: boolean
  data: {
    version: Record<string, unknown>
    status: string
  }
}

type MappingHistoryResponse = {
  ok: boolean
  data: {
    provider_id: string
    endpoint_key: string
    active_version_id?: string | null
    versions: Array<Record<string, unknown>>
    proposals: Array<Record<string, unknown>>
    samples: Array<Record<string, unknown>>
  }
}

type MappingVersionItem = {
  id: string
  version: number
  status: string
  fail_count?: number
  approved_at?: string | null
  mapping_json?: Record<string, unknown>
}

type BindingItem = {
  binding_id: string
  capability_id: string
  item_id: string
  connector_id: string
  endpoint_id: string
  profile_version_id?: string | null
  status: string
}

type ConnectorEndpointOption = {
  connector_id: string
  connector_name: string
  endpoint_id: string
  endpoint_key: string
  name: string
  method: string
  path: string
  capability_id: string
  item_id: string
}

type EndpointKey =
  | 'status'
  | 'currencies'
  | 'latest'
  | 'historical'
  | 'range_historical'
  | 'convert'

type EndpointMethod = 'GET'
type EndpointResponseKind = 'point' | 'series' | 'table'

type EndpointConfig = {
  enabled: boolean
  method: EndpointMethod
  path: string
  responseKind: EndpointResponseKind
  pointsPath: string
  timePath: string
  valuePath: string
  summaryPath: string
}

type ProviderPreset = {
  id: string
  label: string
  kind: FactKind
  baseUrl: string
  apiKeyHeader: string
  endpoints: Partial<Record<EndpointKey, Partial<EndpointConfig>>>
}

type DialogMode = 'create' | 'edit' | 'clone'
type FxGoal = 'spot' | 'series' | 'convert'
type SelfCheckStatus = 'pass' | 'warn' | 'fail'
type SelfCheckAction = 'open_connectors' | 'refresh_data' | 'auto_select_endpoint' | 'set_admin_token'
type SelfCheckItem = {
  key: string
  title: string
  status: SelfCheckStatus
  detail: string
  action?: SelfCheckAction
  actionLabel?: string
}

const SELECT_MENU_PROPS = {
  disableAutoFocusItem: true,
  MenuListProps: { autoFocusItem: false },
}

const ENABLE_LEGACY_ENDPOINT_EDITOR = false

function blurActiveElement() {
  const active = document.activeElement
  if (active instanceof HTMLElement) active.blur()
}

const FACT_KINDS: FactKind[] = [
  'weather', 'fx', 'stock', 'crypto', 'index', 'etf', 'bond_yield', 'commodity',
  'flight', 'train', 'hotel', 'shipping', 'package', 'fuel_price', 'news', 'sports',
  'calendar', 'traffic', 'air_quality', 'earthquake', 'power_outage',
]

const ENDPOINT_ORDER: EndpointKey[] = [
  'status',
  'currencies',
  'latest',
  'historical',
  'range_historical',
  'convert',
]

function endpointLabel(key: EndpointKey): string {
  return key
}

function endpointToCapabilityItem(formKind: FactKind, endpoint: EndpointKey): { capabilityId: string; itemId: string } | null {
  if (formKind === 'fx') {
    if (endpoint === 'latest' || endpoint === 'convert') return { capabilityId: 'exchange_rate', itemId: 'spot' }
    if (endpoint === 'historical' || endpoint === 'range_historical') return { capabilityId: 'exchange_rate', itemId: 'series' }
  }
  return null
}

function kindLabel(t: (key: string) => string, kind: FactKind): string {
  return t(`page.externalFactsPolicy.kindOption.${kind}`)
}

const defaultEndpointConfig = (key: EndpointKey): EndpointConfig => ({
  enabled: key === 'latest',
  method: 'GET',
  path: '',
  responseKind: key === 'range_historical' ? 'series' : 'point',
  pointsPath: 'data',
  timePath: key === 'range_historical' ? 'key' : 'meta.last_updated_at',
  valuePath: key === 'range_historical' ? '{quote}.value' : 'data.{quote}.value',
  summaryPath: '',
})

const emptyEndpoints = (): Record<EndpointKey, EndpointConfig> => ({
  status: defaultEndpointConfig('status'),
  currencies: defaultEndpointConfig('currencies'),
  latest: defaultEndpointConfig('latest'),
  historical: defaultEndpointConfig('historical'),
  range_historical: defaultEndpointConfig('range_historical'),
  convert: defaultEndpointConfig('convert'),
})

const PRESETS: ProviderPreset[] = [
  {
    id: 'fx-currencyapi',
    label: 'CurrencyAPI',
    kind: 'fx',
    baseUrl: 'https://api.currencyapi.com',
    apiKeyHeader: 'apikey',
    endpoints: {
      status: { enabled: true, path: '/v3/status', responseKind: 'point' },
      currencies: { enabled: true, path: '/v3/currencies', responseKind: 'table' },
      latest: { enabled: true, path: '/v3/latest?base_currency={base}&currencies={quote}', responseKind: 'point', valuePath: 'data.{quote}.value', timePath: 'meta.last_updated_at' },
      historical: { enabled: true, path: '/v3/historical?date={from_iso}&base_currency={base}&currencies={quote}', responseKind: 'point', valuePath: 'data.{quote}.value', timePath: 'meta.last_updated_at' },
      range_historical: { enabled: true, path: '/v3/range?datetime_start={from_iso_z}&datetime_end={to_iso_z}&base_currency={base}&currencies={quote}', responseKind: 'series', pointsPath: 'data', timePath: 'key', valuePath: '{quote}.value' },
      convert: { enabled: true, path: '/v3/convert?base_currency={base}&currencies={quote}&value=1', responseKind: 'point', valuePath: 'data.{quote}.value' },
    },
  },
  {
    id: 'fx-currencylayer',
    label: 'CurrencyLayer',
    kind: 'fx',
    baseUrl: 'https://api.currencylayer.com',
    apiKeyHeader: 'apikey',
    endpoints: {
      latest: { enabled: true, path: '/live?source={base}&currencies={quote}', responseKind: 'point', valuePath: 'quotes.{base}{quote}', timePath: 'timestamp' },
    },
  },
  {
    id: 'fx-exchangerate-host',
    label: 'ExchangeRate.host',
    kind: 'fx',
    baseUrl: 'https://api.exchangerate.host',
    apiKeyHeader: 'apikey',
    endpoints: {
      latest: { enabled: true, path: '/latest?base={base}&symbols={quote}', responseKind: 'point', valuePath: 'rates.{quote}', timePath: 'date' },
      range_historical: { enabled: true, path: '/timeseries?start_date={from_iso}&end_date={to_iso}&base={base}&symbols={quote}', responseKind: 'series', pointsPath: 'rates', timePath: 'key', valuePath: '{quote}' },
    },
  },
]

const emptyForm = {
  provider_id: '',
  kind: 'fx' as FactKind,
  name: '',
  base_url: '',
  api_key: '',
  api_key_header: 'Authorization',
  priority: 10,
  enabled: true,
  query_suffix: '',
  capability_text: '',
  endpoints: emptyEndpoints(),
}

function buildAbsoluteUrl(baseUrl: string, pathOrUrl: string): string {
  const raw = pathOrUrl.trim()
  if (!raw) return ''
  if (/^https?:\/\//i.test(raw)) return raw
  const base = baseUrl.trim().replace(/\/+$/, '')
  if (!base) return raw
  return raw.startsWith('/') ? `${base}${raw}` : `${base}/${raw}`
}

function mapToEndpointMap(baseUrl: string, endpoints: Record<EndpointKey, EndpointConfig>): Record<string, unknown> {
  const out: Record<string, unknown> = {}
  for (const key of ENDPOINT_ORDER) {
    const cfg = endpoints[key]
    if (!cfg.enabled || !cfg.path.trim()) continue
    out[key] = buildAbsoluteUrl(baseUrl, cfg.path)
  }
  return out
}

function parsePathFromUrl(baseUrl: string, url: string): string {
  const base = baseUrl.trim().replace(/\/+$/, '')
  if (!base) return url
  return url.startsWith(base) ? (url.slice(base.length) || '/') : url
}

export default function ExternalFactsProvidersPage() {
  const { t } = useTextTranslation()
  usePageHeader({
    title: t(K.page.externalFactsProviders.title),
    subtitle: t(K.page.externalFactsProviders.subtitle),
  })

  const [kindFilter, setKindFilter] = useState<'all' | FactKind>('all')
  const [items, setItems] = useState<ProviderItem[]>([])
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [testingId, setTestingId] = useState<string | null>(null)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [testResult, setTestResult] = useState('')
  const [adminTokenInput, setAdminTokenInput] = useState(() => getToken() || '')
  const [form, setForm] = useState({ ...emptyForm })
  const [presetId, setPresetId] = useState('')
  const [registry, setRegistry] = useState<RegistryCapability[]>([])
  const [editingProviderId, setEditingProviderId] = useState<string | null>(null)
  const [formOpen, setFormOpen] = useState(false)
  const [dialogMode, setDialogMode] = useState<DialogMode>('create')
  const [previewItem, setPreviewItem] = useState<ProviderItem | null>(null)
  const [endpointEditKey, setEndpointEditKey] = useState<EndpointKey | null>(null)
  const [sampleJsonInput, setSampleJsonInput] = useState('')
  const [proposalId, setProposalId] = useState<string | null>(null)
  const [sampleId, setSampleId] = useState<string | null>(null)
  const [proposalPreview, setProposalPreview] = useState<Record<string, unknown> | null>(null)
  const [validationPreview, setValidationPreview] = useState<Record<string, unknown> | null>(null)
  const [canApplyProposal, setCanApplyProposal] = useState(false)
  const [mappingHistory, setMappingHistory] = useState<MappingHistoryResponse['data'] | null>(null)
  const [mappingLoading, setMappingLoading] = useState(false)
  const [mappingPhase, setMappingPhase] = useState<'idle' | 'llm' | 'validate' | 'apply'>('idle')
  const [mappingStatusText, setMappingStatusText] = useState('')
  const [mappingStatusLevel, setMappingStatusLevel] = useState<'info' | 'success' | 'error'>('info')
  const [endpointExpertMode, setEndpointExpertMode] = useState(false)
  const [rollbackVersion, setRollbackVersion] = useState<MappingVersionItem | null>(null)
  const [historyDialogOpen, setHistoryDialogOpen] = useState(false)
  const [historyPreviewVersion, setHistoryPreviewVersion] = useState<MappingVersionItem | null>(null)
  const [bindings, setBindings] = useState<BindingItem[]>([])
  const [bindingCapabilityId, setBindingCapabilityId] = useState('exchange_rate')
  const [bindingItemId, setBindingItemId] = useState('spot')
  const [connectorEndpoints, setConnectorEndpoints] = useState<ConnectorEndpointOption[]>([])
  const [selectedEndpointRef, setSelectedEndpointRef] = useState('')
  const [fxWizardPresetId, setFxWizardPresetId] = useState('fx-currencyapi')
  const [fxWizardGoal, setFxWizardGoal] = useState<FxGoal>('spot')
  const [selfCheckLoading, setSelfCheckLoading] = useState(false)
  const [selfCheckItems, setSelfCheckItems] = useState<SelfCheckItem[]>([])

  const filtered = useMemo(
    () => (kindFilter === 'all' ? items : items.filter((x) => x.kind === kindFilter)),
    [items, kindFilter]
  )

  const presetOptions = useMemo(
    () => PRESETS.filter((preset) => preset.kind === form.kind),
    [form.kind]
  )

  const endpointMapPreview = useMemo(
    () => JSON.stringify(mapToEndpointMap(form.base_url, form.endpoints), null, 2),
    [form.base_url, form.endpoints]
  )

  const endpointEditing = endpointEditKey ? form.endpoints[endpointEditKey] : null
  const compatibleEndpoints = useMemo(
    () => connectorEndpoints.filter((opt) => opt.capability_id === bindingCapabilityId && opt.item_id === bindingItemId),
    [connectorEndpoints, bindingCapabilityId, bindingItemId],
  )
  const selectedEndpointCompatible = compatibleEndpoints.some(
    (opt) => `${opt.connector_id}:${opt.endpoint_id}` === selectedEndpointRef,
  )
  const selfCheckSummary = useMemo(
    () => ({
      pass: selfCheckItems.filter((x) => x.status === 'pass').length,
      warn: selfCheckItems.filter((x) => x.status === 'warn').length,
      fail: selfCheckItems.filter((x) => x.status === 'fail').length,
    }),
    [selfCheckItems],
  )

  useEffect(() => {
    void loadRegistry()
    void loadBindings()
    void loadConnectorEndpoints()
  }, [])

  useEffect(() => {
    void load()
  }, [kindFilter])

  useEffect(() => {
    if (!endpointEditKey) {
      setSampleJsonInput('')
      setProposalId(null)
      setSampleId(null)
      setProposalPreview(null)
      setValidationPreview(null)
      setCanApplyProposal(false)
      setMappingHistory(null)
      setMappingPhase('idle')
      setMappingStatusText('')
      setMappingStatusLevel('info')
      setEndpointExpertMode(false)
      return
    }
    void fetchMappingHistory()
  }, [endpointEditKey])

  async function load() {
    setLoading(true)
    setError('')
    try {
      const params = kindFilter === 'all' ? undefined : { kind: kindFilter }
      const res = await get<ProviderListResponse>('/api/compat/external-facts/providers', { params })
      setItems(Array.isArray(res.data) ? res.data : [])
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : t(K.page.externalFactsProviders.errorLoad))
    } finally {
      setLoading(false)
    }
  }

  async function loadRegistry() {
    try {
      const res = await get<RegistryResponse>('/api/compat/external-facts/registry')
      setRegistry(Array.isArray(res.data) ? res.data : [])
    } catch {
      setRegistry([])
    }
  }

  async function loadBindings() {
    try {
      const res = await get<{ ok: boolean; data: BindingItem[] }>('/api/compat/external-facts/bindings')
      setBindings(Array.isArray(res.data) ? res.data : [])
    } catch {
      setBindings([])
    }
  }

  async function loadConnectorEndpoints() {
    try {
      const res = await get<{ ok: boolean; data: ConnectorEndpointOption[] }>('/api/compat/connectors/search/endpoints/all')
      setConnectorEndpoints(Array.isArray(res.data) ? res.data : [])
    } catch {
      setConnectorEndpoints([])
    }
  }

  function buildPlatformMapping() {
    const endpointMapInline = mapToEndpointMap(form.base_url, form.endpoints)
    if (form.kind !== 'fx') {
      return { supported_items: {}, endpoint_map: endpointMapInline }
    }

    const exchangeItems: Record<string, unknown> = {}
    const latestCfg = form.endpoints.latest
    const rangeCfg = form.endpoints.range_historical
    const historicalCfg = form.endpoints.historical

    if (latestCfg.enabled && latestCfg.path.trim()) {
      exchangeItems.spot = {
        method: latestCfg.method,
        url: buildAbsoluteUrl(form.base_url, latestCfg.path),
        response: {
          kind: 'point',
          time_path: latestCfg.timePath.trim() || 'meta.last_updated_at',
          value_path: latestCfg.valuePath.trim() || 'data.{quote}.value',
        },
      }
    }

    const seriesSource = (rangeCfg.enabled && rangeCfg.path.trim()) ? rangeCfg : historicalCfg
    if (seriesSource.enabled && seriesSource.path.trim()) {
      exchangeItems.series = {
        method: seriesSource.method,
        url: buildAbsoluteUrl(form.base_url, seriesSource.path),
        response: {
          kind: 'series',
          points_path: seriesSource.pointsPath.trim() || 'data',
          time_path: seriesSource.timePath.trim() || 'key',
          value_path: seriesSource.valuePath.trim() || '{quote}.value',
        },
      }
    }

    return {
      supported_items: { exchange_rate: Object.keys(exchangeItems) },
      endpoint_map: {
        ...endpointMapInline,
        exchange_rate: { items: exchangeItems },
      },
    }
  }

  async function saveProvider() {
    setSaving(true)
    setError('')
    setSuccess('')
    const token = getToken()
    if (!token) {
      setSaving(false)
      setError(t(K.page.externalFactsProviders.errorAdminToken))
      return
    }

    try {
      const endpointMap = mapToEndpointMap(form.base_url, form.endpoints)
      const payload = {
        provider_id: form.provider_id.trim(),
        kind: form.kind,
        name: form.name.trim(),
        endpoint_url: buildAbsoluteUrl(form.base_url, form.endpoints.latest.path),
        api_key: form.api_key.trim(),
        api_key_header: form.api_key_header.trim() || 'Authorization',
        priority: Math.max(1, Number(form.priority) || 1),
        enabled: form.enabled,
        config: {
          method: form.endpoints.latest.method,
          value_path: form.endpoints.latest.valuePath.trim(),
          summary_path: form.endpoints.latest.summaryPath.trim(),
          as_of_path: form.endpoints.latest.timePath.trim(),
          rate_path: form.endpoints.latest.valuePath.trim(),
          query_suffix: form.query_suffix.trim(),
          series_endpoint_url: buildAbsoluteUrl(form.base_url, form.endpoints.range_historical.path),
          series_points_path: form.endpoints.range_historical.pointsPath.trim(),
          series_time_path: form.endpoints.range_historical.timePath.trim(),
          series_rate_path: form.endpoints.range_historical.valuePath.trim(),
          endpoint_map: endpointMap,
          capability_text: form.capability_text.trim(),
          base_url: form.base_url.trim(),
          endpoints: form.endpoints,
        },
        ...buildPlatformMapping(),
      }
      await post('/api/compat/external-facts/providers', payload, {
        headers: { 'X-Admin-Token': token },
      })
      setSuccess(t(K.page.externalFactsProviders.saved))
      setForm({ ...emptyForm, kind: form.kind })
      setPresetId('')
      setEditingProviderId(null)
      setFormOpen(false)
      await load()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : t(K.page.externalFactsProviders.errorSave))
    } finally {
      setSaving(false)
    }
  }

  async function removeProvider(providerId: string) {
    const token = getToken()
    if (!token) {
      setError(t(K.page.externalFactsProviders.errorAdminToken))
      return
    }
    try {
      await del(`/api/compat/external-facts/providers/${encodeURIComponent(providerId)}`, {
        headers: { 'X-Admin-Token': token },
      })
      await load()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : t(K.page.externalFactsProviders.errorDelete))
    }
  }

  async function runTest(providerId: string, kind: FactKind) {
    const token = getToken()
    if (!token) {
      setError(t(K.page.externalFactsProviders.errorAdminToken))
      return
    }
    setTestingId(providerId)
    setTestResult('')
    try {
      const sample = kind === 'fx' ? '当前 AUD 和 CNY 的汇率' : `${kind} latest`
      const res = await post<TestResponse>(
        `/api/compat/external-facts/providers/${encodeURIComponent(providerId)}/test`,
        { query: sample },
        { headers: { 'X-Admin-Token': token } }
      )
      const result = res.data?.result
      setTestResult(`${providerId}: ${result?.status || 'unknown'} · ${result?.fallback_text || ''}`)
    } catch (err: unknown) {
      setTestResult(`${providerId}: ${err instanceof Error ? err.message : 'test failed'}`)
    } finally {
      setTestingId(null)
    }
  }

  function saveAdminTokenLocal() {
    const value = adminTokenInput.trim()
    if (!value) {
      clearToken()
      setSuccess(t(K.page.externalFactsProviders.tokenCleared))
      return
    }
    setToken(value)
    setSuccess(t(K.page.externalFactsProviders.tokenSaved))
  }

  function applyPreset(nextPresetId: string) {
    setPresetId(nextPresetId)
    if (!nextPresetId) return
    const selected = PRESETS.find((preset) => preset.id === nextPresetId)
    if (!selected) return

    setForm((prev) => {
      const endpoints = emptyEndpoints()
      for (const key of ENDPOINT_ORDER) {
        const data = selected.endpoints[key] || {}
        endpoints[key] = {
          ...endpoints[key],
          ...data,
        }
      }
      return {
        ...prev,
        kind: selected.kind,
        name: prev.name || selected.label,
        base_url: selected.baseUrl,
        api_key: '',
        api_key_header: selected.apiKeyHeader,
        endpoints,
      }
    })
    setSuccess(`${t(K.page.externalFactsProviders.presetApplied)}: ${selected.label}`)
  }

  function openCreateDialog() {
    setDialogMode('create')
    setEditingProviderId(null)
    setForm({ ...emptyForm, kind: kindFilter === 'all' ? 'fx' : kindFilter })
    setPresetId('')
    setFormOpen(true)
  }

  function applyFxWizard() {
    const selectedPreset = PRESETS.find((preset) => preset.id === fxWizardPresetId) || PRESETS[0]
    const endpoints = emptyEndpoints()
    for (const key of ENDPOINT_ORDER) {
      const data = selectedPreset?.endpoints?.[key] || {}
      endpoints[key] = { ...endpoints[key], ...data, enabled: false }
    }
    if (fxWizardGoal === 'spot') {
      endpoints.latest.enabled = true
      endpoints.convert.enabled = false
      endpoints.range_historical.enabled = false
      endpoints.historical.enabled = false
    } else if (fxWizardGoal === 'series') {
      endpoints.latest.enabled = true
      endpoints.range_historical.enabled = true
      endpoints.historical.enabled = false
      endpoints.convert.enabled = false
    } else {
      endpoints.latest.enabled = false
      endpoints.convert.enabled = true
      endpoints.range_historical.enabled = false
      endpoints.historical.enabled = false
    }
    setDialogMode('create')
    setEditingProviderId(null)
    setForm({
      ...emptyForm,
      kind: 'fx',
      name: selectedPreset.label,
      base_url: selectedPreset.baseUrl,
      api_key_header: selectedPreset.apiKeyHeader,
      endpoints,
    })
    setPresetId(selectedPreset.id)
    setFormOpen(true)
    setSuccess(`已应用 FX 向导：${fxWizardGoal} · ${selectedPreset.label}`)
  }

  function openFormFromProvider(item: ProviderItem, mode: DialogMode) {
    const config = (item.config || {}) as Record<string, any>
    const baseUrl = String(config.base_url || '')
    const endpointMap = (config.endpoint_map || item.endpoint_map || {}) as Record<string, string>
    const storedEndpoints = (config.endpoints || {}) as Partial<Record<EndpointKey, EndpointConfig>>
    const endpoints = emptyEndpoints()

    for (const key of ENDPOINT_ORDER) {
      const mappedUrl = typeof endpointMap[key] === 'string' ? endpointMap[key] : ''
      const fromStored = storedEndpoints[key]
      if (fromStored) {
        endpoints[key] = { ...endpoints[key], ...fromStored }
        continue
      }
      if (mappedUrl) {
        endpoints[key] = {
          ...endpoints[key],
          enabled: true,
          path: parsePathFromUrl(baseUrl, mappedUrl),
        }
      }
    }
    if (String(config.series_endpoint_url || '')) {
      endpoints.range_historical.path = parsePathFromUrl(baseUrl, String(config.series_endpoint_url || ''))
      endpoints.range_historical.enabled = true
    }
    if (String(config.series_points_path || '')) endpoints.range_historical.pointsPath = String(config.series_points_path)
    if (String(config.series_time_path || '')) endpoints.range_historical.timePath = String(config.series_time_path)
    if (String(config.series_rate_path || '')) endpoints.range_historical.valuePath = String(config.series_rate_path)

    setDialogMode(mode)
    setEditingProviderId(mode === 'edit' ? item.provider_id : null)
    setForm({
      provider_id: mode === 'clone' ? `${item.provider_id}-copy` : item.provider_id,
      kind: item.kind,
      name: mode === 'clone' ? `${item.name} Copy` : item.name,
      base_url: baseUrl,
      api_key: '',
      api_key_header: item.api_key_header || 'Authorization',
      priority: Number(item.priority) || 10,
      enabled: Boolean(item.enabled),
      query_suffix: String(config.query_suffix || ''),
      capability_text: String(config.capability_text || ''),
      endpoints,
    })
    setPresetId('')
    setFormOpen(true)
  }

  async function inferEndpointMapping() {
    if (!endpointEditKey) return
    if (!editingProviderId) {
      setError(t(K.page.externalFactsProviders.saveFirstHint))
      return
    }
    const token = getToken()
    if (!token) {
      setError(t(K.page.externalFactsProviders.errorAdminToken))
      return
    }
    const capabilityItem = endpointToCapabilityItem(form.kind, endpointEditKey)
    if (!capabilityItem) {
      setError(t(K.page.externalFactsProviders.endpointUnsupportedHint))
      return
    }
    let parsedSample: Record<string, unknown>
    try {
      if (!sampleJsonInput.trim()) {
        setError(t(K.page.externalFactsProviders.sampleJsonRequired))
        return
      }
      parsedSample = JSON.parse(sampleJsonInput || '{}')
    } catch {
      setError(t(K.page.externalFactsProviders.sampleJsonInvalid))
      return
    }
    setMappingLoading(true)
    setMappingPhase('llm')
    setMappingStatusLevel('info')
    setMappingStatusText('阶段 1/2：正在调用 LLM 生成映射…')
    try {
      const endpointCfg = form.endpoints[endpointEditKey]
      const endpointUrl = buildAbsoluteUrl(form.base_url, endpointCfg.path)
      const res = await post<InferMappingResponse>(
        `/api/compat/external-facts/providers/${encodeURIComponent(editingProviderId)}/endpoint/${encodeURIComponent(`${capabilityItem.capabilityId}:${capabilityItem.itemId}`)}/infer-mapping`,
        {
          sample_json: parsedSample,
          capability_id: capabilityItem.capabilityId,
          item_id: capabilityItem.itemId,
          endpoint: { url: endpointUrl, method: endpointCfg.method },
        },
        { headers: { 'X-Admin-Token': token } },
      )
      setProposalId(res.data.proposal_id)
      setSampleId(res.data.sample_id)
      setProposalPreview(res.data.proposal || null)
      setMappingPhase('validate')
      setMappingStatusText('阶段 2/2：正在校验样本提取结果…')
      setValidationPreview(res.data.validation_report || null)
      setCanApplyProposal(Boolean(res.data.can_apply))
      setSuccess('映射建议已生成。')
      setMappingStatusLevel('success')
      setMappingStatusText(res.data.can_apply ? '映射生成并验证通过，可直接应用。' : '映射已生成，但验证未通过或置信度不足。')
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : '生成映射失败'
      setError(message)
      setMappingStatusLevel('error')
      setMappingStatusText(message)
    } finally {
      setMappingLoading(false)
      setMappingPhase('idle')
    }
  }

  async function applyEndpointMapping() {
    if (!endpointEditKey || !editingProviderId || !proposalId || !sampleId) return
    const token = getToken()
    if (!token) {
      setError(t(K.page.externalFactsProviders.errorAdminToken))
      return
    }
    const capabilityItem = endpointToCapabilityItem(form.kind, endpointEditKey)
    if (!capabilityItem) return
    setMappingLoading(true)
    setMappingPhase('apply')
    setMappingStatusLevel('info')
    setMappingStatusText('正在应用映射版本…')
    try {
      const endpointCfg = form.endpoints[endpointEditKey]
      const endpointUrl = buildAbsoluteUrl(form.base_url, endpointCfg.path)
      await post<ApplyMappingResponse>(
        `/api/compat/external-facts/providers/${encodeURIComponent(editingProviderId)}/endpoint/${encodeURIComponent(`${capabilityItem.capabilityId}:${capabilityItem.itemId}`)}/apply-mapping`,
        {
          proposal_id: proposalId,
          sample_id: sampleId,
          endpoint: { url: endpointUrl, method: endpointCfg.method },
        },
        { headers: { 'X-Admin-Token': token } },
      )
      setSuccess('映射版本已应用。')
      setMappingStatusLevel('success')
      setMappingStatusText('映射已应用并激活。')
      await load()
      await fetchMappingHistory()
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : '应用映射失败'
      if (message.includes('NO_SAMPLE_AVAILABLE_FOR_VALIDATION')) {
        setError(t(K.page.externalFactsProviders.noSampleForValidation))
        setMappingStatusLevel('error')
        setMappingStatusText(t(K.page.externalFactsProviders.noSampleForValidation))
      } else {
        setError(message)
        setMappingStatusLevel('error')
        setMappingStatusText(message)
      }
    } finally {
      setMappingLoading(false)
      setMappingPhase('idle')
    }
  }

  async function rollbackToVersion(version: MappingVersionItem) {
    if (!endpointEditKey || !editingProviderId) return
    const token = getToken()
    if (!token) {
      setError(t(K.page.externalFactsProviders.errorAdminToken))
      return
    }
    const capabilityItem = endpointToCapabilityItem(form.kind, endpointEditKey)
    if (!capabilityItem) return
    const mappingJson = version.mapping_json
    if (!mappingJson || typeof mappingJson !== 'object') {
      setError('mapping_json missing for selected version')
      return
    }
    setMappingLoading(true)
    setMappingPhase('apply')
    try {
      await post<ApplyMappingResponse>(
        `/api/compat/external-facts/providers/${encodeURIComponent(editingProviderId)}/endpoint/${encodeURIComponent(`${capabilityItem.capabilityId}:${capabilityItem.itemId}`)}/apply-mapping`,
        { mapping_json: mappingJson },
        { headers: { 'X-Admin-Token': token } },
      )
      setRollbackVersion(null)
      setHistoryDialogOpen(false)
      setHistoryPreviewVersion(null)
      setSuccess(t(K.page.externalFactsProviders.rollbackSuccess))
      await load()
      await fetchMappingHistory()
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'rollback failed'
      if (message.includes('NO_SAMPLE_AVAILABLE_FOR_VALIDATION')) {
        setError(t(K.page.externalFactsProviders.noSampleForValidation))
      } else {
        setError(message)
      }
    } finally {
      setMappingLoading(false)
      setMappingPhase('idle')
    }
  }

  async function fetchMappingHistory() {
    if (!endpointEditKey || !editingProviderId) return
    const capabilityItem = endpointToCapabilityItem(form.kind, endpointEditKey)
    if (!capabilityItem) {
      setMappingHistory(null)
      return
    }
    try {
      const res = await get<MappingHistoryResponse>(
        `/api/compat/external-facts/providers/${encodeURIComponent(editingProviderId)}/endpoint/${encodeURIComponent(`${capabilityItem.capabilityId}:${capabilityItem.itemId}`)}/mappings`,
      )
      setMappingHistory(res.data)
    } catch {
      setMappingHistory(null)
    }
  }

  async function saveBinding() {
    const token = getToken()
    if (!token) {
      setError(t(K.page.externalFactsProviders.errorAdminToken))
      return
    }
    const selected = connectorEndpoints.find(
      (opt) => `${opt.connector_id}:${opt.endpoint_id}` === selectedEndpointRef,
    )
    if (!selected) {
      setError('请选择一个 Connector Endpoint')
      return
    }
    if (selected.capability_id !== bindingCapabilityId || selected.item_id !== bindingItemId) {
      setError('所选 Endpoint 与 capability/item 不匹配，请重新选择兼容项。')
      return
    }
    try {
      await post(
        '/api/compat/external-facts/bindings',
        {
          capability_id: bindingCapabilityId,
          item_id: bindingItemId,
          connector_id: selected.connector_id,
          endpoint_id: selected.endpoint_id,
          status: 'active',
        },
        { headers: { 'X-Admin-Token': token } },
      )
      setSuccess('Binding saved')
      await loadBindings()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '保存 Binding 失败')
    }
  }

  async function runSelfCheck() {
    setSelfCheckLoading(true)
    setSelfCheckItems([])
    setError('')
    const checks: SelfCheckItem[] = []
    try {
      const [bindingsRes, providersRes, endpointsRes] = await Promise.all([
        get<{ ok: boolean; data: BindingItem[] }>('/api/compat/external-facts/bindings'),
        get<ProviderListResponse>('/api/compat/external-facts/providers'),
        get<{ ok: boolean; data: ConnectorEndpointOption[] }>('/api/compat/connectors/search/endpoints/all'),
      ])
      const bindingsData = Array.isArray(bindingsRes.data) ? bindingsRes.data : []
      const providersData = Array.isArray(providersRes.data) ? providersRes.data : []
      const endpointsData = Array.isArray(endpointsRes.data) ? endpointsRes.data : []
      checks.push({
        key: 'providers_count',
        title: 'Provider 配置数量',
        status: providersData.length > 0 ? 'pass' : 'warn',
        detail: providersData.length > 0 ? `已配置 ${providersData.length} 个 provider` : '当前未配置 provider（允许仅走 binding）',
      })
      const currentCompatible = endpointsData.filter(
        (ep) => ep.capability_id === bindingCapabilityId && ep.item_id === bindingItemId,
      )
      checks.push({
        key: 'compatible_endpoint_pool',
        title: '兼容 Endpoint 池',
        status: currentCompatible.length > 0 ? 'pass' : 'fail',
        detail:
          currentCompatible.length > 0
            ? `找到 ${currentCompatible.length} 个兼容 endpoint（${bindingCapabilityId}:${bindingItemId}）`
            : `没有兼容 endpoint（${bindingCapabilityId}:${bindingItemId}）`,
        action: currentCompatible.length > 0 ? undefined : 'open_connectors',
        actionLabel: currentCompatible.length > 0 ? undefined : '去 Connectors 新增',
      })
      const selectedStillCompatible = currentCompatible.some(
        (ep) => `${ep.connector_id}:${ep.endpoint_id}` === selectedEndpointRef,
      )
      checks.push({
        key: 'selected_endpoint',
        title: '当前选择的 Endpoint',
        status: selectedStillCompatible ? 'pass' : 'warn',
        detail: selectedStillCompatible ? '当前选择项与 capability/item 匹配' : '当前选择项未匹配或未选择',
        action: selectedStillCompatible ? undefined : 'auto_select_endpoint',
        actionLabel: selectedStillCompatible ? undefined : '自动选择兼容项',
      })
      const fxSpotBinding = bindingsData.find((b) => b.capability_id === 'exchange_rate' && b.item_id === 'spot')
      if (!fxSpotBinding) {
        checks.push({
          key: 'fx_spot_binding',
          title: 'exchange_rate:spot 绑定',
          status: 'fail',
          detail: '未找到 exchange_rate:spot 绑定',
          action: 'refresh_data',
          actionLabel: '刷新后重试',
        })
      } else {
        checks.push({
          key: 'fx_spot_binding',
          title: 'exchange_rate:spot 绑定',
          status: 'pass',
          detail: `绑定存在：${fxSpotBinding.connector_id}:${fxSpotBinding.endpoint_id}`,
        })
        const matchedEndpoint = endpointsData.find(
          (ep) => ep.connector_id === fxSpotBinding.connector_id && ep.endpoint_id === fxSpotBinding.endpoint_id,
        )
        if (!matchedEndpoint) {
          checks.push({
            key: 'binding_endpoint_exists',
            title: '绑定目标 Endpoint',
            status: 'fail',
            detail: '绑定目标 endpoint 不存在',
            action: 'open_connectors',
            actionLabel: '去 Connectors 修复',
          })
        } else if (matchedEndpoint.capability_id !== 'exchange_rate' || matchedEndpoint.item_id !== 'spot') {
          checks.push({
            key: 'binding_endpoint_match',
            title: '绑定目标 capability/item',
            status: 'fail',
            detail: `不匹配：${matchedEndpoint.capability_id}:${matchedEndpoint.item_id}`,
            action: 'open_connectors',
            actionLabel: '去 Connectors 修复',
          })
        } else {
          checks.push({
            key: 'binding_endpoint_match',
            title: '绑定目标 capability/item',
            status: 'pass',
            detail: '匹配 exchange_rate:spot',
          })
          const token = getToken()
          if (!token) {
            checks.push({
              key: 'binding_endpoint_test',
              title: '绑定 Endpoint 实测',
              status: 'warn',
              detail: '未设置 Admin Token，跳过 endpoint 实测',
              action: 'set_admin_token',
              actionLabel: '先设置 Token',
            })
          } else {
            try {
              const testRes = await post<{ ok: boolean; data?: Record<string, unknown> }>(
                `/api/compat/connectors/${encodeURIComponent(fxSpotBinding.connector_id)}/endpoints/${encodeURIComponent(fxSpotBinding.endpoint_id)}/test`,
                { params: { base: 'AUD', quote: 'CNY', from_iso: '2026-02-07', to_iso: '2026-02-08' } },
                { headers: { 'X-Admin-Token': token } },
              )
              const maybeError = String((testRes.data || {}).error || '')
              if (maybeError) {
                checks.push({
                  key: 'binding_endpoint_test',
                  title: '绑定 Endpoint 实测',
                  status: 'fail',
                  detail: `实测失败：${maybeError}`,
                  action: 'open_connectors',
                  actionLabel: '去 Connectors 修复',
                })
              } else {
                const statusCode = String((testRes.data || {}).status_code || '200')
                checks.push({
                  key: 'binding_endpoint_test',
                  title: '绑定 Endpoint 实测',
                  status: 'pass',
                  detail: `实测通过（HTTP ${statusCode}）`,
                })
              }
            } catch (err: unknown) {
              checks.push({
                key: 'binding_endpoint_test',
                title: '绑定 Endpoint 实测',
                status: 'fail',
                detail: `实测异常：${err instanceof Error ? err.message : 'unknown error'}`,
                action: 'open_connectors',
                actionLabel: '去 Connectors 修复',
              })
            }
          }
        }
      }
      setSelfCheckItems(checks)
      setSuccess('自检完成')
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '自检失败')
    } finally {
      setSelfCheckLoading(false)
    }
  }

  function runSelfCheckAction(action?: SelfCheckAction) {
    if (!action) return
    if (action === 'open_connectors') {
      window.location.href = '/connectors'
      return
    }
    if (action === 'refresh_data') {
      void loadBindings()
      void loadConnectorEndpoints()
      void load()
      return
    }
    if (action === 'auto_select_endpoint') {
      if (compatibleEndpoints[0]) {
        setSelectedEndpointRef(`${compatibleEndpoints[0].connector_id}:${compatibleEndpoints[0].endpoint_id}`)
        setSuccess('已自动选择第一个兼容 endpoint')
      } else {
        setError('当前没有可自动选择的兼容 endpoint')
      }
      return
    }
    if (action === 'set_admin_token') {
      setError('请先在页面顶部填写并保存 Admin Token，然后再运行自检。')
    }
  }

  async function removeBinding(capabilityId: string, itemId: string) {
    const token = getToken()
    if (!token) {
      setError(t(K.page.externalFactsProviders.errorAdminToken))
      return
    }
    try {
      await del(
        `/api/compat/external-facts/bindings/${encodeURIComponent(capabilityId)}/${encodeURIComponent(itemId)}`,
        { headers: { 'X-Admin-Token': token } },
      )
      await loadBindings()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '删除 Binding 失败')
    }
  }

  async function openHistoryDialog() {
    await fetchMappingHistory()
    setHistoryDialogOpen(true)
  }

  const dialogTitle = dialogMode === 'create'
    ? t(K.page.externalFactsProviders.newProvider)
    : dialogMode === 'edit'
      ? `${t(K.common.edit)} · ${editingProviderId || ''}`
      : `${t(K.common.copy)} · ${editingProviderId || ''}`

  return (
    <Box sx={{ p: 3 }}>
      <Stack spacing={2.5}>
        <Paper component="form" sx={{ p: 2.5 }}>
          <Grid container rowSpacing={2.5} columnSpacing={2}>
            <Grid item xs={12} md={6}>
              <TextField
                size="small"
                type="password"
                label={t(K.page.externalFactsProviders.adminToken)}
                value={adminTokenInput}
                onChange={(e) => setAdminTokenInput(e.target.value)}
                fullWidth
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <Stack direction="row" spacing={1.25}>
                <Button variant="outlined" onClick={saveAdminTokenLocal} fullWidth>
                  {t(K.page.externalFactsProviders.saveToken)}
                </Button>
                <Button
                  variant="outlined"
                  color="inherit"
                  onClick={() => {
                    clearToken()
                    setAdminTokenInput('')
                    setSuccess(t(K.page.externalFactsProviders.tokenCleared))
                  }}
                  fullWidth
                >
                  {t(K.page.externalFactsProviders.clearToken)}
                </Button>
              </Stack>
            </Grid>
            <Grid item xs={12} md={4}>
              <FormControl size="small" fullWidth>
                <InputLabel>{t(K.page.externalFactsProviders.kindFilter)}</InputLabel>
                <Select
                  value={kindFilter}
                  label={t(K.page.externalFactsProviders.kindFilter)}
                  onChange={(e) => setKindFilter(e.target.value as 'all' | FactKind)}
                  onClose={blurActiveElement}
                  MenuProps={SELECT_MENU_PROPS}
                >
                  <MenuItem value="all">{t(K.common.all)}</MenuItem>
                  {FACT_KINDS.map((kind) => (
                    <MenuItem key={kind} value={kind}>{kindLabel(t, kind)}</MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} md={4}>
              <Button variant="outlined" onClick={() => void load()} disabled={loading} fullWidth>
                {t(K.common.refresh)}
              </Button>
            </Grid>
            <Grid item xs={12} md={4}>
              <Button variant="contained" onClick={openCreateDialog} fullWidth>
                {t(K.page.externalFactsProviders.newProvider)}
              </Button>
            </Grid>
          </Grid>
        </Paper>

        {error && <Alert severity="error">{error}</Alert>}
        {success && <Alert severity="success">{success}</Alert>}
        {testResult && <Alert severity="info">{testResult}</Alert>}

        <Alert severity="info">
          <Typography variant="subtitle2" sx={{ mb: 0.5 }}>
            外部事实配置说明（FX）
          </Typography>
          <Typography variant="body2">
            1) `spot`：单点最新汇率（例如 AUD/CNY 当前值）。用于聊天卡片里的“当前汇率”。
          </Typography>
          <Typography variant="body2">
            2) `series`：时间序列汇率（过去 N 分钟/天的曲线）。用于趋势图和窗口分析。
          </Typography>
          <Typography variant="body2">
            3) `convert`：按金额换算（例如 1 AUD = ? CNY）。通常仍映射到 `exchange_rate:spot`。
          </Typography>
          <Typography variant="body2" sx={{ mt: 0.5 }}>
            关键占位符：`&#123;base&#125;`、`&#123;quote&#125;`、`&#123;from_iso&#125;`、`&#123;to_iso&#125;`。请在 Connector Endpoint 的 URL/参数中使用。
          </Typography>
          <Typography variant="caption" sx={{ display: 'block', mt: 0.5 }}>
            Endpoint 新增/编辑参数说明已放在 Connectors 页面对应对话框中。
          </Typography>
        </Alert>

        <Paper sx={{ p: 2.5 }}>
          <Typography variant="h6" sx={{ mb: 1.5 }}>
            FX 快速配置向导
          </Typography>
          <Grid container rowSpacing={2.5} columnSpacing={2}>
            <Grid item xs={12} md={4}>
              <FormControl size="small" fullWidth>
                <InputLabel>目标</InputLabel>
                <Select
                  value={fxWizardGoal}
                  label="目标"
                  onChange={(e) => setFxWizardGoal(e.target.value as FxGoal)}
                  onClose={blurActiveElement}
                  MenuProps={SELECT_MENU_PROPS}
                >
                  <MenuItem value="spot">当前汇率（spot）</MenuItem>
                  <MenuItem value="series">趋势分析（series）</MenuItem>
                  <MenuItem value="convert">金额换算（convert）</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} md={4}>
              <FormControl size="small" fullWidth>
                <InputLabel>数据源预设</InputLabel>
                <Select
                  value={fxWizardPresetId}
                  label="数据源预设"
                  onChange={(e) => setFxWizardPresetId(String(e.target.value))}
                  onClose={blurActiveElement}
                  MenuProps={SELECT_MENU_PROPS}
                >
                  {PRESETS.filter((preset) => preset.kind === 'fx').map((preset) => (
                    <MenuItem key={preset.id} value={preset.id}>{preset.label}</MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} md={4}>
              <Button variant="contained" onClick={applyFxWizard} fullWidth>
                应用到新建表单
              </Button>
            </Grid>
          </Grid>
        </Paper>

        <Paper sx={{ p: 2.5 }}>
          <Typography variant="h6" sx={{ mb: 1.5 }}>
            {t(K.page.externalFactsProviders.bindingTitle)}
          </Typography>
          <Grid container rowSpacing={2.5} columnSpacing={2}>
            <Grid item xs={12} md={3}>
              <FormControl size="small" fullWidth>
                <InputLabel>{t(K.page.externalFactsProviders.bindingCapability)}</InputLabel>
                <Select
                  value={registry.some((cap) => cap.capability_id === bindingCapabilityId) ? bindingCapabilityId : ''}
                  label={t(K.page.externalFactsProviders.bindingCapability)}
                  onChange={(e) => setBindingCapabilityId(String(e.target.value))}
                  onClose={blurActiveElement}
                  MenuProps={SELECT_MENU_PROPS}
                >
                  <MenuItem value="">
                    <em>-</em>
                  </MenuItem>
                  {registry.map((cap) => (
                    <MenuItem key={cap.capability_id} value={cap.capability_id}>
                      {cap.capability_id}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} md={3}>
              <FormControl size="small" fullWidth>
                <InputLabel>{t(K.page.externalFactsProviders.bindingItem)}</InputLabel>
                <Select
                  value={(registry.find((cap) => cap.capability_id === bindingCapabilityId)?.items || []).some((item) => item.item_id === bindingItemId) ? bindingItemId : ''}
                  label={t(K.page.externalFactsProviders.bindingItem)}
                  onChange={(e) => setBindingItemId(String(e.target.value))}
                  onClose={blurActiveElement}
                  MenuProps={SELECT_MENU_PROPS}
                >
                  <MenuItem value="">
                    <em>-</em>
                  </MenuItem>
                  {(registry.find((cap) => cap.capability_id === bindingCapabilityId)?.items || []).map((item) => (
                    <MenuItem key={item.item_id} value={item.item_id}>
                      {item.item_id}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} md={4}>
              <FormControl size="small" fullWidth>
                <InputLabel>{t(K.page.externalFactsProviders.bindingEndpoint)}</InputLabel>
                <Select
                  value={selectedEndpointCompatible ? selectedEndpointRef : ''}
                  label={t(K.page.externalFactsProviders.bindingEndpoint)}
                  onChange={(e) => setSelectedEndpointRef(String(e.target.value))}
                  onClose={blurActiveElement}
                  MenuProps={SELECT_MENU_PROPS}
                >
                  <MenuItem value="">
                    <em>-</em>
                  </MenuItem>
                  {compatibleEndpoints.map((opt) => (
                      <MenuItem key={`${opt.connector_id}:${opt.endpoint_id}`} value={`${opt.connector_id}:${opt.endpoint_id}`}>
                        {opt.connector_name} · {opt.name} · {opt.method} {opt.path}
                      </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} md={2}>
              <Button variant="contained" onClick={() => void saveBinding()} fullWidth>
                {t(K.page.externalFactsProviders.bindingBind)}
              </Button>
            </Grid>
            <Grid item xs={12} md={12}>
              <Stack direction={{ xs: 'column', md: 'row' }} spacing={1.25} alignItems={{ md: 'center' }}>
                <Typography variant="caption" sx={{ opacity: 0.75 }}>
                  兼容 Endpoint 数量：{compatibleEndpoints.length}（只显示与 {bindingCapabilityId}:{bindingItemId} 匹配项）
                </Typography>
                <Button variant="outlined" size="small" onClick={() => void runSelfCheck()} disabled={selfCheckLoading}>
                  {selfCheckLoading ? '自检中…' : '一键自检'}
                </Button>
                {!!selfCheckItems.length && (
                  <Stack direction="row" spacing={0.75}>
                    <Chip size="small" color="success" label={`通过 ${selfCheckSummary.pass}`} />
                    <Chip size="small" color="warning" label={`警告 ${selfCheckSummary.warn}`} />
                    <Chip size="small" color="error" label={`失败 ${selfCheckSummary.fail}`} />
                  </Stack>
                )}
              </Stack>
              {!compatibleEndpoints.length && (
                <Alert severity="warning" sx={{ mt: 1 }}>
                  当前没有兼容 Endpoint。请先到 Connectors 页面新增 capability/item 匹配的 endpoint。
                </Alert>
              )}
              {!!selfCheckItems.length && (
                <Grid container spacing={1.25} sx={{ mt: 0.25 }}>
                  {selfCheckItems.map((item) => (
                    <Grid item xs={12} md={6} key={item.key}>
                      <Paper variant="outlined" sx={{ p: 1.25 }}>
                        <Stack direction="row" justifyContent="space-between" alignItems="center" spacing={1}>
                          <Typography variant="subtitle2">{item.title}</Typography>
                          <Chip
                            size="small"
                            color={item.status === 'pass' ? 'success' : item.status === 'warn' ? 'warning' : 'error'}
                            label={item.status === 'pass' ? '通过' : item.status === 'warn' ? '警告' : '失败'}
                          />
                        </Stack>
                        <Typography variant="caption" sx={{ display: 'block', opacity: 0.78, mt: 0.5 }}>
                          {item.detail}
                        </Typography>
                        {item.action && item.actionLabel && (
                          <Button
                            sx={{ mt: 1 }}
                            size="small"
                            variant="outlined"
                            onClick={() => runSelfCheckAction(item.action)}
                          >
                            {item.actionLabel}
                          </Button>
                        )}
                      </Paper>
                    </Grid>
                  ))}
                </Grid>
              )}
            </Grid>
          </Grid>
          <Stack spacing={1.25} sx={{ mt: 2 }}>
            {bindings.map((b) => (
              <Paper key={b.binding_id} variant="outlined" sx={{ p: 1.25 }}>
                <Stack direction="row" justifyContent="space-between" alignItems="center">
                  <Box>
                    <Typography variant="subtitle2">{b.capability_id}:{b.item_id}</Typography>
                    <Typography variant="caption" sx={{ opacity: 0.72 }}>
                      {b.connector_id}:{b.endpoint_id} · {b.status}
                    </Typography>
                  </Box>
                  <Button size="small" variant="outlined" color="error" onClick={() => void removeBinding(b.capability_id, b.item_id)}>
                    {t(K.common.delete)}
                  </Button>
                </Stack>
              </Paper>
            ))}
            {!bindings.length && (
              <Typography variant="body2" sx={{ opacity: 0.72 }}>
                {t(K.page.externalFactsProviders.bindingEmpty)}
              </Typography>
            )}
          </Stack>
        </Paper>

        <Paper sx={{ p: 2.5 }}>
          <Typography variant="h6" sx={{ mb: 1.5 }}>
            {t(K.page.externalFactsProviders.registeredProviders)}
          </Typography>
          <Stack spacing={1.25}>
            {filtered.map((item) => (
              <Paper key={item.provider_id} variant="outlined" sx={{ p: 1.5 }}>
                <Stack direction={{ xs: 'column', md: 'row' }} spacing={1.25} alignItems={{ md: 'center' }} justifyContent="space-between">
                  <Box sx={{ minWidth: 0 }}>
                    <Typography variant="subtitle2">{item.name} · {item.provider_id}</Typography>
                    <Typography variant="caption" sx={{ opacity: 0.82, display: 'block' }}>
                      {kindLabel(t, item.kind)} · {t(K.page.externalFactsProviders.priority)} {item.priority} · {item.enabled ? t(K.common.enabled) : t(K.common.disabled)}
                    </Typography>
                    <Typography variant="caption" sx={{ opacity: 0.72, display: 'block' }}>
                      {item.endpoint_url}
                    </Typography>
                    <Typography variant="caption" sx={{ opacity: 0.72, display: 'block' }}>
                      schema: {item.endpoint_map_schema_valid ? 'valid' : 'invalid'}
                      {item.last_validation_error ? ` · ${item.last_validation_error}` : ''}
                    </Typography>
                    <Typography variant="caption" sx={{ opacity: 0.72, display: 'block' }}>
                      {item.has_api_key ? t(K.page.externalFactsProviders.keyConfigured) : t(K.page.externalFactsProviders.keyMissing)}
                    </Typography>
                  </Box>
                  <Stack direction="row" spacing={1}>
                    <Button size="small" variant="outlined" onClick={() => openFormFromProvider(item, 'edit')}>
                      {t(K.common.edit)}
                    </Button>
                    <Button size="small" variant="outlined" onClick={() => openFormFromProvider(item, 'clone')}>
                      {t(K.common.copy)}
                    </Button>
                    <Button size="small" variant="outlined" onClick={() => setPreviewItem(item)}>
                      {t(K.common.preview)}
                    </Button>
                    <Button size="small" variant="outlined" onClick={() => void runTest(item.provider_id, item.kind)} disabled={testingId === item.provider_id}>
                      {testingId === item.provider_id ? t(K.common.loading) : t(K.page.externalFactsProviders.test)}
                    </Button>
                    <Button size="small" color="error" variant="outlined" onClick={() => void removeProvider(item.provider_id)}>
                      {t(K.common.delete)}
                    </Button>
                  </Stack>
                </Stack>
              </Paper>
            ))}
            {filtered.length === 0 && (
              <Typography variant="body2" sx={{ opacity: 0.7 }}>
                {t(K.page.externalFactsProviders.empty)}
              </Typography>
            )}
            {registry.length > 0 && (
              <Typography variant="caption" sx={{ opacity: 0.72, pt: 0.5 }}>
                Registry: {registry.map((cap) => `${cap.capability_id}(${cap.items.map((it) => it.item_id).join(',')})`).join(' · ')}
              </Typography>
            )}
          </Stack>
        </Paper>
      </Stack>

      <Dialog open={formOpen} onClose={() => setFormOpen(false)} fullWidth maxWidth="md">
        <DialogTitle>{dialogTitle}</DialogTitle>
        <DialogContent dividers>
          <Box component="form">
          <Grid container rowSpacing={2.5} columnSpacing={2} sx={{ mt: 0.25 }}>
            <Grid item xs={12} md={4}>
              <TextField
                size="small"
                label={t(K.page.externalFactsProviders.providerId)}
                value={form.provider_id}
                onChange={(e) => setForm((p) => ({ ...p, provider_id: e.target.value }))}
                fullWidth
              />
            </Grid>
            <Grid item xs={12} md={4}>
              <TextField
                size="small"
                label={t(K.page.externalFactsProviders.name)}
                value={form.name}
                onChange={(e) => setForm((p) => ({ ...p, name: e.target.value }))}
                fullWidth
              />
            </Grid>
            <Grid item xs={12} md={4}>
              <FormControl size="small" fullWidth>
                <InputLabel>{t(K.page.externalFactsProviders.kind)}</InputLabel>
                <Select
                  value={form.kind}
                  label={t(K.page.externalFactsProviders.kind)}
                  onChange={(e) => {
                    const nextKind = e.target.value as FactKind
                    setForm((p) => ({ ...p, kind: nextKind }))
                    setPresetId('')
                  }}
                  onClose={blurActiveElement}
                  MenuProps={SELECT_MENU_PROPS}
                >
                  {FACT_KINDS.map((kind) => (
                    <MenuItem key={kind} value={kind}>{kindLabel(t, kind)}</MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>

            <Grid item xs={12} md={6}>
              <FormControl size="small" fullWidth>
                <InputLabel>{t(K.page.externalFactsProviders.preset)}</InputLabel>
                <Select
                  value={presetId}
                  label={t(K.page.externalFactsProviders.preset)}
                  onChange={(e) => applyPreset(e.target.value)}
                  onClose={blurActiveElement}
                  MenuProps={SELECT_MENU_PROPS}
                >
                  <MenuItem value="">{t(K.page.externalFactsProviders.presetNone)}</MenuItem>
                  {presetOptions.map((preset) => (
                    <MenuItem key={preset.id} value={preset.id}>{preset.label}</MenuItem>
                  ))}
                </Select>
              </FormControl>
              <Typography variant="caption" sx={{ display: 'block', mt: 0.75, opacity: 0.72 }}>
                {t(K.page.externalFactsProviders.presetHint)}
              </Typography>
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                size="small"
                label={t('page.externalFactsProviders.baseUrl')}
                value={form.base_url}
                onChange={(e) => setForm((p) => ({ ...p, base_url: e.target.value }))}
                fullWidth
                helperText={t('page.externalFactsProviders.baseUrlHint')}
              />
            </Grid>

            <Grid item xs={12} md={4}>
              <TextField
                size="small"
                label={t(K.page.externalFactsProviders.apiKey)}
                value={form.api_key}
                onChange={(e) => setForm((p) => ({ ...p, api_key: e.target.value }))}
                type="password"
                fullWidth
              />
            </Grid>
            <Grid item xs={12} md={4}>
              <TextField
                size="small"
                label={t(K.page.externalFactsProviders.apiKeyHeader)}
                value={form.api_key_header}
                onChange={(e) => setForm((p) => ({ ...p, api_key_header: e.target.value }))}
                fullWidth
              />
            </Grid>
            <Grid item xs={12} md={2}>
              <TextField
                size="small"
                type="number"
                label={t(K.page.externalFactsProviders.priority)}
                value={form.priority}
                onChange={(e) => setForm((p) => ({ ...p, priority: Number(e.target.value) }))}
                fullWidth
              />
            </Grid>
            <Grid item xs={12} md={2}>
              <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ height: 40, px: 1 }}>
                <Typography variant="body2">{t(K.page.externalFactsProviders.enabled)}</Typography>
                <Switch
                  checked={form.enabled}
                  onChange={(e) => setForm((p) => ({ ...p, enabled: e.target.checked }))}
                />
              </Stack>
            </Grid>

            {ENABLE_LEGACY_ENDPOINT_EDITOR ? (
              <Grid item xs={12}>
                <Typography variant="subtitle2" sx={{ mb: 1 }}>
                  Endpoints
                </Typography>
                <Stack spacing={1}>
                  {ENDPOINT_ORDER.map((key) => {
                    const cfg = form.endpoints[key]
                    return (
                      <Paper key={key} variant="outlined" sx={{ p: 1.25 }}>
                        <Stack direction="row" alignItems="center" justifyContent="space-between">
                          <Box>
                            <Typography variant="body2">{endpointLabel(key)}</Typography>
                            <Typography variant="caption" sx={{ opacity: 0.7 }}>
                              {cfg.enabled ? buildAbsoluteUrl(form.base_url, cfg.path) || '(empty)' : 'disabled'}
                            </Typography>
                          </Box>
                          <Stack direction="row" spacing={1} alignItems="center">
                            <Switch
                              size="small"
                              checked={cfg.enabled}
                              onChange={(e) =>
                                setForm((prev) => ({
                                  ...prev,
                                  endpoints: {
                                    ...prev.endpoints,
                                    [key]: { ...prev.endpoints[key], enabled: e.target.checked },
                                  },
                                }))
                              }
                            />
                            <Button size="small" variant="outlined" onClick={() => setEndpointEditKey(key)}>
                              {t(K.common.edit)}
                            </Button>
                          </Stack>
                        </Stack>
                      </Paper>
                    )
                  })}
                </Stack>
              </Grid>
            ) : (
              <Grid item xs={12}>
                <Alert severity="info">
                  {t(K.page.externalFactsProviders.endpointEditorMoved)}
                </Alert>
              </Grid>
            )}

            {ENABLE_LEGACY_ENDPOINT_EDITOR && (
              <Grid item xs={12}>
                <TextField
                  size="small"
                  multiline
                  minRows={2}
                  label={t(K.page.externalFactsProviders.capabilityText)}
                  value={form.capability_text}
                  onChange={(e) => setForm((p) => ({ ...p, capability_text: e.target.value }))}
                  fullWidth
                />
              </Grid>
            )}
            {ENABLE_LEGACY_ENDPOINT_EDITOR && (
              <Grid item xs={12}>
                <TextField
                  size="small"
                  multiline
                  minRows={4}
                  label={t(K.page.externalFactsProviders.endpointMapPreview)}
                  value={endpointMapPreview}
                  InputProps={{ readOnly: true }}
                  fullWidth
                />
              </Grid>
            )}
          </Grid>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setFormOpen(false)}>{t(K.common.cancel)}</Button>
          <Button variant="contained" onClick={() => void saveProvider()} disabled={saving}>
            {saving ? t(K.common.loading) : t(K.common.save)}
          </Button>
        </DialogActions>
      </Dialog>

      {ENABLE_LEGACY_ENDPOINT_EDITOR && (
      <Dialog open={Boolean(endpointEditKey && endpointEditing)} onClose={() => setEndpointEditKey(null)} fullWidth maxWidth="sm">
        <DialogTitle>
          {endpointEditKey
            ? t(K.page.externalFactsProviders.endpointDialogTitle, { name: endpointLabel(endpointEditKey) })
            : t(K.page.externalFactsProviders.endpointDialogTitle, { name: '' })}
        </DialogTitle>
        <DialogContent dividers>
          {endpointEditKey && endpointEditing && (
            <Grid container rowSpacing={2.5} columnSpacing={2} sx={{ mt: 0.25 }}>
              <Grid item xs={12}>
                <Alert severity="info" sx={{ mb: 0.5 }}>
                  <Typography variant="subtitle2" sx={{ mb: 0.25 }}>
                    {t(K.page.externalFactsProviders.endpointGuideTitle)}
                  </Typography>
                  <Typography variant="body2">
                    {t(K.page.externalFactsProviders.endpointGuideBody)}
                  </Typography>
                  <Typography variant="caption" sx={{ display: 'block', mt: 0.5 }}>
                    {t(K.page.externalFactsProviders.endpointGuideExample)}
                  </Typography>
                </Alert>
              </Grid>
              <Grid item xs={12}>
                <TextField
                  size="small"
                  label={t(K.page.externalFactsProviders.endpointPathLabel)}
                  value={endpointEditing.path}
                  onChange={(e) =>
                    setForm((prev) => ({
                      ...prev,
                      endpoints: {
                        ...prev.endpoints,
                        [endpointEditKey]: { ...prev.endpoints[endpointEditKey], path: e.target.value },
                      },
                    }))
                  }
                  helperText={t(K.page.externalFactsProviders.endpointPathHint)}
                  fullWidth
                />
              </Grid>
              <Grid item xs={12}>
                <TextField
                  size="small"
                  multiline
                  minRows={6}
                  label={t(K.page.externalFactsProviders.sampleJsonLabel)}
                  value={sampleJsonInput}
                  onChange={(e) => setSampleJsonInput(e.target.value)}
                  fullWidth
                  helperText={t(K.page.externalFactsProviders.sampleJsonHint)}
                />
              </Grid>
              <Grid item xs={12}>
                <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
                  <Button
                    variant="outlined"
                    onClick={() => void inferEndpointMapping()}
                    disabled={mappingLoading || !sampleJsonInput.trim()}
                  >
                    {mappingLoading ? t(K.common.loading) : t(K.page.externalFactsProviders.generateMapping)}
                  </Button>
                  <Button variant="contained" onClick={() => void applyEndpointMapping()} disabled={!canApplyProposal || mappingLoading}>
                    {t(K.page.externalFactsProviders.applyMapping)}
                  </Button>
                  <Button variant="text" onClick={() => void openHistoryDialog()} disabled={mappingLoading}>
                    {t(K.page.externalFactsProviders.mappingHistory)}
                  </Button>
                  {mappingLoading && <CircularProgress size={18} />}
                </Stack>
                <Stack direction="row" spacing={1} alignItems="center" sx={{ mt: 0.75 }}>
                  {mappingPhase === 'llm' && <Chip size="small" label={t(K.page.externalFactsProviders.mappingPhaseLlm)} />}
                  {mappingPhase === 'validate' && <Chip size="small" label={t(K.page.externalFactsProviders.mappingPhaseValidate)} />}
                  {mappingPhase === 'apply' && <Chip size="small" label={t(K.page.externalFactsProviders.mappingPhaseApply)} />}
                </Stack>
                {mappingStatusText && (
                  <Alert severity={mappingStatusLevel} sx={{ mt: 1 }}>
                    {mappingStatusText}
                  </Alert>
                )}
              </Grid>
              <Grid item xs={12}>
                <Accordion expanded={endpointExpertMode} onChange={(_, expanded) => setEndpointExpertMode(expanded)}>
                  <AccordionSummary expandIcon={<ExpandMoreIcon />} sx={{ px: 0.5 }}>
                    <Typography variant="subtitle2">{t(K.page.externalFactsProviders.expertModeTitle)}</Typography>
                  </AccordionSummary>
                  <AccordionDetails sx={{ px: 0 }}>
                    <Grid container rowSpacing={2.5} columnSpacing={2}>
                      <Grid item xs={12} md={6}>
                        <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ height: 40, px: 1 }}>
                          <Typography variant="body2">{t(K.page.externalFactsProviders.enabled)}</Typography>
                          <Switch
                            checked={endpointEditing.enabled}
                            onChange={(e) =>
                              setForm((prev) => ({
                                ...prev,
                                endpoints: {
                                  ...prev.endpoints,
                                  [endpointEditKey]: { ...prev.endpoints[endpointEditKey], enabled: e.target.checked },
                                },
                              }))
                            }
                          />
                        </Stack>
                      </Grid>
                      <Grid item xs={12} md={6}>
                        <FormControl size="small" fullWidth>
                          <InputLabel>{t(K.page.externalFactsProviders.method)}</InputLabel>
                          <Select
                            value={endpointEditing.method}
                            label={t(K.page.externalFactsProviders.method)}
                            onChange={(e) =>
                              setForm((prev) => ({
                                ...prev,
                                endpoints: {
                                  ...prev.endpoints,
                                  [endpointEditKey]: { ...prev.endpoints[endpointEditKey], method: e.target.value as EndpointMethod },
                                },
                              }))
                            }
                            onClose={blurActiveElement}
                            MenuProps={SELECT_MENU_PROPS}
                          >
                            <MenuItem value="GET">{t('page.externalFactsProviders.methodGet')}</MenuItem>
                          </Select>
                        </FormControl>
                      </Grid>
                      <Grid item xs={12} md={4}>
                        <FormControl size="small" fullWidth>
                          <InputLabel>{t('page.externalFactsProviders.responseKind')}</InputLabel>
                          <Select
                            value={endpointEditing.responseKind}
                            label={t('page.externalFactsProviders.responseKind')}
                            onChange={(e) =>
                              setForm((prev) => ({
                                ...prev,
                                endpoints: {
                                  ...prev.endpoints,
                                  [endpointEditKey]: { ...prev.endpoints[endpointEditKey], responseKind: e.target.value as EndpointResponseKind },
                                },
                              }))
                            }
                            onClose={blurActiveElement}
                            MenuProps={SELECT_MENU_PROPS}
                          >
                            <MenuItem value="point">point</MenuItem>
                            <MenuItem value="series">series</MenuItem>
                            <MenuItem value="table">table</MenuItem>
                          </Select>
                        </FormControl>
                      </Grid>
                      <Grid item xs={12} md={4}>
                        <TextField
                          size="small"
                          label={t(K.page.externalFactsProviders.asOfPath)}
                          value={endpointEditing.timePath}
                          onChange={(e) =>
                            setForm((prev) => ({
                              ...prev,
                              endpoints: {
                                ...prev.endpoints,
                                [endpointEditKey]: { ...prev.endpoints[endpointEditKey], timePath: e.target.value },
                              },
                            }))
                          }
                          fullWidth
                        />
                      </Grid>
                      <Grid item xs={12} md={4}>
                        <TextField
                          size="small"
                          label={t(K.page.externalFactsProviders.valuePath)}
                          value={endpointEditing.valuePath}
                          onChange={(e) =>
                            setForm((prev) => ({
                              ...prev,
                              endpoints: {
                                ...prev.endpoints,
                                [endpointEditKey]: { ...prev.endpoints[endpointEditKey], valuePath: e.target.value },
                              },
                            }))
                          }
                          fullWidth
                        />
                      </Grid>
                      <Grid item xs={12} md={6}>
                        <TextField
                          size="small"
                          label={t(K.page.externalFactsProviders.seriesPointsPath)}
                          value={endpointEditing.pointsPath}
                          onChange={(e) =>
                            setForm((prev) => ({
                              ...prev,
                              endpoints: {
                                ...prev.endpoints,
                                [endpointEditKey]: { ...prev.endpoints[endpointEditKey], pointsPath: e.target.value },
                              },
                            }))
                          }
                          fullWidth
                        />
                      </Grid>
                      <Grid item xs={12} md={6}>
                        <TextField
                          size="small"
                          label={t(K.page.externalFactsProviders.summaryPath)}
                          value={endpointEditing.summaryPath}
                          onChange={(e) =>
                            setForm((prev) => ({
                              ...prev,
                              endpoints: {
                                ...prev.endpoints,
                                [endpointEditKey]: { ...prev.endpoints[endpointEditKey], summaryPath: e.target.value },
                              },
                            }))
                          }
                          fullWidth
                        />
                      </Grid>
                    </Grid>
                  </AccordionDetails>
                </Accordion>
              </Grid>
              {proposalPreview && (
                <Grid item xs={12}>
                  <TextField
                    size="small"
                    multiline
                    minRows={4}
                    label={t('page.externalFactsProviders.llmMappingProposal')}
                    value={JSON.stringify(proposalPreview, null, 2)}
                    InputProps={{ readOnly: true }}
                    fullWidth
                  />
                </Grid>
              )}
              {validationPreview && (
                <Grid item xs={12}>
                  <TextField
                    size="small"
                    multiline
                    minRows={4}
                    label={t('page.externalFactsProviders.validationReport')}
                    value={JSON.stringify(validationPreview, null, 2)}
                    InputProps={{ readOnly: true }}
                    fullWidth
                  />
                </Grid>
              )}
            </Grid>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEndpointEditKey(null)}>{t(K.common.close)}</Button>
        </DialogActions>
      </Dialog>
      )}

      <Dialog open={Boolean(previewItem)} onClose={() => setPreviewItem(null)} fullWidth maxWidth="md">
        <DialogTitle>{previewItem ? `${previewItem.name} · ${previewItem.provider_id}` : t(K.common.preview)}</DialogTitle>
        <DialogContent dividers>
          <TextField
            size="small"
            multiline
            minRows={10}
            label={t(K.page.externalFactsProviders.endpointMapJson)}
            value={JSON.stringify((previewItem?.config as any)?.endpoint_map || previewItem?.endpoint_map || {}, null, 2)}
            InputProps={{ readOnly: true }}
            fullWidth
          />
          {previewItem && (
            <Typography variant="caption" sx={{ display: 'block', mt: 1, opacity: 0.72 }}>
              schema: {previewItem.endpoint_map_schema_valid ? 'valid' : 'invalid'}
              {previewItem.last_validation_error ? ` · ${previewItem.last_validation_error}` : ''}
            </Typography>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPreviewItem(null)}>{t(K.common.close)}</Button>
        </DialogActions>
      </Dialog>

      <Dialog open={historyDialogOpen} onClose={() => setHistoryDialogOpen(false)} fullWidth maxWidth="md">
        <DialogTitle>{t(K.page.externalFactsProviders.mappingHistory)}</DialogTitle>
        <DialogContent dividers>
          {!mappingHistory || !(mappingHistory.versions || []).length ? (
            <Typography variant="body2" sx={{ opacity: 0.72 }}>No versions.</Typography>
          ) : (
            <Grid container spacing={2}>
              <Grid item xs={12} md={6}>
                <Stack spacing={1}>
                  {(mappingHistory.versions || []).slice(0, 20).map((raw) => {
                    const version = raw as unknown as MappingVersionItem
                    const isActive = String(version.id) === String(mappingHistory.active_version_id || '')
                    return (
                      <Paper key={String(version.id)} variant="outlined" sx={{ p: 1.25 }}>
                        <Stack direction="row" justifyContent="space-between" alignItems="center" spacing={1}>
                          <Box>
                            <Typography variant="body2">v{Number(version.version || 0)} · {String(version.status || '')}</Typography>
                            <Typography variant="caption" sx={{ opacity: 0.72 }}>
                              fail_count: {Number(version.fail_count || 0)} · approved_at: {String(version.approved_at || '-')}
                            </Typography>
                          </Box>
                          <Stack direction="row" spacing={1} alignItems="center">
                            {isActive && <Chip size="small" label={t(K.page.externalFactsProviders.active)} color="success" />}
                            <Button size="small" variant="outlined" onClick={() => setHistoryPreviewVersion(version)}>
                              {t(K.common.preview)}
                            </Button>
                            <Button
                              size="small"
                              variant="contained"
                              disabled={isActive || mappingLoading}
                              onClick={() => setRollbackVersion(version)}
                            >
                              {t(K.page.externalFactsProviders.selectVersion)}
                            </Button>
                          </Stack>
                        </Stack>
                      </Paper>
                    )
                  })}
                </Stack>
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  size="small"
                  multiline
                  minRows={16}
                  label={t('page.externalFactsProviders.versionPreview')}
                  value={
                    historyPreviewVersion
                      ? JSON.stringify(
                          {
                            version: historyPreviewVersion.version,
                            status: historyPreviewVersion.status,
                            mapping_json: historyPreviewVersion.mapping_json || {},
                          },
                          null,
                          2,
                        )
                      : '{}'
                  }
                  InputProps={{ readOnly: true }}
                  fullWidth
                />
              </Grid>
            </Grid>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setHistoryDialogOpen(false)}>{t(K.common.close)}</Button>
        </DialogActions>
      </Dialog>

      <Dialog open={Boolean(rollbackVersion)} onClose={() => setRollbackVersion(null)} fullWidth maxWidth="xs">
        <DialogTitle>{t(K.page.externalFactsProviders.rollbackConfirmTitle)}</DialogTitle>
        <DialogContent dividers>
          <Typography variant="body2">
            {t(K.page.externalFactsProviders.rollbackConfirmBody)}
          </Typography>
          {rollbackVersion && (
            <Typography variant="caption" sx={{ display: 'block', mt: 1, opacity: 0.72 }}>
              target: v{Number(rollbackVersion.version || 0)}
            </Typography>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRollbackVersion(null)}>{t(K.common.cancel)}</Button>
          <Button
            variant="contained"
            onClick={() => rollbackVersion && void rollbackToVersion(rollbackVersion)}
            disabled={mappingLoading}
          >
            {mappingLoading ? t(K.common.loading) : t(K.page.externalFactsProviders.rollback)}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
