/* eslint-disable react/jsx-no-literals */
import { useState, useEffect, useCallback, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { usePageHeader, usePageActions } from '@/ui/layout'
import { AppCard, AppCardHeader, AppCardBody, LoadingState } from '@/ui'
import { K, useTextTranslation } from '@/ui/text'
// eslint-disable-next-line no-restricted-imports -- G3 Exception: useTheme and alpha are MUI utilities (not components) needed for theme token access
import { Box, Typography, useTheme, alpha, Button, Stack } from '@mui/material'
import { RefreshIcon } from '@/ui/icons'
import { systemService } from '@/services/system.service'
import { riskService } from '@/services/risk.service'
import { useSnackbar } from 'notistack'

type HealthStatus = 'ok' | 'degraded' | 'error' | 'warn'

type ActionCard = {
  title: string
  description: string
  buttonLabel: string
  path: string
  critical?: boolean
}

type StatusBadge = {
  icon: string
  label: string
  color: 'success.main' | 'warning.main' | 'error.main'
}

export default function HomePage() {
  const { t } = useTextTranslation()
  const theme = useTheme()
  const navigate = useNavigate()
  const { enqueueSnackbar } = useSnackbar()

  const [loading, setLoading] = useState(true)
  const [runtimeInfo, setRuntimeInfo] = useState<{
    version: string
    uptime: number
    environment: string
    features: string[]
    pid: number
  } | null>(null)
  const [metrics, setMetrics] = useState<{
    cpu_usage: number
    memory_usage: number
    disk_usage: number
    network_rx: number
    network_tx: number
  } | null>(null)
  const [healthCheck, setHealthCheck] = useState<{
    status: HealthStatus
    components: Record<string, { status: string; message?: string }>
    timestamp: string
  } | null>(null)
  const [riskStatus, setRiskStatus] = useState<{
    overall_risk: number
    execution_risk: number
    trust_risk: number
    policy_risk: number
    capability_risk: number
  } | null>(null)

  const octopusosRaw: {
    bg?: Record<string, string>
    border?: Record<string, string>
    shape?: { radius: { sm: number; md: number; lg: number } }
  } | null = (theme as { octopusos?: Record<string, unknown> }).octopusos ?? (theme.palette as { octopusos?: Record<string, unknown> }).octopusos ?? null

  const bg = octopusosRaw?.bg ?? {
    canvas: theme.palette.background.default,
    surface: alpha(theme.palette.background.default, 0.9),
    paper: theme.palette.background.paper,
    section: alpha(theme.palette.background.paper, 0.55),
    elevated: alpha(theme.palette.background.paper, 0.8),
  }

  const border = octopusosRaw?.border ?? {
    subtle: theme.palette.mode === 'light' ? 'rgba(0,0,0,0.08)' : 'rgba(255,255,255,0.06)',
    strong: theme.palette.mode === 'light' ? 'rgba(0,0,0,0.12)' : 'rgba(255,255,255,0.10)',
  }

  const shape = octopusosRaw?.shape ?? {
    radius: { sm: 10, md: 14, lg: 18 },
  }

  const octopusos = {
    bg,
    border,
    shape,
    ...octopusosRaw,
  }

  const fetchData = useCallback(async () => {
    try {
      setLoading(true)

      // Real API calls: runtime info + metrics + health check + risk status
      const [runtimeRes, metricsRes, healthRes, riskRes] = await Promise.all([
        systemService.getRuntimeInfo().catch((err: unknown) => ({ error: err })),
        systemService.getMetricsJson().catch((err: unknown) => ({ error: err })),
        systemService.healthCheck().catch((err: unknown) => ({ error: err })),
        riskService.getCurrentRiskStatus().catch((err: unknown) => ({ error: err })),
      ])

      // Handle runtime info
      if (runtimeRes && typeof runtimeRes === 'object' && !('error' in runtimeRes)) {
        setRuntimeInfo(runtimeRes)
      }

      if (metricsRes && typeof metricsRes === 'object' && !('error' in metricsRes)) {
        const metricsData = metricsRes.metrics || metricsRes
        setMetrics(metricsData as typeof metrics)
      }

      if (healthRes && typeof healthRes === 'object' && !('error' in healthRes)) {
        setHealthCheck(healthRes)
      }

      if (riskRes && typeof riskRes === 'object' && !('error' in riskRes)) {
        setRiskStatus(riskRes)
      }

      const allFailed = (!runtimeRes || (typeof runtimeRes === 'object' && 'error' in runtimeRes)) &&
                        (!metricsRes || (typeof metricsRes === 'object' && 'error' in metricsRes)) &&
                        (!healthRes || (typeof healthRes === 'object' && 'error' in healthRes)) &&
                        (!riskRes || (typeof riskRes === 'object' && 'error' in riskRes))
      if (allFailed) {
        enqueueSnackbar(t('common.error') + ': Failed to load dashboard data', { variant: 'error' })
      }
    } catch (error) {
      console.error('Unexpected error fetching dashboard data:', error)
      enqueueSnackbar(t('common.error') + ': ' + String(error), { variant: 'error' })
    } finally {
      setLoading(false)
    }
  }, [enqueueSnackbar, t])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const handleRefresh = async () => {
    enqueueSnackbar(t('common.loading') + '...', { variant: 'info' })
    await fetchData()
    enqueueSnackbar(t('common.success'), { variant: 'success' })
  }

  const pageHelp = useMemo(() => ({
    purpose: t(K.page.home.helpPurpose),
    usage: t(K.page.home.helpUsage),
    howToUse: t(K.page.home.helpHowToUse),
    details: t(K.page.home.helpDetails),
    steps: [
      t(K.page.home.helpStep1),
      t(K.page.home.helpStep2),
      t(K.page.home.helpStep3),
      t(K.page.home.helpStep4),
    ],
  }), [t])

  usePageHeader({
    title: t(K.page.home.title),
    subtitle: t(K.page.home.subtitle),
    help: pageHelp,
  })

  usePageActions([
    {
      key: 'refresh',
      label: t('common.refresh'),
      icon: <RefreshIcon />,
      variant: 'contained',
      onClick: handleRefresh,
    },
  ])

  const getBadge = (state: 'runnable' | 'needsConfig' | 'blocked'): StatusBadge => {
    if (state === 'runnable') return { icon: '✅', label: t(K.page.home.statusRunnable), color: 'success.main' }
    if (state === 'needsConfig') return { icon: '⚠️', label: t(K.page.home.statusNeedsConfig), color: 'warning.main' }
    return { icon: '❌', label: t(K.page.home.statusBlocked), color: 'error.main' }
  }

  const runtimeState: 'runnable' | 'needsConfig' | 'blocked' =
    !healthCheck ? 'needsConfig' : healthCheck.status === 'ok' ? 'runnable' : healthCheck.status === 'error' ? 'blocked' : 'needsConfig'

  const setupState: 'runnable' | 'needsConfig' | 'blocked' =
    runtimeInfo && runtimeInfo.features?.includes('providers') ? 'runnable' : 'needsConfig'

  const writeState: 'runnable' | 'needsConfig' | 'blocked' = (() => {
    if (!riskStatus) return 'needsConfig'
    if (riskStatus.overall_risk >= 70) return 'blocked'
    if (riskStatus.overall_risk >= 30) return 'needsConfig'
    return 'runnable'
  })()

  const ctaCards: ActionCard[] = [
    {
      title: t(K.page.home.ctaConnectProjectTitle),
      description: t(K.page.home.ctaConnectProjectDesc),
      buttonLabel: t(K.page.home.ctaConnectProjectAction),
      path: '/projects',
    },
    {
      title: t(K.page.home.ctaSafeTaskTitle),
      description: t(K.page.home.ctaSafeTaskDesc),
      buttonLabel: t(K.page.home.ctaSafeTaskAction),
      path: '/tasks',
    },
    {
      title: t(K.page.home.ctaHealthTitle),
      description: t(K.page.home.ctaHealthDesc),
      buttonLabel: t(K.page.home.ctaHealthAction),
      path: '/system-health',
    },
    {
      title: t(K.page.home.ctaEvidenceTitle),
      description: t(K.page.home.ctaEvidenceDesc),
      buttonLabel: t(K.page.home.ctaEvidenceAction),
      path: '/evidence-chains',
    },
    {
      title: t(K.page.home.ctaAdminTokenTitle),
      description: t(K.page.home.ctaAdminTokenDesc),
      buttonLabel: t(K.page.home.ctaAdminTokenAction),
      path: '/config',
      critical: true,
    },
  ]

  if (loading) {
    return <LoadingState />
  }

  return (
    <Box
      sx={{
        display: 'grid',
        gridTemplateColumns: { xs: '1fr', lg: '2fr 1fr' },
        gap: 3,
        alignItems: 'start',
      }}
    >
      <Stack spacing={3}>
        <AppCard>
          <AppCardHeader title={t(K.page.home.questionStripTitle)} />
          <AppCardBody>
            <Stack spacing={1.25}>
              <Typography variant="body2" color="text.secondary">{t(K.page.home.questionCanDo)}</Typography>
              <Typography variant="body2" color="text.secondary">{t(K.page.home.questionNext)}</Typography>
              <Typography variant="body2" color="text.secondary">{t(K.page.home.questionRisk)}</Typography>
              <Typography variant="body2" color="text.secondary">{t(K.page.home.questionHelp)}</Typography>
            </Stack>
          </AppCardBody>
        </AppCard>

        <AppCard>
          <AppCardHeader title={t(K.page.home.taskEntryTitle)} />
          <AppCardBody>
            <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 2 }}>
              {ctaCards.map((card) => (
                <Box
                  key={card.path}
                  sx={{
                    p: 2,
                    border: `1px solid ${card.critical ? theme.palette.error.main : octopusos.border.subtle}`,
                    borderRadius: 2,
                    bgcolor: card.critical ? alpha(theme.palette.error.main, 0.06) : octopusos.bg.section,
                    display: 'flex',
                    flexDirection: 'column',
                    gap: 1.25,
                  }}
                >
                  <Typography variant="subtitle1" fontWeight={700}>{card.title}</Typography>
                  <Typography variant="body2" color="text.secondary">{card.description}</Typography>
                  <Box sx={{ mt: 'auto' }}>
                    <Button
                      variant={card.critical ? 'outlined' : 'contained'}
                      color={card.critical ? 'error' : 'primary'}
                      onClick={() => navigate(card.path)}
                    >
                      {card.buttonLabel}
                    </Button>
                  </Box>
                </Box>
              ))}
            </Box>
          </AppCardBody>
        </AppCard>

        <AppCard>
          <AppCardHeader title={t(K.page.home.safetyTitle)} />
          <AppCardBody>
            <Stack spacing={1.25}>
              <Typography variant="body2" color="text.secondary">• {t(K.page.home.safetyPromiseOne)}</Typography>
              <Typography variant="body2" color="text.secondary">• {t(K.page.home.safetyPromiseTwo)}</Typography>
              <Typography variant="body2" color="text.secondary">• {t(K.page.home.safetyPromiseThree)}</Typography>
            </Stack>
          </AppCardBody>
        </AppCard>

        <AppCard>
          <AppCardHeader title={t(K.page.home.systemStatusTitle)} />
          <AppCardBody>
            <Stack spacing={1.5}>
              {[
                {
                  key: 'runtime',
                  title: t(K.page.home.systemStatusRuntimeTitle),
                  description: t(K.page.home.systemStatusRuntimeDesc),
                  badge: getBadge(runtimeState),
                  actionLabel: t(K.page.home.systemStatusRuntimeAction),
                  path: '/system-health',
                },
                {
                  key: 'setup',
                  title: t(K.page.home.systemStatusSetupTitle),
                  description: t(K.page.home.systemStatusSetupDesc),
                  badge: getBadge(setupState),
                  actionLabel: t(K.page.home.systemStatusSetupAction),
                  path: '/providers',
                },
                {
                  key: 'write',
                  title: t(K.page.home.systemStatusWriteTitle),
                  description: t(K.page.home.systemStatusWriteDesc),
                  badge: getBadge(writeState),
                  actionLabel: t(K.page.home.systemStatusWriteAction),
                  path: '/config',
                },
              ].map((item) => (
                <Box
                  key={item.key}
                  sx={{
                    p: 2,
                    border: `1px solid ${octopusos.border.subtle}`,
                    borderRadius: 2,
                    bgcolor: octopusos.bg.section,
                    display: 'grid',
                    gridTemplateColumns: { xs: '1fr', md: 'auto 1fr auto' },
                    gap: 1.5,
                    alignItems: 'center',
                  }}
                >
                  <Typography sx={{ color: item.badge.color, fontWeight: 700 }}>
                    {item.badge.icon} {item.badge.label}
                  </Typography>
                  <Box>
                    <Typography variant="body1" fontWeight={600}>{item.title}</Typography>
                    <Typography variant="body2" color="text.secondary">{item.description}</Typography>
                  </Box>
                  <Button variant="text" onClick={() => navigate(item.path)}>
                    {item.actionLabel}
                  </Button>
                </Box>
              ))}
            </Stack>

            <Box
              sx={{
                mt: 2,
                p: 1.5,
                borderRadius: 2,
                border: `1px dashed ${octopusos.border.subtle}`,
                bgcolor: octopusos.bg.canvas,
              }}
            >
              <Typography variant="caption" color="text.secondary">
                {t(K.page.home.systemMeta)}
                {runtimeInfo?.version ? ` v${runtimeInfo.version}` : ''}
                {metrics?.cpu_usage != null ? ` · CPU ${metrics.cpu_usage.toFixed(1)}%` : ''}
              </Typography>
            </Box>
          </AppCardBody>
        </AppCard>
      </Stack>

      <Stack spacing={3} sx={{ position: { lg: 'sticky' }, top: { lg: 0 }, alignSelf: 'start' }}>
        <AppCard>
          <AppCardHeader title={t(K.page.home.copilotTitle)} />
          <AppCardBody>
            <Stack spacing={1.5}>
              <Typography variant="subtitle1" fontWeight={700}>
                {t(K.page.home.copilotSubtitle)}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {t(K.page.home.copilotDescription)}
              </Typography>
              <Button variant="contained" onClick={() => navigate('/chat')}>
                {t(K.page.home.copilotAction)}
              </Button>
            </Stack>
          </AppCardBody>
        </AppCard>

        <AppCard>
          <AppCardHeader title={t(K.page.home.supportTitle)} />
          <AppCardBody>
            <Stack spacing={1.25}>
              <Button variant="outlined" onClick={() => navigate('/dispatch-review')}>
                {t(K.page.home.supportActionReview)}
              </Button>
              <Button variant="outlined" onClick={() => navigate('/governance')}>
                {t(K.page.home.supportActionGovernance)}
              </Button>
            </Stack>
          </AppCardBody>
        </AppCard>
      </Stack>
    </Box>
  )
}
