import AccessTimeIcon from '@mui/icons-material/AccessTime'
import AirIcon from '@mui/icons-material/Air'
import OpacityIcon from '@mui/icons-material/Opacity'
import ThermostatIcon from '@mui/icons-material/Thermostat'
import {
  Box,
  Card,
  CardContent,
  Chip,
  Divider,
  Popover,
  Stack,
  Typography,
} from '@mui/material'
import { useMemo, useRef, useState } from 'react'
import { MiniTempChart } from './MiniTempChart'
import { CardExportActions } from './CardExportActions'

type DayForecast = {
  date?: string
  condition?: string
  high_c?: number
  low_c?: number
}

type HourPoint = {
  time?: string
  temp_c?: number
}

type WeatherCardProps = {
  location?: string
  summary?: string
  condition?: string
  tempC?: number
  highC?: number
  lowC?: number
  windKmh?: number
  humidityPct?: number
  daily?: DayForecast[]
  hourly?: HourPoint[]
  updatedAt?: string
  source?: string
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

function compactUpdatedLabel(updatedAt?: string): string {
  if (!updatedAt) return 'Updated recently'
  const ts = new Date(updatedAt).getTime()
  if (Number.isNaN(ts)) return 'Updated recently'
  const diffMins = Math.max(1, Math.round((Date.now() - ts) / 60000))
  if (diffMins < 60) return `Updated ${diffMins}m ago`
  const diffHours = Math.round(diffMins / 60)
  return `Updated ${diffHours}h ago`
}

function formatShortDay(value?: string, fallback = 'Day'): string {
  if (!value) return fallback
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return value.slice(0, 3)
  return parsed.toLocaleDateString('en-US', { weekday: 'short' })
}

function formatHourTick(value?: string): string {
  if (!value) return '--'
  const digits = value.replace(/\D/g, '')
  if (digits.length >= 4) {
    return `${digits.slice(0, 2)}:${digits.slice(2, 4)}`
  }
  if (digits.length === 2) {
    return `${digits}:00`
  }
  return value
}

export function WeatherCard({
  location,
  summary,
  condition,
  tempC,
  highC,
  lowC,
  windKmh,
  humidityPct,
  daily = [],
  hourly = [],
  updatedAt,
  source,
}: WeatherCardProps) {
  const cardRef = useRef<HTMLDivElement>(null)
  const [activeDay, setActiveDay] = useState(0)
  const [anchorEl, setAnchorEl] = useState<HTMLElement | null>(null)

  const topDays = useMemo(() => daily.slice(0, 3), [daily])
  const selectedDay = topDays[activeDay] || topDays[0]
  const selectedHigh = selectedDay?.high_c ?? highC
  const selectedLow = selectedDay?.low_c ?? lowC

  const chartPoints = useMemo(
    () =>
      hourly
        .filter((point): point is Required<HourPoint> => Number.isFinite(point.temp_c))
        .map((point) => ({ t: formatHourTick(point.time), temp: Number(point.temp_c) })),
    [hourly]
  )
  const exportRows = useMemo(
    () => chartPoints.map((p) => ({ time: p.t, value: p.temp })),
    [chartPoints]
  )

  const temperatureLabel = Number.isFinite(tempC)
    ? `${Math.round(Number(tempC))}°`
    : ''
  const temperatureUnit = Number.isFinite(tempC) ? 'C' : ''
  const headerSubtitle = condition || summary || 'Weather'

  return (
    <Card
      ref={cardRef}
      data-testid="chat-weather-card"
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
                {location || 'Unknown location'}
              </Typography>
              <Typography variant="body2" sx={{ color: tokens.textSecondary, mt: 0.35 }}>
                {headerSubtitle}
              </Typography>
            </Box>
            <Stack direction="row" alignItems="center" spacing={0.75} sx={{ flexShrink: 0 }}>
              <CardExportActions
                targetRef={cardRef}
                fileBaseName={`weather-${location || 'location'}`}
                tableData={{ columns: ['time', 'value'], rows: exportRows }}
              />
              <Chip
                size="small"
                icon={<AccessTimeIcon sx={{ fontSize: 14 }} />}
                label={compactUpdatedLabel(updatedAt)}
                sx={{ bgcolor: tokens.surface, color: tokens.textSecondary, height: 24 }}
                onClick={(event) => setAnchorEl(event.currentTarget)}
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

          <Stack
            direction={{ xs: 'column', sm: 'row' }}
            spacing={2}
            alignItems={{ xs: 'flex-start', sm: 'stretch' }}
            justifyContent="space-between"
          >
            <Box sx={{ minWidth: { sm: 180 } }}>
              {temperatureLabel ? (
                <Stack direction="row" alignItems="flex-end" spacing={0.75}>
                  <Typography sx={{ fontSize: { xs: 46, sm: 54 }, fontWeight: 800, lineHeight: 1 }}>
                    {temperatureLabel}
                  </Typography>
                  <Typography sx={{ fontSize: 18, color: tokens.textSecondary, pb: 0.8 }}>
                    °{temperatureUnit}
                  </Typography>
                </Stack>
              ) : (
                <Typography variant="body2" sx={{ color: tokens.textSecondary }}>
                  Current temperature unavailable
                </Typography>
              )}
            </Box>

            <Stack
              direction="row"
              spacing={1.25}
              flexWrap="wrap"
              useFlexGap
              sx={{ alignContent: 'flex-start' }}
            >
              {(Number.isFinite(selectedHigh) || Number.isFinite(selectedLow)) && (
                <Chip
                  icon={<ThermostatIcon sx={{ fontSize: 15 }} />}
                  label={`H ${selectedHigh ?? '--'}° · L ${selectedLow ?? '--'}°`}
                  sx={{ bgcolor: tokens.surface, color: tokens.textPrimary, borderRadius: 2 }}
                />
              )}
              {Number.isFinite(windKmh) && (
                <Chip
                  icon={<AirIcon sx={{ fontSize: 15 }} />}
                  label={`Wind ${windKmh} km/h`}
                  sx={{ bgcolor: tokens.surface, color: tokens.textPrimary, borderRadius: 2 }}
                />
              )}
              {Number.isFinite(humidityPct) && (
                <Chip
                  icon={<OpacityIcon sx={{ fontSize: 15 }} />}
                  label={`Humidity ${humidityPct}%`}
                  sx={{ bgcolor: tokens.surface, color: tokens.textPrimary, borderRadius: 2 }}
                />
              )}
            </Stack>
          </Stack>

          {topDays.length > 0 && (
            <Stack direction="row" spacing={1} sx={{ overflowX: 'auto', pb: 0.25 }}>
              {topDays.map((day, index) => {
                const selected = index === activeDay
                return (
                  <Box
                    key={`${day.date || index}`}
                    onClick={() => setActiveDay(index)}
                    sx={{
                      minWidth: 112,
                      px: 1.25,
                      py: 1,
                      borderRadius: 2,
                      bgcolor: selected ? tokens.surface2 : tokens.surface,
                      cursor: 'pointer',
                      transition: 'background-color 120ms ease',
                    }}
                  >
                    <Typography variant="caption" sx={{ color: tokens.textSecondary, fontWeight: 600 }}>
                      {formatShortDay(day.date, `D${index + 1}`)}
                    </Typography>
                    <Typography variant="body2" sx={{ fontWeight: 700, mt: 0.35 }}>
                      {day.high_c ?? '--'}° / {day.low_c ?? '--'}°
                    </Typography>
                    <Typography
                      variant="caption"
                      sx={{
                        color: tokens.textTertiary,
                        mt: 0.3,
                        display: '-webkit-box',
                        WebkitBoxOrient: 'vertical',
                        WebkitLineClamp: 1,
                        overflow: 'hidden',
                      }}
                    >
                      {day.condition || '—'}
                    </Typography>
                  </Box>
                )
              })}
            </Stack>
          )}

          {chartPoints.length > 1 && (
            <>
              <Divider sx={{ borderColor: 'rgba(255,255,255,0.10)' }} />
              <MiniTempChart points={chartPoints} />
            </>
          )}

          <Typography variant="caption" sx={{ color: tokens.textTertiary }}>
            Updated {updatedAt || 'recently'}{source ? ` · Source ${source}` : ''}
          </Typography>
        </Stack>
      </CardContent>

      <Popover
        open={Boolean(anchorEl)}
        anchorEl={anchorEl}
        onClose={() => setAnchorEl(null)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'left' }}
      >
        <Box sx={{ p: 1.25 }}>
          <Typography variant="caption">{updatedAt || 'No timestamp provided'}</Typography>
        </Box>
      </Popover>
    </Card>
  )
}
