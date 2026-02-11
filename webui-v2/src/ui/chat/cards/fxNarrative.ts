/**
 * FX narrative hard constraints:
 * - Describe only observed historical window data.
 * - No prediction/advice/sentiment words.
 * - All statements must be directly derivable from samples.
 */

export type FxSample = { ts: number; rate: number }

export type FxTrendShape = 'upThenDown' | 'downThenUp' | 'mostlyUp' | 'mostlyDown' | 'flat-ish'

export type FxWindowStats = {
  samples: FxSample[]
  windowMs: number
  count: number
  first: number | null
  last: number | null
  minRate: number | null
  minTs: number | null
  maxRate: number | null
  maxTs: number | null
  range: number | null
  rangePct: number | null
  changeAbs: number | null
  changePct: number | null
  position: number | null
  positionBand: 'low' | 'mid' | 'high' | null
  trendShape: FxTrendShape
  updatedAtTs: number | null
}

const PROHIBITED_TERMS = [
  '将会', '预计', '可能', '大概率', '建议', '买', '卖', '止损', '目标',
  '风险', '利好', '利空', '看涨', '看跌',
]

function toFiniteNumber(value: unknown): number | null {
  const n = Number(value)
  return Number.isFinite(n) ? n : null
}

function formatWindow(windowMs: number): string {
  const mins = Math.max(1, Math.round(windowMs / 60000))
  if (mins < 60) return `${mins} 分钟`
  const hours = Math.floor(mins / 60)
  const remain = mins % 60
  return remain ? `${hours} 小时 ${remain} 分钟` : `${hours} 小时`
}

function inferTrendShape(samples: FxSample[], changePct: number | null, rangePct: number | null): FxTrendShape {
  if (samples.length < 3) {
    if (changePct === null || Math.abs(changePct) < 0.005) return 'flat-ish'
    return changePct > 0 ? 'mostlyUp' : 'mostlyDown'
  }

  if ((changePct !== null && Math.abs(changePct) < 0.005) || (rangePct !== null && rangePct < 0.01)) {
    return 'flat-ish'
  }

  let iMax = 0
  let iMin = 0
  for (let i = 1; i < samples.length; i += 1) {
    if (samples[i].rate > samples[iMax].rate) iMax = i
    if (samples[i].rate < samples[iMin].rate) iMin = i
  }

  const edgeMax = iMax === 0 || iMax === samples.length - 1
  const edgeMin = iMin === 0 || iMin === samples.length - 1
  if (!edgeMax && !edgeMin) {
    if (iMax < iMin) return 'upThenDown'
    if (iMin < iMax) return 'downThenUp'
  }

  if (changePct === null || Math.abs(changePct) < 0.005) return 'flat-ish'
  return changePct > 0 ? 'mostlyUp' : 'mostlyDown'
}

function formatRate(value: number | null): string {
  if (value === null) return '--'
  return value.toFixed(6)
}

function formatAbs(value: number | null): string {
  if (value === null) return '--'
  return value.toFixed(6)
}

function formatPct(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return '--'
  return `${value.toFixed(5)}%`
}

function formatUpdatedAt(ts: number | null): string {
  if (ts === null || !Number.isFinite(ts)) return '--'
  try {
    return new Date(ts).toLocaleString()
  } catch {
    return '--'
  }
}

export function computeFxWindowStats(rawSamples: FxSample[], windowMs: number): FxWindowStats {
  const samples = rawSamples
    .map((item) => ({ ts: toFiniteNumber(item.ts), rate: toFiniteNumber(item.rate) }))
    .filter((item): item is { ts: number; rate: number } => item.ts !== null && item.rate !== null)
    .sort((a, b) => a.ts - b.ts)

  const count = samples.length
  const first = count > 0 ? samples[0].rate : null
  const last = count > 0 ? samples[count - 1].rate : null
  const updatedAtTs = count > 0 ? samples[count - 1].ts : null

  if (count === 0) {
    return {
      samples: [],
      windowMs,
      count,
      first: null,
      last: null,
      minRate: null,
      minTs: null,
      maxRate: null,
      maxTs: null,
      range: null,
      rangePct: null,
      changeAbs: null,
      changePct: null,
      position: null,
      positionBand: null,
      trendShape: 'flat-ish',
      updatedAtTs,
    }
  }

  let minIndex = 0
  let maxIndex = 0
  for (let i = 1; i < count; i += 1) {
    if (samples[i].rate < samples[minIndex].rate) minIndex = i
    if (samples[i].rate > samples[maxIndex].rate) maxIndex = i
  }
  const minRate = samples[minIndex].rate
  const maxRate = samples[maxIndex].rate
  const range = maxRate - minRate
  const changeAbs = first === null || last === null ? null : last - first
  const changePct = first === null || first === 0 || changeAbs === null ? null : (changeAbs / first) * 100
  const rangePct = first === null || first === 0 ? null : (range / first) * 100
  const position = range === 0 || last === null ? null : (last - minRate) / range
  const positionBand = position === null ? null : (position < 0.33 ? 'low' : (position > 0.67 ? 'high' : 'mid'))
  const trendShape = inferTrendShape(samples, changePct, rangePct)

  return {
    samples,
    windowMs,
    count,
    first,
    last,
    minRate,
    minTs: samples[minIndex].ts,
    maxRate,
    maxTs: samples[maxIndex].ts,
    range,
    rangePct,
    changeAbs,
    changePct,
    position,
    positionBand,
    trendShape,
    updatedAtTs,
  }
}

export function buildFxNarrative(stats: FxWindowStats, pairLabel: string): string {
  const windowLabel = formatWindow(stats.windowMs)
  if (stats.count < 2) {
    return `样本不足，当前仅显示最新汇率 ${formatRate(stats.last)}，无法生成窗口解读。`
  }
  if ((stats.range ?? 0) === 0) {
    return `过去 ${windowLabel} 内未观察到可见波动（min=max=${formatRate(stats.last)}）。`
  }

  const sentence1 = `过去 ${windowLabel} 内，${pairLabel} 在 ${formatRate(stats.minRate)}–${formatRate(stats.maxRate)} 区间内波动。`
  const sentence2 = `区间振幅 ${formatAbs(stats.range)}（约 ${formatPct(stats.rangePct)}）；窗口首尾变化 ${formatAbs(stats.changeAbs)}（约 ${formatPct(stats.changePct)}）。`

  let shapeText = '走势整体接近横向波动'
  if (stats.trendShape === 'upThenDown') shapeText = '走势上先上行后回落'
  if (stats.trendShape === 'downThenUp') shapeText = '走势上先回落后上行'
  if (stats.trendShape === 'mostlyUp') shapeText = '走势整体偏上行'
  if (stats.trendShape === 'mostlyDown') shapeText = '走势整体偏下行'
  if (stats.trendShape === 'flat-ish') shapeText = '走势整体接近持平'

  const bandLabel = stats.positionBand === 'low' ? '低位' : stats.positionBand === 'high' ? '高位' : '中部'
  const sentence3 = `${shapeText}；当前值 ${formatRate(stats.last)} 更接近区间${bandLabel}。`
  const sentence4 = `样本数 ${stats.count}；更新于 ${formatUpdatedAt(stats.updatedAtTs)}。`
  return `${sentence1}${sentence2}${sentence3}${sentence4}`
}

export function buildFxNumericSummary(stats: FxWindowStats, pairLabel: string): string {
  if (stats.count < 2) {
    return `样本数 ${stats.count}；最新 ${pairLabel} ${formatRate(stats.last)}。`
  }
  return `样本数 ${stats.count}；区间 ${formatRate(stats.minRate)}–${formatRate(stats.maxRate)}；首尾变化 ${formatAbs(stats.changeAbs)}（${formatPct(stats.changePct)}）。`
}

export function fxNarrativeLint(text: string): { ok: boolean; hits: string[] } {
  const hits = PROHIBITED_TERMS.filter((term) => text.includes(term))
  return { ok: hits.length === 0, hits }
}

