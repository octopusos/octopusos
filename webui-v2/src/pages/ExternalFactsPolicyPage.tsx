import { useEffect, useMemo, useState } from 'react'
import {
  Box,
  Button,
  Divider,
  FormControl,
  FormControlLabel,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Stack,
  Switch,
  TextField,
  Typography,
} from '@mui/material'
import { Link as RouterLink } from 'react-router-dom'

import { get, put } from '@platform/http/httpClient'
import { usePageHeader } from '@/ui/layout'
import { K, useTextTranslation } from '@/ui/text'

type PolicyPayload = {
  prefer_structured: boolean
  allow_search_fallback: boolean
  max_sources: number
  require_freshness_seconds: number | null
  source_whitelist: string[]
  source_blacklist: string[]
  min_confidence: 'high' | 'medium' | 'low'
}

const FACT_KINDS = [
  'weather', 'fx', 'stock', 'crypto', 'index', 'etf', 'bond_yield', 'commodity',
  'news', 'flight', 'train', 'hotel', 'traffic', 'air_quality', 'sports', 'calendar',
  'package', 'shipping', 'fuel_price', 'earthquake', 'power_outage',
] as const

type PolicyResponse = {
  ok: boolean
  data: {
    mode: string
    kind: string
    policy: PolicyPayload
  }
}

const SELECT_MENU_PROPS = {
  disableAutoFocusItem: true,
  MenuListProps: { autoFocusItem: false },
}

function blurActiveElement() {
  const active = document.activeElement
  if (active instanceof HTMLElement) active.blur()
}

export default function ExternalFactsPolicyPage() {
  const { t } = useTextTranslation()
  usePageHeader({
    title: t(K.page.externalFactsPolicy.title),
    subtitle: t(K.page.externalFactsPolicy.subtitle),
  })

  const [mode, setMode] = useState<'chat' | 'discussion'>('chat')
  const [kind, setKind] = useState<(typeof FACT_KINDS)[number]>('weather')
  const [policy, setPolicy] = useState<PolicyPayload>({
    prefer_structured: true,
    allow_search_fallback: true,
    max_sources: 3,
    require_freshness_seconds: 3600,
    source_whitelist: [],
    source_blacklist: ['reddit.com'],
    min_confidence: 'low',
  })
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [savedAt, setSavedAt] = useState('')

  const whitelistInput = useMemo(() => policy.source_whitelist.join(', '), [policy.source_whitelist])
  const blacklistInput = useMemo(() => policy.source_blacklist.join(', '), [policy.source_blacklist])

  useEffect(() => {
    void loadPolicy(mode, kind)
  }, [mode, kind])

  async function loadPolicy(nextMode: string, nextKind: string) {
    setLoading(true)
    setError('')
    try {
      const response = await get<PolicyResponse>('/api/compat/external-facts/policy', {
        params: { mode: nextMode, kind: nextKind },
      })
      setPolicy(response.data.policy)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : t(K.page.externalFactsPolicy.errorLoad))
    } finally {
      setLoading(false)
    }
  }

  async function savePolicy() {
    setSaving(true)
    setError('')
    try {
      await put('/api/compat/external-facts/policy', {
        mode,
        kind,
        ...policy,
      })
      setSavedAt(new Date().toISOString())
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : t(K.page.externalFactsPolicy.errorSave))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Box sx={{ p: 3 }}>
      <Paper sx={{ p: 3, maxWidth: 980 }} data-testid="external-facts-policy-form">
        <Stack spacing={3}>
          <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
            <Box sx={{ flex: { xs: '1 1 100%', md: '1 1 0' }, minWidth: 0 }}>
              <FormControl size="small" fullWidth>
                <InputLabel>{t(K.page.externalFactsPolicy.mode)}</InputLabel>
                <Select
                  value={mode}
                  label={t(K.page.externalFactsPolicy.mode)}
                  onChange={(e) => setMode(e.target.value as 'chat' | 'discussion')}
                  onClose={blurActiveElement}
                  MenuProps={SELECT_MENU_PROPS}
                >
                  <MenuItem value="chat">{t(K.page.externalFactsPolicy.modeChat)}</MenuItem>
                  <MenuItem value="discussion">{t(K.page.externalFactsPolicy.modeDiscussion)}</MenuItem>
                </Select>
              </FormControl>
            </Box>
            <Box sx={{ flex: { xs: '1 1 100%', md: '1 1 0' }, minWidth: 0 }}>
              <FormControl size="small" fullWidth>
                <InputLabel>{t(K.page.externalFactsPolicy.kind)}</InputLabel>
                <Select
                  value={kind}
                  label={t(K.page.externalFactsPolicy.kind)}
                  onChange={(e) => setKind(e.target.value as (typeof FACT_KINDS)[number])}
                  onClose={blurActiveElement}
                  MenuProps={SELECT_MENU_PROPS}
                >
                  {FACT_KINDS.map((item) => (
                    <MenuItem key={item} value={item}>
                      {t(`page.externalFactsPolicy.kindOption.${item}`)}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Box>
          </Box>

          <Divider />

          <Stack spacing={1.25}>
            <FormControlLabel
              control={(
                <Switch
                  checked={policy.prefer_structured}
                  onChange={(e) => setPolicy((prev) => ({ ...prev, prefer_structured: e.target.checked }))}
                />
              )}
              label={t(K.page.externalFactsPolicy.preferStructured)}
            />
            <FormControlLabel
              control={(
                <Switch
                  checked={policy.allow_search_fallback}
                  onChange={(e) => setPolicy((prev) => ({ ...prev, allow_search_fallback: e.target.checked }))}
                />
              )}
              label={t(K.page.externalFactsPolicy.allowSearchFallback)}
            />
          </Stack>

          <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
            <Box sx={{ flex: { xs: '1 1 100%', md: '1 1 0' }, minWidth: 0 }}>
              <TextField
                size="small"
                type="number"
                label={t(K.page.externalFactsPolicy.maxSources)}
                value={policy.max_sources}
                onChange={(e) => setPolicy((prev) => ({ ...prev, max_sources: Math.max(1, Number(e.target.value) || 1) }))}
                fullWidth
              />
            </Box>
            <Box sx={{ flex: { xs: '1 1 100%', md: '1 1 0' }, minWidth: 0 }}>
              <TextField
                size="small"
                type="number"
                label={t(K.page.externalFactsPolicy.freshnessSeconds)}
                value={policy.require_freshness_seconds ?? ''}
                onChange={(e) => {
                  const raw = e.target.value.trim()
                  setPolicy((prev) => ({
                    ...prev,
                    require_freshness_seconds: raw === '' ? null : Math.max(0, Number(raw) || 0),
                  }))
                }}
                fullWidth
              />
            </Box>
            <Box sx={{ flex: { xs: '1 1 100%', md: '1 1 0' }, minWidth: 0 }}>
              <FormControl size="small" fullWidth>
                <InputLabel>{t(K.page.externalFactsPolicy.minConfidence)}</InputLabel>
                <Select
                  value={policy.min_confidence}
                  label={t(K.page.externalFactsPolicy.minConfidence)}
                  onChange={(e) =>
                    setPolicy((prev) => ({ ...prev, min_confidence: e.target.value as 'high' | 'medium' | 'low' }))
                  }
                  onClose={blurActiveElement}
                  MenuProps={SELECT_MENU_PROPS}
                >
                  <MenuItem value="high">{t(K.page.externalFactsPolicy.confidenceHigh)}</MenuItem>
                  <MenuItem value="medium">{t(K.page.externalFactsPolicy.confidenceMedium)}</MenuItem>
                  <MenuItem value="low">{t(K.page.externalFactsPolicy.confidenceLow)}</MenuItem>
                </Select>
              </FormControl>
            </Box>
          </Box>

          <Stack spacing={2}>
            <TextField
              size="small"
              label={t(K.page.externalFactsPolicy.sourceWhitelist)}
              value={whitelistInput}
              onChange={(e) =>
                setPolicy((prev) => ({
                  ...prev,
                  source_whitelist: e.target.value.split(',').map((v) => v.trim()).filter(Boolean),
                }))
              }
              helperText={t(K.page.externalFactsPolicy.sourceListHint)}
              fullWidth
            />
            <TextField
              size="small"
              label={t(K.page.externalFactsPolicy.sourceBlacklist)}
              value={blacklistInput}
              onChange={(e) =>
                setPolicy((prev) => ({
                  ...prev,
                  source_blacklist: e.target.value.split(',').map((v) => v.trim()).filter(Boolean),
                }))
              }
              helperText={t(K.page.externalFactsPolicy.sourceListHint)}
              fullWidth
            />
          </Stack>
        </Stack>

        {error && (
          <Typography color="error" sx={{ mt: 2 }}>
            {error}
          </Typography>
        )}
        {savedAt && !error && (
          <Typography variant="caption" sx={{ mt: 1, display: 'block', opacity: 0.7 }}>
            {t(K.page.externalFactsPolicy.savedAt)}: {savedAt}
          </Typography>
        )}

        <Stack direction="row" spacing={1.5} sx={{ mt: 2 }}>
          <Button variant="contained" onClick={savePolicy} disabled={saving || loading}>
            {saving ? t(K.common.loading) : t(K.common.save)}
          </Button>
          <Button variant="outlined" onClick={() => void loadPolicy(mode, kind)} disabled={saving || loading}>
            {t(K.common.refresh)}
          </Button>
          <Button variant="outlined" component={RouterLink} to="/facts/schema">
            {t(K.nav.factsSchema)}
          </Button>
          <Button variant="outlined" component={RouterLink} to="/external-facts/providers">
            {t(K.nav.externalFactsProviders)}
          </Button>
        </Stack>
      </Paper>
    </Box>
  )
}
