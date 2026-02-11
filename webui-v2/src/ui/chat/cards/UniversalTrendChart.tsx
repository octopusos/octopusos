import { Box } from '@mui/material'
import { useMemo } from 'react'
import {
  CartesianGrid,
  Label,
  Line,
  LineChart,
  ReferenceDot,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

type TrendPoint = {
  time: string
  value: number
}

type UniversalTrendChartProps = {
  points: TrendPoint[]
  engine?: 'ag' | 'mui'
  xAxisLabel?: string
  yAxisLabel?: string
  windowMs?: number
  showExtrema?: boolean
}

function yTickDigits(range: number): number {
  if (range <= 0.0001) return 6
  if (range <= 0.001) return 5
  if (range <= 0.01) return 4
  if (range <= 0.1) return 3
  return 2
}

function formatAxisTime(ts: number, windowMs: number): string {
  const date = new Date(ts)
  if (windowMs <= 5 * 60_000) {
    return date.toLocaleTimeString([], { minute: '2-digit', second: '2-digit' })
  }
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

function toTs(time: string, fallback: number): number {
  const ts = new Date(time).getTime()
  if (Number.isFinite(ts)) return ts
  return fallback
}

export function UniversalTrendChart({
  points,
  engine = 'ag',
  xAxisLabel = '时间',
  yAxisLabel = 'Value',
  windowMs = 5 * 60_000,
  showExtrema = false,
}: UniversalTrendChartProps) {
  const normalized = useMemo(
    () =>
      points
        .filter((p) => Number.isFinite(p.value) && !!p.time)
        .map((p, idx) => {
          const ts = toTs(String(p.time), idx * 1000)
          return { time: String(p.time), value: Number(p.value), ts, timeLabel: formatAxisTime(ts, windowMs) }
        }),
    [points, windowMs]
  )

  if (normalized.length < 2) return null

  const values = normalized.map((p) => p.value)
  const minValue = Math.min(...values)
  const maxValue = Math.max(...values)
  const range = maxValue - minValue
  const pad = Math.max(range * 0.2, 0.000001)
  const yMin = minValue - pad
  const yMax = maxValue + pad
  const digits = yTickDigits(range)

  let maxPoint = normalized[0]
  let minPoint = normalized[0]
  for (const point of normalized) {
    if (point.value > maxPoint.value) maxPoint = point
    if (point.value < minPoint.value) minPoint = point
  }

  const verticalTooClose = Math.abs(maxPoint.value - minPoint.value) <= Math.max(range * 0.1, 0.0000005)
  const maxLabelPosition: 'top' | 'bottom' = verticalTooClose ? 'top' : 'top'
  const minLabelPosition: 'top' | 'bottom' = verticalTooClose ? 'bottom' : 'bottom'
  const labelShort = verticalTooClose
  const strokeColor = engine === 'mui' ? '#90caf9' : '#90caf9'

  return (
    <Box sx={{ width: '100%', height: 180, position: 'relative', overflow: 'hidden', borderRadius: 1.5 }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart
          data={normalized}
          margin={{ left: 8, right: 16, top: 8, bottom: 20 }}
        >
          <CartesianGrid stroke="rgba(255,255,255,0.08)" strokeDasharray="3 3" />
          <XAxis
            dataKey="ts"
            type="number"
            domain={['dataMin', 'dataMax']}
            tickFormatter={(value) => formatAxisTime(Number(value), windowMs)}
            tick={{ fill: 'rgba(255,255,255,0.62)', fontSize: 11 }}
            minTickGap={24}
          >
            <Label value={xAxisLabel} position="insideBottom" offset={-6} fill="rgba(255,255,255,0.7)" />
          </XAxis>
          <YAxis
            domain={[yMin, yMax]}
            tickFormatter={(value) => Number(value).toFixed(digits)}
            tick={{ fill: 'rgba(255,255,255,0.62)', fontSize: 11 }}
            width={76}
          >
            <Label
              value={yAxisLabel}
              angle={-90}
              position="insideLeft"
              style={{ textAnchor: 'middle', fill: 'rgba(255,255,255,0.7)' }}
            />
          </YAxis>
          <Tooltip
            labelFormatter={(value) => formatAxisTime(Number(value), windowMs)}
            formatter={(value: number | string | Array<number | string> | undefined) => [Number(value ?? 0).toFixed(digits), yAxisLabel]}
            contentStyle={{ background: 'rgba(16,18,26,0.96)', border: '1px solid rgba(255,255,255,0.16)' }}
            labelStyle={{ color: 'rgba(255,255,255,0.85)' }}
          />
          <Line
            type="monotone"
            dataKey="value"
            stroke={strokeColor}
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4 }}
            isAnimationActive={false}
          />
          {showExtrema && (
            <>
              <ReferenceDot
                x={maxPoint.ts}
                y={maxPoint.value}
                r={4}
                fill="#ffcc80"
                stroke="#ffcc80"
                label={{
                  value: labelShort ? `H ${maxPoint.value.toFixed(digits)}` : `最高 ${maxPoint.value.toFixed(digits)}`,
                  position: maxLabelPosition,
                  fill: '#ffe0b2',
                  fontSize: 11,
                }}
              />
              <ReferenceDot
                x={minPoint.ts}
                y={minPoint.value}
                r={4}
                fill="#80deea"
                stroke="#80deea"
                label={{
                  value: labelShort ? `L ${minPoint.value.toFixed(digits)}` : `最低 ${minPoint.value.toFixed(digits)}`,
                  position: minLabelPosition,
                  fill: '#b2ebf2',
                  fontSize: 11,
                }}
              />
            </>
          )}
        </LineChart>
      </ResponsiveContainer>
    </Box>
  )
}
