import { Box, Typography } from '@mui/material'
import { useId, useMemo, useState } from 'react'

type TempPoint = {
  t: string
  temp: number
}

type MiniTempChartProps = {
  points: TempPoint[]
}

const CHART_HEIGHT = 72
const CHART_WIDTH = 520
const CHART_PADDING_X = 12
const CHART_PADDING_Y = 8

export function MiniTempChart({ points }: MiniTempChartProps) {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null)
  const gradientId = useId()

  const validPoints = useMemo(
    () => points.filter((point) => Number.isFinite(point.temp)),
    [points]
  )

  if (validPoints.length < 2) {
    return null
  }

  const minTemp = Math.min(...validPoints.map((point) => point.temp))
  const maxTemp = Math.max(...validPoints.map((point) => point.temp))
  const range = Math.max(1, maxTemp - minTemp)
  const innerWidth = CHART_WIDTH - CHART_PADDING_X * 2
  const innerHeight = CHART_HEIGHT - CHART_PADDING_Y * 2

  const chartPoints = validPoints.map((point, index) => {
    const x = CHART_PADDING_X + (innerWidth * index) / (validPoints.length - 1)
    const y =
      CHART_PADDING_Y + innerHeight - ((point.temp - minTemp) / range) * innerHeight
    return { ...point, x, y, index }
  })

  const polyline = chartPoints.map((point) => `${point.x},${point.y}`).join(' ')
  const areaPath = [
    `M ${chartPoints[0].x} ${CHART_HEIGHT - CHART_PADDING_Y}`,
    ...chartPoints.map((point) => `L ${point.x} ${point.y}`),
    `L ${chartPoints[chartPoints.length - 1].x} ${CHART_HEIGHT - CHART_PADDING_Y}`,
    'Z',
  ].join(' ')

  const tickIndexes = [0, Math.floor((chartPoints.length - 1) / 3), Math.floor((chartPoints.length - 1) * 2 / 3), chartPoints.length - 1]

  return (
    <Box>
      <Box sx={{ position: 'relative', width: '100%', height: CHART_HEIGHT }}>
        <svg
          viewBox={`0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`}
          preserveAspectRatio="none"
          width="100%"
          height={CHART_HEIGHT}
        >
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="rgba(96,165,250,0.34)" />
              <stop offset="100%" stopColor="rgba(96,165,250,0.04)" />
            </linearGradient>
          </defs>
          <path d={areaPath} fill={`url(#${gradientId})`} />
          <polyline
            points={polyline}
            fill="none"
            stroke="rgba(191,219,254,0.92)"
            strokeWidth={2}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          {chartPoints.map((point) => (
            <circle
              key={`${point.t}-${point.index}`}
              cx={point.x}
              cy={point.y}
              r={hoveredIndex === point.index ? 3.8 : 2.8}
              fill="rgba(241,245,249,0.98)"
              stroke="rgba(15,23,42,0.8)"
              strokeWidth={1}
              onMouseEnter={() => setHoveredIndex(point.index)}
              onMouseLeave={() => setHoveredIndex(null)}
            />
          ))}
        </svg>
        {hoveredIndex !== null && chartPoints[hoveredIndex] && (
          <Box
            sx={{
              position: 'absolute',
              left: `${(chartPoints[hoveredIndex].x / CHART_WIDTH) * 100}%`,
              top: -30,
              transform: 'translateX(-50%)',
              px: 1,
              py: 0.4,
              borderRadius: 1,
              bgcolor: 'rgba(2,6,23,0.9)',
              border: '1px solid rgba(148,163,184,0.35)',
              pointerEvents: 'none',
            }}
          >
            <Typography variant="caption" sx={{ color: 'rgba(248,250,252,0.95)' }}>
              {chartPoints[hoveredIndex].t} · {chartPoints[hoveredIndex].temp}°
            </Typography>
          </Box>
        )}
      </Box>
      <Box sx={{ mt: 0.5, display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 0.5 }}>
        {tickIndexes.map((index, tickIndex) => {
          const point = chartPoints[index]
          return (
            <Typography
              key={`${point.t}-${tickIndex}`}
              variant="caption"
              sx={{ color: 'rgba(255,255,255,0.55)', textAlign: tickIndex === 0 ? 'left' : tickIndex === 3 ? 'right' : 'center' }}
            >
              {point.t}
            </Typography>
          )
        })}
      </Box>
    </Box>
  )
}
