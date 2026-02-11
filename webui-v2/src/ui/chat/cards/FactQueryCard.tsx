import AccessTimeIcon from '@mui/icons-material/AccessTime'
import { Box, Card, CardContent, Chip, Divider, Stack, Typography } from '@mui/material'
import { useMemo, useRef, useState } from 'react'
import { K, useTextTranslation } from '@/ui/text'
import { UniversalTrendChart } from './UniversalTrendChart'
import { CardExportActions } from './CardExportActions'
import {
  buildFxNarrative,
  buildFxNumericSummary,
  computeFxWindowStats,
  fxNarrativeLint,
  type FxSample,
} from './fxNarrative'

type MetricItem = {
  label: string
  value: string
}

type TrendPoint = {
  time: string
  value: number
}

type FactQueryCardProps = {
  kind?: string
  title: string
  subtitle?: string
  headline?: string
  unit?: string
  summary?: string
  metrics?: MetricItem[]
  trend?: TrendPoint[]
  updatedAt?: string
  source?: string
  safeSummary?: boolean
  sensitiveExport?: boolean
}

const tokens = {
  radius: 16,
  pad: 16,
  bg: 'linear-gradient(180deg, rgba(18,22,30,0.95) 0%, rgba(16,18,26,0.98) 100%)',
  surface: 'rgba(255,255,255,0.06)',
  surface2: 'rgba(255,255,255,0.09)',
  border: 'rgba(255,255,255,0.10)',
  textPrimary: 'rgba(255,255,255,0.92)',
  textSecondary: 'rgba(255,255,255,0.70)',
  textTertiary: 'rgba(255,255,255,0.52)',
}

function compactUpdatedLabel(updatedAt: string | undefined, t: (key: string, params?: Record<string, string | number>) => string): string {
  if (!updatedAt) return t(K.component.factQueryCard.updatedRecently)
  const ts = new Date(updatedAt).getTime()
  if (Number.isNaN(ts)) return t(K.component.factQueryCard.updatedRecently)
  const diffMins = Math.max(1, Math.round((Date.now() - ts) / 60000))
  if (diffMins < 60) return t(K.component.factQueryCard.updatedMinutesAgo, { minutes: diffMins })
  const diffHours = Math.round(diffMins / 60)
  return t(K.component.factQueryCard.updatedHoursAgo, { hours: diffHours })
}

function parseWindowMinutes(metrics: MetricItem[], trend: TrendPoint[]): number {
  const windowMetric = metrics.find((item) => item.label.toLowerCase() === 'window')
  if (windowMetric) {
    const match = String(windowMetric.value).match(/(\d+)/)
    if (match) return Math.max(1, Number(match[1]))
  }
  if (trend.length >= 2) {
    const first = new Date(trend[0].time).getTime()
    const last = new Date(trend[trend.length - 1].time).getTime()
    if (Number.isFinite(first) && Number.isFinite(last) && last > first) {
      return Math.max(1, Math.round((last - first) / 60000))
    }
  }
  return 5
}

function looksLikeFx(kind?: string, title?: string, subtitle?: string): boolean {
  const k = (kind || '').toLowerCase()
  if (k === 'fx' || k === 'exchange_rate') return true
  const text = `${title || ''} ${subtitle || ''}`.toLowerCase()
  return text.includes('fx') || text.includes('exchange rate') || text.includes('aud/') || text.includes('/cny')
}

function looksLikeStock(kind?: string, title?: string, subtitle?: string): boolean {
  const k = (kind || '').toLowerCase()
  if (k === 'stock') return true
  const text = `${title || ''} ${subtitle || ''}`.toLowerCase()
  return text.includes('stock') || text.includes('股票')
}

function toTs(time: string, fallback: number): number {
  const ts = new Date(time).getTime()
  if (Number.isFinite(ts)) return ts
  return fallback
}

export function FactQueryCard({
  kind,
  title,
  subtitle,
  headline,
  unit,
  summary,
  metrics = [],
  trend = [],
  updatedAt,
  source,
  safeSummary = false,
  sensitiveExport = false,
}: FactQueryCardProps) {
  const { t } = useTextTranslation()
  const cardRef = useRef<HTMLDivElement>(null)
  const [focusIndex, setFocusIndex] = useState(0)
  const isFxCard = useMemo(() => looksLikeFx(kind, title, subtitle), [kind, title, subtitle])
  const isStockCard = useMemo(() => looksLikeStock(kind, title, subtitle), [kind, title, subtitle])
  const windowMinutes = useMemo(() => parseWindowMinutes(metrics, trend), [metrics, trend])
  const fxSamples = useMemo<FxSample[]>(
    () =>
      trend
        .filter((p) => Number.isFinite(p.value))
        .map((p, idx) => ({ ts: toTs(p.time, idx * 1000), rate: Number(p.value) })),
    [trend]
  )
  const fxStats = useMemo(() => computeFxWindowStats(fxSamples, windowMinutes * 60_000), [fxSamples, windowMinutes])
  const fxPairLabel = useMemo(() => {
    const s = String(subtitle || '').trim()
    if (s.includes('/')) return s
    const t = String(title || '')
    const match = t.match(/[A-Z]{3}\/[A-Z]{3}/)
    return match ? match[0] : 'AUD/CNY'
  }, [subtitle, title])
  const fxNarrative = useMemo(() => {
    if (!isFxCard) return ''
    const draft = buildFxNarrative(fxStats, fxPairLabel)
    const lint = fxNarrativeLint(draft)
    return lint.ok ? draft : buildFxNumericSummary(fxStats, fxPairLabel)
  }, [isFxCard, fxStats, fxPairLabel])
  const visibleMetrics = useMemo(() => {
    if (!isFxCard) return metrics.slice(0, 4)
    return [
      { label: t(K.component.factQueryCard.metricWindow), value: `${windowMinutes}m` },
      { label: t(K.component.factQueryCard.metricSamples), value: String(fxStats.count) },
      { label: t(K.component.factQueryCard.metricMin), value: fxStats.minRate === null ? '--' : fxStats.minRate.toFixed(6) },
      { label: t(K.component.factQueryCard.metricMax), value: fxStats.maxRate === null ? '--' : fxStats.maxRate.toFixed(6) },
    ]
  }, [isFxCard, metrics, windowMinutes, fxStats.count, fxStats.minRate, fxStats.maxRate, t])
  const chartPoints = useMemo(
    () => (isFxCard
      ? fxStats.samples.map((p) => ({ t: new Date(p.ts).toISOString(), temp: p.rate }))
      : trend.filter((p) => Number.isFinite(p.value)).map((p) => ({ t: p.time, temp: p.value }))),
    [isFxCard, fxStats.samples, trend]
  )
  const exportRows = useMemo(
    () => chartPoints.map((p) => ({ time: p.t, value: p.temp })),
    [chartPoints]
  )

  return (
    <Card
      ref={cardRef}
      sx={{
        width: '100%',
        maxWidth: 820,
        borderRadius: `${tokens.radius}px`,
        background: tokens.bg,
        border: `1px solid ${tokens.border}`,
        boxShadow: 'none',
        color: tokens.textPrimary,
      }}
    >
      <CardContent sx={{ p: `${tokens.pad}px !important` }}>
        <Stack spacing={1.5}>
          <Stack direction="row" alignItems="flex-start" justifyContent="space-between" gap={1.5}>
            <Box>
              <Typography variant="h6" sx={{ fontWeight: 700, lineHeight: 1.1 }}>
                {title}
              </Typography>
              {subtitle && (
                <Typography variant="body2" sx={{ color: tokens.textSecondary, mt: 0.35 }}>
                  {subtitle}
                </Typography>
              )}
            </Box>
            <Stack direction="row" alignItems="center" spacing={0.75} sx={{ flexShrink: 0 }}>
              <CardExportActions
                targetRef={cardRef}
                fileBaseName={`${title || 'query-card'}`}
                sensitive={sensitiveExport}
                tableData={{ columns: ['time', 'value'], rows: exportRows }}
              />
              <Chip
                size="small"
                icon={<AccessTimeIcon sx={{ fontSize: 14 }} />}
                label={compactUpdatedLabel(updatedAt, t)}
                sx={{ bgcolor: tokens.surface, color: tokens.textSecondary, height: 24 }}
              />
              {source && (
                <Chip
                  size="small"
                  label={source}
                  sx={{ bgcolor: tokens.surface2, color: tokens.textSecondary, height: 24 }}
                />
              )}
            </Stack>
          </Stack>

          {!safeSummary && headline && (
            <Stack direction="row" alignItems="baseline" spacing={0.75}>
              <Typography sx={{ fontSize: { xs: 40, sm: 48 }, fontWeight: 800, lineHeight: 1 }}>
                {headline}
              </Typography>
              {unit && (
                <Typography sx={{ fontSize: 18, color: tokens.textSecondary }}>
                  {unit}
                </Typography>
              )}
            </Stack>
          )}

          {summary && !(isStockCard && !safeSummary) && (
            <Typography variant="body2" sx={{ color: tokens.textSecondary }}>
              {summary}
            </Typography>
          )}

          {visibleMetrics.length > 0 && (
            <Stack direction="row" spacing={1} sx={{ overflowX: 'auto', pb: 0.25 }}>
              {visibleMetrics.map((metric, index) => {
                const selected = index === focusIndex
                return (
                  <Box
                    key={`${metric.label}-${index}`}
                    onClick={() => setFocusIndex(index)}
                    sx={{
                      minWidth: 124,
                      px: 1.25,
                      py: 1,
                      borderRadius: 2,
                      bgcolor: selected ? tokens.surface2 : tokens.surface,
                      cursor: 'pointer',
                    }}
                  >
                    <Typography variant="caption" sx={{ color: tokens.textSecondary, fontWeight: 600 }}>
                      {metric.label}
                    </Typography>
                    <Typography variant="body2" sx={{ fontWeight: 700, mt: 0.35 }}>
                      {metric.value}
                    </Typography>
                  </Box>
                )
              })}
            </Stack>
          )}

          {!safeSummary && chartPoints.length > 1 && (
            <Box sx={{ mt: 0.5, mb: 0.75 }}>
              <UniversalTrendChart
                points={chartPoints.map((p) => ({ time: p.t, value: p.temp }))}
                engine="ag"
                xAxisLabel={t(K.component.factQueryCard.axisTime)}
                yAxisLabel={isFxCard ? fxPairLabel : t(K.component.factQueryCard.axisValue)}
                windowMs={windowMinutes * 60_000}
                showExtrema={isFxCard}
              />
            </Box>
          )}
          {isFxCard && (
            <Box
              sx={{
                mt: 0.5,
                p: 1.25,
                borderRadius: 2,
                bgcolor: tokens.surface,
                border: `1px solid ${tokens.border}`,
              }}
            >
              <Typography variant="subtitle2" sx={{ color: tokens.textPrimary, fontWeight: 700, mb: 0.5 }}>
                {t(K.component.factQueryCard.fxNarrativeTitle, { minutes: windowMinutes })}
              </Typography>
              <Typography variant="body2" sx={{ color: tokens.textSecondary, lineHeight: 1.6 }}>
                {fxNarrative}
              </Typography>
            </Box>
          )}
          {isStockCard && summary && !safeSummary && (
            <Box
              sx={{
                mt: 0.5,
                p: 1.25,
                borderRadius: 2,
                bgcolor: tokens.surface,
                border: `1px solid ${tokens.border}`,
              }}
            >
              <Typography variant="subtitle2" sx={{ color: tokens.textPrimary, fontWeight: 700, mb: 0.5 }}>
                走势解读
              </Typography>
              <Typography variant="body2" sx={{ color: tokens.textSecondary, lineHeight: 1.65, whiteSpace: 'pre-line' }}>
                {summary}
              </Typography>
            </Box>
          )}

          <Divider sx={{ borderColor: 'rgba(255,255,255,0.10)', my: 0.25 }} />
          <Typography variant="caption" sx={{ color: tokens.textTertiary }}>
            {kind ? `${kind} · ` : ''}Updated {updatedAt || 'recently'}{source ? ` · Source ${source}` : ''}
          </Typography>
        </Stack>
      </CardContent>
    </Card>
  )
}
