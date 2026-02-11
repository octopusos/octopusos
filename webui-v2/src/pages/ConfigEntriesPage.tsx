import { useEffect, useMemo, useRef, useState } from 'react'
import { Box, Button, MenuItem, Select, TextField, Typography } from '@/ui'
import { usePageHeader } from '@/ui/layout'
import { toast } from '@/ui/feedback'
import { K, useTextTranslation } from '@/ui/text'
import { type ConfigAllowlistModule } from '@services'
import { systemService } from '@services/system.service'
import { useWriteGate } from '@/ui/guards/useWriteGate'
import { WriteGateBanner } from '@/components/gates/WriteGateBanner'

type ValueType = 'String' | 'Integer' | 'Boolean'

type RowState = {
  key: string
  value: unknown
  source: string
  schemaVersion: number
  isSecret: boolean
  secretConfigured: boolean
  isHotReload: boolean
}

const KEY_TYPE_MAP: Record<string, ValueType> = {
  'calls.enabled': 'Boolean',
  'calls.recording.enabled': 'Boolean',
  'calls.recording.retention_days': 'Integer',
}

function inferType(key: string): ValueType {
  return KEY_TYPE_MAP[key] || 'String'
}

function asString(value: unknown): string {
  if (value === null || value === undefined) return ''
  if (typeof value === 'string') return value
  if (typeof value === 'number' || typeof value === 'boolean') return String(value)
  try {
    return JSON.stringify(value)
  } catch {
    return ''
  }
}

function extractBackendError(err: unknown): string {
  if (err instanceof Error) {
    return err.message
  }
  return 'Request failed'
}

function extractBackendErrorCode(err: unknown): string | null {
  if (!err || typeof err !== 'object') return null
  const maybeResponse = (err as { response?: { data?: { error?: unknown } } }).response
  const code = maybeResponse?.data?.error
  return typeof code === 'string' ? code : null
}

function inferHotReloadForKey(key: string): boolean {
  return !key.startsWith('runtime.')
}

export function ConfigEntriesContent({ readOnly = true }: { readOnly?: boolean }) {
  const { t } = useTextTranslation()
  const [loading, setLoading] = useState(true)
  const [modules, setModules] = useState<ConfigAllowlistModule[]>([])
  const [activeModule, setActiveModule] = useState('')
  const [rows, setRows] = useState<Record<string, RowState>>({})
  const [drafts, setDrafts] = useState<Record<string, string>>({})
  const [savingKey, setSavingKey] = useState<string | null>(null)
  const [scopeMode, setScopeMode] = useState<'global' | 'project'>('global')
  const [projectId, setProjectId] = useState('')

  const loadData = async () => {
    setLoading(true)
    try {
      const allowlistResp = await systemService.getConfigAllowlist()
      const allowlistModules: ConfigAllowlistModule[] = allowlistResp.modules || []
      setModules(allowlistModules)
      const defaultModule = allowlistModules[0]?.module || ''
      const resolvedActiveModule =
        activeModule && allowlistModules.some((m) => m.module === activeModule)
          ? activeModule
          : defaultModule
      if (resolvedActiveModule !== activeModule) {
        setActiveModule(resolvedActiveModule)
      }

      const selectedModule = allowlistModules.find((m) => m.module === resolvedActiveModule)
      if (!selectedModule) {
        setRows({})
        setDrafts({})
        return
      }

      const scopedProjectId =
        scopeMode === 'project' && projectId.trim().length > 0 ? projectId.trim() : undefined
      const moduleKeys = [...selectedModule.keys, ...selectedModule.secrets]

      const nextRows: Record<string, RowState> = {}
      const nextDrafts: Record<string, string> = {}
      await Promise.all(
        moduleKeys.map(async (key) => {
          const resolved = await systemService.resolveConfig(key, scopedProjectId)
          const isSecret = selectedModule.secrets.includes(key)
          let secretConfigured = false

          if (isSecret || key.endsWith('_ref')) {
            try {
              const secretStatus = await systemService.getConfigSecretStatus(key, scopedProjectId)
              secretConfigured = Boolean(secretStatus.configured)
            } catch {
              secretConfigured = false
            }
          }

          nextRows[key] = {
            key,
            value: resolved.value,
            source: resolved.source || 'default',
            schemaVersion: resolved.schema_version || 1,
            isSecret,
            secretConfigured,
            isHotReload: true,
          }
          nextDrafts[key] = asString(resolved.value)
        })
      )

      setRows(nextRows)
      setDrafts(nextDrafts)
    } catch (err) {
      toast.error(extractBackendError(err))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scopeMode, projectId, activeModule])

  const currentModule = useMemo(
    () => modules.find((m: any) => m.module === activeModule) || modules[0],
    [modules, activeModule]
  )

  const moduleKeys = useMemo(() => {
    if (!currentModule) return []
    return [...currentModule.keys, ...currentModule.secrets]
  }, [currentModule])

  const submitUpdate = async (key: string, value: string, isSecret: boolean) => {
    if (readOnly) {
      toast.info(t('common.readOnly'))
      return
    }
    const valueType = isSecret ? 'String' : inferType(key)
    let payloadValue: string | number | boolean = value
    if (valueType === 'Boolean') {
      payloadValue = String(value).toLowerCase() === 'true'
    } else if (valueType === 'Integer') {
      payloadValue = Number(value)
    }

    setSavingKey(key)
    try {
      const scopedProjectId =
        scopeMode === 'project' && projectId.trim().length > 0 ? projectId.trim() : undefined
      const payloadBase = {
        key,
        value: payloadValue,
        type: valueType,
        scope: scopeMode,
        project_id: scopedProjectId,
        is_secret: isSecret,
        is_hot_reload: inferHotReloadForKey(key),
      }

      try {
        await systemService.createConfigEntry(payloadBase as any)
      } catch (err) {
        const code = extractBackendErrorCode(err)
        if (code === 'CONFIG_REQUIRES_DRY_RUN') {
          await systemService.createConfigEntry({ ...(payloadBase as any), dry_run: true })
          await systemService.createConfigEntry({ ...(payloadBase as any), confirm: true })
        } else if (code === 'CONFIG_HIGH_RISK_CONFIRMATION_REQUIRED') {
          await systemService.createConfigEntry({ ...(payloadBase as any), confirm: true })
        } else {
          throw err
        }
      }

      toast.success(t('common.success'))
      await loadData()
    } catch (err) {
      toast.error(extractBackendError(err))
    } finally {
      setSavingKey(null)
    }
  }

  if (loading) {
    return <Typography>{t('common.loading')}</Typography>
  }

  return (
    <Box sx={{ mt: 2 }}>
      <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mb: 2 }}>
        <Select
          size="small"
          value={scopeMode}
          onChange={(e) => setScopeMode((e.target.value as 'global' | 'project') || 'global')}
          sx={{ minWidth: 180 }}
        >
          <MenuItem value="global">{t(K.page.configEntries.scopeGlobal)}</MenuItem>
          <MenuItem value="project">{t(K.page.configEntries.scopeProject)}</MenuItem>
        </Select>
        {scopeMode === 'project' && (
          <TextField
            size="small"
            placeholder={t(K.page.configEntries.projectIdPlaceholder)}
            value={projectId}
            onChange={(e) => setProjectId(e.target.value)}
            sx={{ minWidth: 220 }}
          />
        )}
        {modules.map((m) => (
          <Button
            key={m.module}
            variant={activeModule === m.module ? 'contained' : 'outlined'}
            onClick={() => setActiveModule(m.module)}
          >
            {m.title}
          </Button>
        ))}
      </Box>

      {!currentModule && <Typography>{t(K.page.configEntries.noAllowlistModules)}</Typography>}
      {currentModule && (
        <Box sx={{ display: 'grid', gap: 1 }}>
          {moduleKeys.map((key) => {
            const row = rows[key]
            if (!row) return null
            const valueType = inferType(key)
            return (
              <Box
                key={key}
                sx={{
                  border: '1px solid',
                  borderColor: 'divider',
                  borderRadius: 1,
                  p: 1.5,
                  display: 'grid',
                  gap: 1,
                }}
              >
                <Typography sx={{ fontWeight: 600 }}>{key}</Typography>
                <Typography variant="body2">
                  {t(K.page.configEntries.sourceLabel)}: {row.source} | {t(K.page.configEntries.schemaLabel)}: {row.schemaVersion} | {row.isHotReload ? t(K.page.configEntries.reloadHot) : t(K.page.configEntries.reloadRestart)}
                </Typography>
                {row.isSecret ? (
                  <>
                    <Typography variant="body2">
                      {t(K.page.configEntries.statusLabel)}: {row.secretConfigured ? t(K.page.configEntries.configured) : t(K.page.configEntries.notConfigured)}
                    </Typography>
                    <TextField
                      size="small"
                      fullWidth
                      placeholder={t(K.page.configEntries.secretRefPlaceholder)}
                      value={drafts[key] || ''}
                      onChange={(e) => setDrafts((prev) => ({ ...prev, [key]: e.target.value }))}
                      disabled={readOnly}
                    />
                    <Box>
                      <Button
                        variant="contained"
                        disabled={readOnly || savingKey === key || !drafts[key] || (scopeMode === 'project' && !projectId)}
                        onClick={() => submitUpdate(key, drafts[key] || '', true)}
                      >
                        {savingKey === key ? t('common.loading') : t(K.page.configEntries.updateSecretRef)}
                      </Button>
                    </Box>
                  </>
                ) : (
                  <>
                    {valueType === 'Boolean' ? (
                      <Select
                        size="small"
                        fullWidth
                        value={String(drafts[key] ?? asString(row.value))}
                        onChange={(e) => setDrafts((prev) => ({ ...prev, [key]: e.target.value }))}
                        disabled={readOnly}
                      >
                        <MenuItem value="true">true</MenuItem>
                        <MenuItem value="false">false</MenuItem>
                      </Select>
                    ) : (
                      <TextField
                        size="small"
                        fullWidth
                        value={drafts[key] ?? asString(row.value)}
                        type={valueType === 'Integer' ? 'number' : 'text'}
                        onChange={(e) => setDrafts((prev) => ({ ...prev, [key]: e.target.value }))}
                        disabled={readOnly}
                      />
                    )}
                    <Box>
                      <Button
                        variant="contained"
                        disabled={readOnly || savingKey === key || (scopeMode === 'project' && !projectId)}
                        onClick={() => submitUpdate(key, drafts[key] ?? asString(row.value), false)}
                      >
                        {savingKey === key ? t('common.loading') : t('common.save')}
                      </Button>
                    </Box>
                  </>
                )}
              </Box>
            )
          })}
        </Box>
      )}
    </Box>
  )
}

export default function ConfigEntriesPage() {
  const { t } = useTextTranslation()
  const writeGate = useWriteGate('FEATURE_CONFIG_WRITE')
  const lastGateToastRef = useRef<string | null>(null)
  usePageHeader({
    title: t('page.configEntries.title'),
    subtitle: t('page.configEntries.subtitle'),
  })
  const editingEnabled = import.meta.env.VITE_CONFIG_UI_EDITING_ENABLED !== 'false'

  useEffect(() => {
    if (writeGate.allowed) {
      lastGateToastRef.current = 'OK'
      return
    }

    const missing = writeGate.missingOperations
    const toastKey = `${writeGate.reason}:${missing.join(',')}`
    if (lastGateToastRef.current === toastKey) return
    lastGateToastRef.current = toastKey

    if (writeGate.reason === 'CONTRACT_UNAVAILABLE' && missing.length > 0) {
      toast.info(`${t('gate.write.contractUnavailable.title')} (${missing.join(', ')})`)
      return
    }
    if (writeGate.reason === 'MODE_READONLY') {
      toast.info(t('gate.write.modeReadOnly.title'))
      return
    }
    toast.info(t('gate.write.contractUnavailable.title'))
  }, [t, writeGate.allowed, writeGate.missingOperations, writeGate.reason])

  return (
    <>
      <WriteGateBanner
        featureKey="FEATURE_CONFIG_WRITE"
        reason={writeGate.reason}
        missingOperations={writeGate.missingOperations}
      />
      <ConfigEntriesContent readOnly={!editingEnabled || !writeGate.allowed} />
    </>
  )
}
