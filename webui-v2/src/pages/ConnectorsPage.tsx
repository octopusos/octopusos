import { useEffect, useMemo, useState } from 'react'
import {
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
  Tab,
  Tabs,
  TextField,
  Typography,
} from '@mui/material'

import { del, get, post } from '@platform/http/httpClient'
import { clearToken, getToken, setToken } from '@platform/auth/adminToken'
import { usePageHeader } from '@/ui/layout'
import { K, useTextTranslation } from '@/ui/text'
import { toast } from '@/ui/feedback'

type Connector = {
  connector_id: string
  name: string
  base_url: string
  auth_type: string
  auth_header: string
  has_api_key?: boolean
  enabled: boolean
  priority: number
  updated_at: string
}

type Endpoint = {
  endpoint_id: string
  endpoint_key: string
  name: string
  capability_id: string
  item_id: string
  method: string
  path: string
  enabled: boolean
}

type ProfileBundle = {
  active_version_id?: string
  versions: Array<Record<string, unknown>>
  proposals: Array<Record<string, unknown>>
  samples: Array<Record<string, unknown>>
}

type ImportVersion = {
  id: string
  source_type: string
  source_ref?: string
  summary?: {
    added?: number
    updated?: number
    deleted?: number
    endpoint_count?: number
  }
  created_at: string
}

type ImportMode = 'text' | 'url'
type EndpointTestState = {
  status: 'idle' | 'testing' | 'ok' | 'error'
  statusCode?: number
  message?: string
}

const METHODS = ['GET', 'POST']

function endpointTitle(ep: Partial<Endpoint>) {
  return `${ep.name || ep.endpoint_key || 'endpoint'} · ${ep.method || 'GET'} ${ep.path || ''}`
}

export default function ConnectorsPage() {
  const { t } = useTextTranslation()
  usePageHeader({
    title: t(K.page.connectors.title),
    subtitle: t(K.page.connectors.subtitle),
  })

  const [adminTokenInput, setAdminTokenInput] = useState(() => getToken() || '')
  const [items, setItems] = useState<Connector[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  const [connectorDialogOpen, setConnectorDialogOpen] = useState(false)
  const [connectorForm, setConnectorForm] = useState({
    connector_id: '',
    name: '',
    base_url: '',
    auth_type: 'api_key',
    auth_header: 'Authorization',
    api_key: '',
    enabled: true,
    priority: 100,
  })

  const [manageOpen, setManageOpen] = useState(false)
  const [manageTab, setManageTab] = useState(0)
  const [manageConnector, setManageConnector] = useState<Connector | null>(null)

  const [endpoints, setEndpoints] = useState<Endpoint[]>([])
  const [endpointDialogOpen, setEndpointDialogOpen] = useState(false)
  const [endpointForm, setEndpointForm] = useState({
    endpoint_id: '',
    endpoint_key: '',
    name: '',
    capability_id: 'exchange_rate',
    item_id: 'spot',
    method: 'GET',
    path: '',
    enabled: true,
  })

  const [requestSampleJsonInput, setRequestSampleJsonInput] = useState('')
  const [responseSampleJsonInput, setResponseSampleJsonInput] = useState('')
  const [apiDocTextInput, setApiDocTextInput] = useState('')
  const [proposalId, setProposalId] = useState<string | null>(null)
  const [sampleId, setSampleId] = useState<string | null>(null)
  const [proposalPreview, setProposalPreview] = useState<Record<string, unknown> | null>(null)
  const [validationPreview, setValidationPreview] = useState<Record<string, unknown> | null>(null)
  const [canApplyProposal, setCanApplyProposal] = useState(false)
  const [mappingLoading, setMappingLoading] = useState(false)
  const [endpointOpMessage, setEndpointOpMessage] = useState('')
  const [endpointOpSeverity, setEndpointOpSeverity] = useState<'info' | 'success' | 'error'>('info')
  const [history, setHistory] = useState<ProfileBundle | null>(null)
  const [historyPreview, setHistoryPreview] = useState<Record<string, unknown> | null>(null)
  const [usageCard, setUsageCard] = useState('')
  const [endpointTab, setEndpointTab] = useState(0)

  const [importMode, setImportMode] = useState<ImportMode>('text')
  const [openApiSpec, setOpenApiSpec] = useState('')
  const [openApiUrl, setOpenApiUrl] = useState('')
  const [importing, setImporting] = useState(false)
  const [importSummary, setImportSummary] = useState<Record<string, unknown> | null>(null)
  const [importVersions, setImportVersions] = useState<ImportVersion[]>([])
  const [endpointTestStates, setEndpointTestStates] = useState<Record<string, EndpointTestState>>({})

  const manageConnectorId = manageConnector?.connector_id || ''

  const selectedEndpoint = useMemo(
    () => endpoints.find((ep) => ep.endpoint_id === endpointForm.endpoint_id) || null,
    [endpoints, endpointForm.endpoint_id],
  )

  useEffect(() => {
    void loadConnectors()
  }, [])

  useEffect(() => {
    if (!manageConnectorId) {
      setEndpoints([])
      setImportVersions([])
      setEndpointTestStates({})
      return
    }
    void loadEndpoints(manageConnectorId)
    void loadImportVersions(manageConnectorId)
  }, [manageConnectorId])

  async function loadConnectors() {
    setLoading(true)
    setError('')
    try {
      const res = await get<{ ok: boolean; data: Connector[] }>('/api/compat/connectors')
      setItems(Array.isArray(res.data) ? res.data : [])
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : t(K.page.externalFactsProviders.errorLoad))
    } finally {
      setLoading(false)
    }
  }

  async function loadEndpoints(connectorId: string) {
    try {
      const res = await get<{ ok: boolean; data: Endpoint[] }>(`/api/compat/connectors/${encodeURIComponent(connectorId)}/endpoints`)
      const next = Array.isArray(res.data) ? res.data : []
      setEndpoints(next)
      setEndpointTestStates((prev) => {
        const nextStates: Record<string, EndpointTestState> = {}
        for (const ep of next) {
          nextStates[ep.endpoint_id] = prev[ep.endpoint_id] || { status: 'idle' }
        }
        return nextStates
      })
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : t(K.page.externalFactsProviders.errorLoad))
    }
  }

  function renderTestChip(endpointId: string) {
    const state = endpointTestStates[endpointId] || { status: 'idle' as const }
    if (state.status === 'ok') {
      return (
        <Chip
          size="small"
          color="success"
          label={`${t(K.page.connectors.testStatusOk)}${state.statusCode ? ` ${state.statusCode}` : ''}`}
        />
      )
    }
    if (state.status === 'error') {
      return <Chip size="small" color="error" label={t(K.page.connectors.testStatusError)} />
    }
    if (state.status === 'testing') {
      return <Chip size="small" color="warning" label={t(K.page.connectors.testStatusTesting)} />
    }
    return <Chip size="small" variant="outlined" label={t(K.page.connectors.testStatusIdle)} />
  }

  async function loadImportVersions(connectorId: string) {
    try {
      const res = await get<{ ok: boolean; data: ImportVersion[] }>(`/api/compat/connectors/${encodeURIComponent(connectorId)}/import-versions`)
      setImportVersions(Array.isArray(res.data) ? res.data : [])
    } catch {
      setImportVersions([])
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

  function openConnectorDialog(item?: Connector) {
    if (item) {
      setConnectorForm({
        connector_id: item.connector_id,
        name: item.name,
        base_url: item.base_url,
        auth_type: item.auth_type || 'api_key',
        auth_header: item.auth_header || 'Authorization',
        api_key: '',
        enabled: Boolean(item.enabled),
        priority: Number(item.priority) || 100,
      })
    } else {
      setConnectorForm({
        connector_id: '',
        name: '',
        base_url: '',
        auth_type: 'api_key',
        auth_header: 'Authorization',
        api_key: '',
        enabled: true,
        priority: 100,
      })
    }
    setConnectorDialogOpen(true)
  }

  async function saveConnector() {
    const token = getToken()
    if (!token) {
      setError(t(K.page.externalFactsProviders.errorAdminToken))
      return
    }
    try {
      await post('/api/compat/connectors', connectorForm, {
        headers: { 'X-Admin-Token': token },
      })
      setConnectorDialogOpen(false)
      setSuccess(t(K.page.externalFactsProviders.saved))
      await loadConnectors()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : t(K.page.externalFactsProviders.errorSave))
    }
  }

  async function removeConnector(id: string) {
    const token = getToken()
    if (!token) {
      setError(t(K.page.externalFactsProviders.errorAdminToken))
      return
    }
    try {
      await del(`/api/compat/connectors/${encodeURIComponent(id)}`, {
        headers: { 'X-Admin-Token': token },
      })
      if (manageConnector?.connector_id === id) {
        setManageOpen(false)
        setManageConnector(null)
      }
      await loadConnectors()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : t(K.page.externalFactsProviders.errorDelete))
    }
  }

  function openManage(item: Connector) {
    setManageConnector(item)
    setManageTab(0)
    setOpenApiSpec('')
    setOpenApiUrl('')
    setImportSummary(null)
    setManageOpen(true)
  }

  function openEndpointDialog(item?: Endpoint) {
    if (!manageConnectorId) {
      setError(t(K.page.connectors.selectConnectorFirst))
      return
    }
    if (item) {
      setEndpointForm({
        endpoint_id: item.endpoint_id,
        endpoint_key: item.endpoint_key,
        name: item.name,
        capability_id: item.capability_id,
        item_id: item.item_id,
        method: item.method || 'GET',
        path: item.path,
        enabled: Boolean(item.enabled),
      })
    } else {
      setEndpointForm({
        endpoint_id: '',
        endpoint_key: '',
        name: '',
        capability_id: 'exchange_rate',
        item_id: 'spot',
        method: 'GET',
        path: '',
        enabled: true,
      })
    }
    setRequestSampleJsonInput('')
    setResponseSampleJsonInput('')
    setApiDocTextInput('')
    setProposalId(null)
    setSampleId(null)
    setProposalPreview(null)
    setValidationPreview(null)
    setCanApplyProposal(false)
    setHistory(null)
    setHistoryPreview(null)
    setUsageCard('')
    setEndpointTab(0)
    setEndpointDialogOpen(true)
  }

  useEffect(() => {
    if (!endpointDialogOpen || !manageConnectorId || !endpointForm.endpoint_id) return
    if (endpointTab === 1) {
      void openHistory()
    } else if (endpointTab === 2) {
      void loadUsageCard()
    }
  }, [endpointDialogOpen, endpointTab, manageConnectorId, endpointForm.endpoint_id])

  async function saveEndpoint() {
    const token = getToken()
    if (!token) {
      setError(t(K.page.externalFactsProviders.errorAdminToken))
      return
    }
    if (!manageConnectorId) return
    try {
      const res = await post<{ ok: boolean; data: Endpoint }>(
        `/api/compat/connectors/${encodeURIComponent(manageConnectorId)}/endpoints`,
        endpointForm,
        { headers: { 'X-Admin-Token': token } },
      )
      setEndpointForm((f) => ({ ...f, endpoint_id: res.data.endpoint_id }))
      await loadEndpoints(manageConnectorId)
      setSuccess(t(K.page.connectors.endpointSaved))
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : t(K.page.externalFactsProviders.errorSave))
    }
  }

  async function removeEndpoint(endpointId: string) {
    const token = getToken()
    if (!token || !manageConnectorId) {
      setError(t(K.page.externalFactsProviders.errorAdminToken))
      return
    }
    try {
      await del(`/api/compat/connectors/${encodeURIComponent(manageConnectorId)}/endpoints/${encodeURIComponent(endpointId)}`, {
        headers: { 'X-Admin-Token': token },
      })
      await loadEndpoints(manageConnectorId)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : t(K.page.externalFactsProviders.errorDelete))
    }
  }

  async function inferProfile() {
    const token = getToken()
    if (!token) {
      setError(t(K.page.externalFactsProviders.errorAdminToken))
      return
    }
    if (!manageConnectorId || !endpointForm.endpoint_id) {
      const msg = t(K.page.connectors.saveEndpointFirst)
      setError(msg)
      setEndpointOpSeverity('error')
      setEndpointOpMessage(msg)
      return
    }
    let parsedResponse: Record<string, unknown>
    try {
      parsedResponse = JSON.parse(responseSampleJsonInput || '{}')
    } catch {
      setError(t(K.page.externalFactsProviders.sampleJsonInvalid))
      return
    }
    let parsedRequest: Record<string, unknown> = {}
    if (requestSampleJsonInput.trim()) {
      try {
        parsedRequest = JSON.parse(requestSampleJsonInput || '{}')
      } catch {
        setError(t(K.page.connectors.requestSampleJsonInvalid))
        return
      }
    }
    setMappingLoading(true)
    setEndpointOpSeverity('info')
    setEndpointOpMessage(t(K.common.loading))
    console.info('[connectors] infer-profile:start', {
      connector_id: manageConnectorId,
      endpoint_id: endpointForm.endpoint_id,
      capability_id: endpointForm.capability_id,
      item_id: endpointForm.item_id,
    })
    try {
      const base = manageConnector?.base_url?.replace(/\/+$/, '') || ''
      const path = endpointForm.path || ''
      const url = path.startsWith('http') ? path : `${base}/${path.replace(/^\/+/, '')}`
      const res = await post<{ ok: boolean; data: any }>(
        `/api/compat/connectors/${encodeURIComponent(manageConnectorId)}/endpoints/${encodeURIComponent(endpointForm.endpoint_id)}/infer-profile`,
        {
          capability_id: endpointForm.capability_id,
          item_id: endpointForm.item_id,
          request_sample_json: parsedRequest,
          response_sample_json: parsedResponse,
          api_doc_text: apiDocTextInput,
          endpoint: { method: endpointForm.method, url },
        },
        { headers: { 'X-Admin-Token': token } },
      )
      console.info('[connectors] infer-profile:response', res.data)
      setProposalId(res.data.proposal_id)
      setSampleId(res.data.sample_id)
      setProposalPreview(res.data.proposal || null)
      setValidationPreview(res.data.validation_report || null)
      setCanApplyProposal(Boolean(res.data.can_apply))
      setEndpointOpSeverity(Boolean(res.data.can_apply) ? 'success' : 'info')
      setEndpointOpMessage(Boolean(res.data.can_apply) ? t(K.page.connectors.profileGenerated) : JSON.stringify(res.data.validation_report || {}))
      setSuccess(t(K.page.connectors.profileGenerated))
    } catch (err: unknown) {
      console.error('[connectors] infer-profile:error', err)
      setError(err instanceof Error ? err.message : t(K.page.externalFactsProviders.errorSave))
      setEndpointOpSeverity('error')
      setEndpointOpMessage(err instanceof Error ? err.message : t(K.page.externalFactsProviders.errorSave))
    } finally {
      setMappingLoading(false)
    }
  }

  async function applyProfile(mappingJson?: Record<string, unknown>) {
    const token = getToken()
    if (!token) {
      setError(t(K.page.externalFactsProviders.errorAdminToken))
      return
    }
    if (!manageConnectorId || !endpointForm.endpoint_id) return
    setMappingLoading(true)
    setEndpointOpMessage('')
      console.info('[connectors] apply-profile:start', {
      connector_id: manageConnectorId,
      endpoint_id: endpointForm.endpoint_id,
      use_mapping_json: Boolean(mappingJson),
      proposal_id: proposalId,
      sample_id: sampleId,
    })
    try {
      const base = manageConnector?.base_url?.replace(/\/+$/, '') || ''
      const path = endpointForm.path || ''
      const url = path.startsWith('http') ? path : `${base}/${path.replace(/^\/+/, '')}`
      await post<{ ok: boolean; data: any }>(
        `/api/compat/connectors/${encodeURIComponent(manageConnectorId)}/endpoints/${encodeURIComponent(endpointForm.endpoint_id)}/apply-profile`,
        mappingJson
          ? { mapping_json: mappingJson, endpoint: { method: endpointForm.method, url } }
          : {
              proposal_id: proposalId,
              sample_id: sampleId,
              endpoint: { method: endpointForm.method, url },
            },
        { headers: { 'X-Admin-Token': token } },
      )
      console.info('[connectors] apply-profile:ok')
      setSuccess(t(K.page.externalFactsProviders.saved))
      setEndpointOpSeverity('success')
      setEndpointOpMessage(t(K.page.externalFactsProviders.saved))
      await openHistory()
      await loadUsageCard()
    } catch (err: unknown) {
      console.error('[connectors] apply-profile:error', err)
      setError(err instanceof Error ? err.message : t(K.page.externalFactsProviders.errorSave))
      setEndpointOpSeverity('error')
      setEndpointOpMessage(err instanceof Error ? err.message : t(K.page.externalFactsProviders.errorSave))
    } finally {
      setMappingLoading(false)
    }
  }

  async function testEndpoint(endpointId: string, options?: { notify?: boolean }) {
    const notify = options?.notify !== false
    const token = getToken()
    if (!token) {
      const msg = t(K.page.externalFactsProviders.errorAdminToken)
      setError(msg)
      if (notify) toast.error(msg)
      return false
    }
    if (!manageConnectorId) {
      const msg = t(K.page.connectors.selectConnectorFirst)
      setError(msg)
      if (notify) toast.error(msg)
      return false
    }
    setEndpointTestStates((prev) => ({
      ...prev,
      [endpointId]: { status: 'testing' },
    }))
    setMappingLoading(true)
    setEndpointOpSeverity('info')
    setEndpointOpMessage(t(K.common.loading))
    console.info('[connectors] endpoint-test:start', { connector_id: manageConnectorId, endpoint_id: endpointId })
    try {
      const res = await post<{ ok: boolean; data: any }>(
        `/api/compat/connectors/${encodeURIComponent(manageConnectorId)}/endpoints/${encodeURIComponent(endpointId)}/test`,
        {},
        { headers: { 'X-Admin-Token': token } },
      )
      console.info('[connectors] endpoint-test:response', res.data)
      if (res.data?.error) {
        setEndpointOpSeverity('error')
        setEndpointOpMessage(String(res.data.error))
        setEndpointTestStates((prev) => ({
          ...prev,
          [endpointId]: { status: 'error', statusCode: Number(res.data?.status_code || 0), message: String(res.data.error) },
        }))
        if (notify) toast.error(String(res.data.error))
        return false
      } else {
        setEndpointOpSeverity('success')
        const statusCode = Number(res.data?.status_code || 200)
        setEndpointOpMessage(`HTTP ${statusCode} · ${String(res.data?.url || '')}`)
        setEndpointTestStates((prev) => ({
          ...prev,
          [endpointId]: { status: 'ok', statusCode, message: String(res.data?.url || '') },
        }))
        if (notify) toast.success(t(K.page.connectors.testEndpointPassed))
        return true
      }
    } catch (err: unknown) {
      console.error('[connectors] endpoint-test:error', err)
      setEndpointOpSeverity('error')
      const msg = err instanceof Error ? err.message : t(K.page.externalFactsProviders.errorSave)
      setEndpointOpMessage(msg)
      setEndpointTestStates((prev) => ({
        ...prev,
        [endpointId]: { status: 'error', message: msg },
      }))
      if (notify) toast.error(msg)
      return false
    } finally {
      setMappingLoading(false)
    }
  }

  async function testAllEndpoints() {
    if (!endpoints.length) {
      toast.info(t(K.page.connectors.noEndpoints))
      return
    }
    if (mappingLoading) return
    let passed = 0
    for (const ep of endpoints) {
      // Keep sequential requests to avoid rate-limit spikes.
      const ok = await testEndpoint(ep.endpoint_id, { notify: false })
      if (ok) passed += 1
    }
    const failed = endpoints.length - passed
    if (failed === 0) {
      toast.success(`${t(K.page.connectors.testAllDone)} ${passed}/${endpoints.length}`)
    } else {
      toast.warning(`${t(K.page.connectors.testAllDone)} ${passed}/${endpoints.length}, ${t(K.common.error)} ${failed}`)
    }
  }

  async function openHistory() {
    if (!manageConnectorId || !endpointForm.endpoint_id) return
    try {
      const res = await get<{ ok: boolean; data: ProfileBundle }>(
        `/api/compat/connectors/${encodeURIComponent(manageConnectorId)}/endpoints/${encodeURIComponent(endpointForm.endpoint_id)}/profiles`,
      )
      setHistory(res.data)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : t(K.page.externalFactsProviders.errorLoad))
    }
  }

  async function loadUsageCard() {
    if (!manageConnectorId || !endpointForm.endpoint_id) return
    try {
      const res = await get<{ ok: boolean; data: { content_md: string } }>(
        `/api/compat/connectors/${encodeURIComponent(manageConnectorId)}/endpoints/${encodeURIComponent(endpointForm.endpoint_id)}/usage-card`,
      )
      setUsageCard(String(res.data.content_md || ''))
    } catch {
      setUsageCard('')
    }
  }

  async function runOpenApiImport() {
    const token = getToken()
    if (!token) {
      setError(t(K.page.externalFactsProviders.errorAdminToken))
      return
    }
    if (!manageConnectorId) {
      setError(t(K.page.connectors.selectConnectorFirst))
      return
    }
    setImporting(true)
    setImportSummary(null)
    try {
      const url =
        importMode === 'text'
          ? `/api/compat/connectors/${encodeURIComponent(manageConnectorId)}/import/openapi`
          : `/api/compat/connectors/${encodeURIComponent(manageConnectorId)}/import/openapi-url`
      const payload = importMode === 'text' ? { spec: openApiSpec } : { url: openApiUrl }
      const res = await post<{ ok: boolean; data: any }>(url, payload, {
        headers: { 'X-Admin-Token': token },
      })
      setImportSummary(res.data)
      await loadEndpoints(manageConnectorId)
      await loadImportVersions(manageConnectorId)
      setSuccess(t(K.page.connectors.importSuccess))
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : t(K.page.externalFactsProviders.errorSave))
    } finally {
      setImporting(false)
    }
  }

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
            <Grid item xs={12} md={6}>
              <Button variant="contained" onClick={() => openConnectorDialog()} fullWidth>
                {t(K.page.connectors.createConnector)}
              </Button>
            </Grid>
            <Grid item xs={12} md={6}>
              <Button variant="outlined" onClick={() => void loadConnectors()} fullWidth>
                {t(K.common.refresh)}
              </Button>
            </Grid>
          </Grid>
        </Paper>

        {error && <Alert severity="error">{error}</Alert>}
        {success && <Alert severity="success">{success}</Alert>}

        <Paper sx={{ p: 2.5 }}>
          <Typography variant="h6" sx={{ mb: 1.5 }}>{t(K.page.connectors.listTitle)}</Typography>
          <Stack spacing={1.25}>
            {items.map((item) => (
              <Paper key={item.connector_id} variant="outlined" sx={{ p: 1.25 }}>
                <Stack direction="row" justifyContent="space-between" alignItems="center" spacing={1}>
                  <Box>
                    <Typography variant="subtitle2">{item.name}</Typography>
                    <Typography variant="caption" sx={{ display: 'block', opacity: 0.72 }}>{item.base_url}</Typography>
                    <Typography variant="caption" sx={{ display: 'block', opacity: 0.62 }}>
                      {item.auth_type} · {item.enabled ? 'enabled' : 'disabled'} · p{item.priority}
                    </Typography>
                  </Box>
                  <Stack direction="row" spacing={1}>
                    <Button size="small" variant="contained" onClick={() => openManage(item)}>{t(K.page.connectors.manage)}</Button>
                    <Button size="small" variant="outlined" onClick={() => openConnectorDialog(item)}>{t(K.common.edit)}</Button>
                    <Button size="small" variant="outlined" color="error" onClick={() => void removeConnector(item.connector_id)}>{t(K.common.delete)}</Button>
                  </Stack>
                </Stack>
              </Paper>
            ))}
            {!items.length && !loading && <Typography variant="body2" sx={{ opacity: 0.7 }}>{t(K.page.connectors.noConnectors)}</Typography>}
            {loading && <CircularProgress size={20} />}
          </Stack>
        </Paper>
      </Stack>

      <Dialog open={connectorDialogOpen} onClose={() => setConnectorDialogOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>{connectorForm.connector_id ? t(K.page.connectors.editConnector) : t(K.page.connectors.createConnector)}</DialogTitle>
        <DialogContent dividers>
          <Box component="form">
          <Grid container rowSpacing={2} columnSpacing={2} sx={{ mt: 0.25 }}>
            <Grid item xs={12}>
              <TextField size="small" label={t(K.page.connectors.connectorId)} value={connectorForm.connector_id} onChange={(e) => setConnectorForm((f) => ({ ...f, connector_id: e.target.value }))} fullWidth />
            </Grid>
            <Grid item xs={12}>
              <TextField size="small" label={t(K.page.externalFactsProviders.name)} value={connectorForm.name} onChange={(e) => setConnectorForm((f) => ({ ...f, name: e.target.value }))} fullWidth />
            </Grid>
            <Grid item xs={12}>
              <TextField size="small" label={t(K.page.connectors.baseUrl)} value={connectorForm.base_url} onChange={(e) => setConnectorForm((f) => ({ ...f, base_url: e.target.value }))} fullWidth />
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField size="small" label={t(K.page.externalFactsProviders.apiKey)} type="password" value={connectorForm.api_key} onChange={(e) => setConnectorForm((f) => ({ ...f, api_key: e.target.value }))} fullWidth />
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField size="small" label={t(K.page.externalFactsProviders.apiKeyHeader)} value={connectorForm.auth_header} onChange={(e) => setConnectorForm((f) => ({ ...f, auth_header: e.target.value }))} fullWidth />
            </Grid>
          </Grid>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConnectorDialogOpen(false)}>{t(K.common.cancel)}</Button>
          <Button variant="contained" onClick={() => void saveConnector()}>{t(K.common.save)}</Button>
        </DialogActions>
      </Dialog>

      <Dialog open={manageOpen} onClose={() => setManageOpen(false)} fullWidth maxWidth="lg">
        <DialogTitle>{t(K.page.connectors.manage)} · {manageConnector?.name || ''}</DialogTitle>
        <DialogContent dividers>
          <Tabs value={manageTab} onChange={(_, v) => setManageTab(v)}>
            <Tab label={t(K.page.connectors.detailEndpointsTab)} />
            <Tab label={t(K.page.connectors.detailImportTab)} />
          </Tabs>

          {manageTab === 0 && (
            <Box sx={{ pt: 2 }}>
              <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1.5 }}>
                <Typography variant="h6">{t(K.page.connectors.endpointListTitle)}</Typography>
                <Stack direction="row" spacing={1}>
                  <Button variant="outlined" onClick={() => void testAllEndpoints()} disabled={!manageConnectorId || !endpoints.length || mappingLoading}>
                    {t(K.page.connectors.testAllEndpoints)}
                  </Button>
                  <Button variant="outlined" onClick={() => openEndpointDialog()} disabled={!manageConnectorId}>{t(K.page.connectors.createEndpoint)}</Button>
                </Stack>
              </Stack>
              <Stack spacing={1}>
                {endpoints.map((ep) => (
                  <Paper key={ep.endpoint_id} variant="outlined" sx={{ p: 1.25 }}>
                    <Stack direction="row" justifyContent="space-between" alignItems="center" spacing={1}>
                      <Box>
                        <Stack direction="row" spacing={1} alignItems="center">
                          <Typography variant="subtitle2">{ep.name}</Typography>
                          {renderTestChip(ep.endpoint_id)}
                        </Stack>
                        <Typography variant="caption" sx={{ opacity: 0.72 }}>{ep.method} {ep.path}</Typography>
                        <Typography variant="caption" sx={{ display: 'block', opacity: 0.62 }}>{ep.capability_id}:{ep.item_id} · {ep.endpoint_key}</Typography>
                      </Box>
                      <Stack direction="row" spacing={1}>
                        <Button size="small" variant="outlined" onClick={() => openEndpointDialog(ep)}>{t(K.common.edit)}</Button>
                        <Button size="small" variant="outlined" onClick={() => void testEndpoint(ep.endpoint_id)} disabled={mappingLoading}>
                          {t(K.page.connectors.testEndpoint)}
                        </Button>
                        <Button size="small" variant="outlined" color="error" onClick={() => void removeEndpoint(ep.endpoint_id)}>{t(K.common.delete)}</Button>
                      </Stack>
                    </Stack>
                  </Paper>
                ))}
                {!endpoints.length && <Typography variant="body2" sx={{ opacity: 0.72 }}>{t(K.page.connectors.noEndpoints)}</Typography>}
              </Stack>
            </Box>
          )}

          {manageTab === 1 && (
            <Box sx={{ pt: 2 }}>
              <Tabs value={importMode} onChange={(_, value: ImportMode) => setImportMode(value)}>
                <Tab value="text" label={t(K.page.connectors.importFromText)} />
                <Tab value="url" label={t(K.page.connectors.importFromUrl)} />
              </Tabs>
              <Grid container rowSpacing={2} columnSpacing={2} sx={{ mt: 0.5 }}>
                {importMode === 'text' ? (
                  <Grid item xs={12}>
                    <TextField
                      size="small"
                      multiline
                      minRows={12}
                      fullWidth
                      label={t(K.page.connectors.openApiSpec)}
                      value={openApiSpec}
                      onChange={(e) => setOpenApiSpec(e.target.value)}
                    />
                  </Grid>
                ) : (
                  <Grid item xs={12}>
                    <TextField
                      size="small"
                      fullWidth
                      label={t(K.page.connectors.openApiUrl)}
                      value={openApiUrl}
                      onChange={(e) => setOpenApiUrl(e.target.value)}
                    />
                  </Grid>
                )}
                <Grid item xs={12}>
                  <Stack direction="row" spacing={1} alignItems="center">
                    <Button variant="contained" onClick={() => void runOpenApiImport()} disabled={importing || !manageConnectorId || (importMode === 'text' ? !openApiSpec.trim() : !openApiUrl.trim())}>
                      {importing ? t(K.common.loading) : t(K.page.connectors.importRun)}
                    </Button>
                    {importing && <CircularProgress size={16} />}
                  </Stack>
                </Grid>
                {importSummary && (
                  <Grid item xs={12}>
                    <Alert severity="success">
                      <Typography variant="body2">
                        {t(K.page.connectors.importSummary)}: {JSON.stringify(importSummary)}
                      </Typography>
                    </Alert>
                  </Grid>
                )}
                <Grid item xs={12}>
                  <Typography variant="subtitle2" sx={{ mb: 1 }}>{t(K.page.connectors.importVersionList)}</Typography>
                  <Stack spacing={1}>
                    {importVersions.map((v) => (
                      <Paper key={v.id} variant="outlined" sx={{ p: 1.25 }}>
                        <Stack direction="row" justifyContent="space-between" alignItems="center">
                          <Box>
                            <Typography variant="body2">{v.id}</Typography>
                            <Typography variant="caption" sx={{ opacity: 0.7 }}>{v.created_at}</Typography>
                          </Box>
                          <Chip size="small" label={`${v.summary?.added || 0}/${v.summary?.updated || 0}/${v.summary?.deleted || 0}`} />
                        </Stack>
                      </Paper>
                    ))}
                    {!importVersions.length && <Typography variant="body2" sx={{ opacity: 0.72 }}>{t(K.page.connectors.importVersionEmpty)}</Typography>}
                  </Stack>
                </Grid>
              </Grid>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setManageOpen(false)}>{t(K.common.close)}</Button>
        </DialogActions>
      </Dialog>

      <Dialog open={endpointDialogOpen} onClose={() => setEndpointDialogOpen(false)} fullWidth maxWidth="md">
        <DialogTitle>{endpointTitle(selectedEndpoint || endpointForm)}</DialogTitle>
        <DialogContent dividers>
          <Grid container rowSpacing={2} columnSpacing={2} sx={{ mt: 0.25 }}>
            <Grid item xs={12}>
              <Alert severity="info">
                <Typography variant="subtitle2" sx={{ mb: 0.5 }}>
                  Endpoint 参数说明（新增/编辑）
                </Typography>
                <Typography variant="body2">1) `capability_id + item_id` 决定这个 endpoint 会绑定到哪个事实能力（例如 `exchange_rate:spot` / `exchange_rate:series`）。</Typography>
                <Typography variant="body2">2) `path` 支持相对路径或完整 URL；推荐在 query/path 使用占位符：`&#123;base&#125;`、`&#123;quote&#125;`、`&#123;from_iso&#125;`、`&#123;to_iso&#125;`。</Typography>
                <Typography variant="body2">3) FX 常见约定：`spot`=当前单点，`series`=时间序列，`convert`=按金额换算（通常仍落到 `spot`）。</Typography>
                <Typography variant="caption" sx={{ display: 'block', mt: 0.5 }}>
                  保存 endpoint 后，再在“Sample & Infer”页贴响应样本生成 mapping，并应用版本。
                </Typography>
              </Alert>
            </Grid>
            <Grid item xs={12} md={4}>
              <TextField
                size="small"
                label={t(K.page.connectors.endpointId)}
                value={endpointForm.endpoint_id}
                onChange={(e) => setEndpointForm((f) => ({ ...f, endpoint_id: e.target.value }))}
                helperText="可选。留空会自动生成。"
                fullWidth
              />
            </Grid>
            <Grid item xs={12} md={4}>
              <TextField
                size="small"
                label={t(K.page.connectors.endpointKey)}
                value={endpointForm.endpoint_key}
                onChange={(e) => setEndpointForm((f) => ({ ...f, endpoint_key: e.target.value }))}
                helperText="建议用语义化 key，如 latest / convert / range_historical。"
                fullWidth
              />
            </Grid>
            <Grid item xs={12} md={4}>
              <TextField
                size="small"
                label={t(K.page.connectors.endpointName)}
                value={endpointForm.name}
                onChange={(e) => setEndpointForm((f) => ({ ...f, name: e.target.value }))}
                helperText="页面展示名，例如 FX Latest。"
                fullWidth
              />
            </Grid>
            <Grid item xs={12} md={4}>
              <TextField
                size="small"
                label={t(K.page.connectors.capability)}
                value={endpointForm.capability_id}
                onChange={(e) => setEndpointForm((f) => ({ ...f, capability_id: e.target.value }))}
                helperText="例如 exchange_rate。"
                fullWidth
              />
            </Grid>
            <Grid item xs={12} md={4}>
              <TextField
                size="small"
                label={t(K.page.connectors.item)}
                value={endpointForm.item_id}
                onChange={(e) => setEndpointForm((f) => ({ ...f, item_id: e.target.value }))}
                helperText="FX 推荐填 spot 或 series。"
                fullWidth
              />
            </Grid>
            <Grid item xs={12} md={4}>
              <FormControl size="small" fullWidth>
                <InputLabel>{t(K.page.externalFactsProviders.method)}</InputLabel>
                <Select value={endpointForm.method} label={t(K.page.externalFactsProviders.method)} onChange={(e) => setEndpointForm((f) => ({ ...f, method: e.target.value }))}>
                  {METHODS.map((m) => <MenuItem key={m} value={m}>{m}</MenuItem>)}
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12}>
              <TextField
                size="small"
                label={t(K.page.externalFactsProviders.endpointPathLabel)}
                value={endpointForm.path}
                onChange={(e) => setEndpointForm((f) => ({ ...f, path: e.target.value }))}
                helperText="可填 /v3/latest?base_currency={base}&currencies={quote} 或完整 URL。"
                fullWidth
              />
            </Grid>
            <Grid item xs={12}>
              <Button variant="outlined" onClick={() => void saveEndpoint()}>{t(K.page.connectors.saveEndpoint)}</Button>
            </Grid>

            <Grid item xs={12}>
              <Tabs value={endpointTab} onChange={(_, v) => setEndpointTab(v)}>
                <Tab label={t(K.page.connectors.sampleInferTab)} />
                <Tab label={t(K.page.connectors.historyTab)} />
                <Tab label={t(K.page.connectors.usageCardTab)} />
              </Tabs>
            </Grid>

            {endpointTab === 0 && (
              <>
                <Grid item xs={12}>
                  <TextField
                    size="small"
                    multiline
                    minRows={6}
                    label={t(K.page.connectors.requestSampleJsonLabel)}
                    value={requestSampleJsonInput}
                    onChange={(e) => setRequestSampleJsonInput(e.target.value)}
                    helperText={t(K.page.connectors.requestSampleJsonHint)}
                    fullWidth
                  />
                </Grid>
                <Grid item xs={12}>
                  <TextField
                    size="small"
                    multiline
                    minRows={8}
                    label={t(K.page.connectors.responseSampleJsonLabel)}
                    value={responseSampleJsonInput}
                    onChange={(e) => setResponseSampleJsonInput(e.target.value)}
                    helperText={t(K.page.externalFactsProviders.sampleJsonHint)}
                    fullWidth
                  />
                </Grid>
                <Grid item xs={12}>
                  <TextField
                    size="small"
                    multiline
                    minRows={5}
                    label={t(K.page.connectors.apiDocTextLabel)}
                    value={apiDocTextInput}
                    onChange={(e) => setApiDocTextInput(e.target.value)}
                    helperText={t(K.page.connectors.apiDocTextHint)}
                    fullWidth
                  />
                </Grid>
                <Grid item xs={12}>
                  <Stack direction="row" spacing={1} alignItems="center">
                    <Button variant="outlined" onClick={() => void inferProfile()} disabled={mappingLoading || !responseSampleJsonInput.trim()}>
                      {mappingLoading ? t(K.common.loading) : t(K.page.externalFactsProviders.generateMapping)}
                    </Button>
                    <Button variant="contained" onClick={() => void applyProfile()} disabled={mappingLoading || !canApplyProposal || !proposalId}>
                      {t(K.page.externalFactsProviders.applyMapping)}
                    </Button>
                    {mappingLoading && <CircularProgress size={16} />}
                  </Stack>
                  {endpointOpMessage && (
                    <Alert severity={endpointOpSeverity} sx={{ mt: 1.25 }}>
                      {endpointOpMessage}
                    </Alert>
                  )}
                </Grid>
                {proposalPreview && (
                  <Grid item xs={12} md={6}>
                    <TextField size="small" multiline minRows={8} label={t(K.page.connectors.proposalLabel)} value={JSON.stringify(proposalPreview, null, 2)} InputProps={{ readOnly: true }} fullWidth />
                  </Grid>
                )}
                {validationPreview && (
                  <Grid item xs={12} md={6}>
                    <TextField size="small" multiline minRows={8} label={t(K.page.connectors.validationLabel)} value={JSON.stringify(validationPreview, null, 2)} InputProps={{ readOnly: true }} fullWidth />
                  </Grid>
                )}
              </>
            )}

            {endpointTab === 1 && (
              <Grid item xs={12}>
                <Button variant="outlined" onClick={() => void openHistory()} sx={{ mb: 1 }}>{t(K.page.connectors.loadHistory)}</Button>
                <Stack spacing={1}>
                  {(history?.versions || []).map((version) => {
                    const id = String(version.id || '')
                    const isActive = id === String(history?.active_version_id || '')
                    return (
                      <Paper key={id} variant="outlined" sx={{ p: 1.25 }}>
                        <Stack direction="row" justifyContent="space-between" alignItems="center" spacing={1}>
                          <Box>
                            <Typography variant="body2">v{Number(version.version || 0)} · {String(version.status || '')}</Typography>
                            <Typography variant="caption" sx={{ opacity: 0.72 }}>fail_count: {Number(version.fail_count || 0)}</Typography>
                          </Box>
                          <Stack direction="row" spacing={1} alignItems="center">
                            {isActive && <Chip size="small" color="success" label={t(K.page.externalFactsProviders.active)} />}
                            <Button size="small" variant="outlined" onClick={() => setHistoryPreview(version as Record<string, unknown>)}>{t(K.common.preview)}</Button>
                            <Button size="small" variant="contained" disabled={isActive || mappingLoading} onClick={() => void applyProfile((version.mapping_json as Record<string, unknown>) || {})}>
                              {t(K.page.externalFactsProviders.selectVersion)}
                            </Button>
                          </Stack>
                        </Stack>
                      </Paper>
                    )
                  })}
                </Stack>
                {!history?.versions?.length && (
                  <Alert severity="info" sx={{ mt: 1.25 }}>
                    {t(K.page.connectors.noHistoryContent)}
                  </Alert>
                )}
                {historyPreview && (
                  <TextField
                    sx={{ mt: 1.5 }}
                    size="small"
                    multiline
                    minRows={8}
                    label={t(K.page.connectors.versionPreviewLabel)}
                    value={JSON.stringify(historyPreview, null, 2)}
                    InputProps={{ readOnly: true }}
                    fullWidth
                  />
                )}
              </Grid>
            )}

            {endpointTab === 2 && (
              <Grid item xs={12}>
                <Button variant="outlined" onClick={() => void loadUsageCard()} sx={{ mb: 1 }}>{t(K.page.connectors.loadUsageCard)}</Button>
                <TextField
                  size="small"
                  multiline
                  minRows={12}
                  label={t(K.page.connectors.usageCardLabel)}
                  value={usageCard}
                  InputProps={{ readOnly: true }}
                  fullWidth
                />
                {!usageCard.trim() && (
                  <Alert severity="info" sx={{ mt: 1.25 }}>
                    {t(K.page.connectors.noUsageCardContent)}
                  </Alert>
                )}
              </Grid>
            )}
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEndpointDialogOpen(false)}>{t(K.common.close)}</Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
