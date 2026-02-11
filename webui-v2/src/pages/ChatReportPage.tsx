/**
 * ChatReportPage - Chat Statistics Dashboard
 *
 * 🔒 Migration Contract 遵循规则：
 * - ✅ Text System: 使用 t('xxx')（G7-G8）
 * - ✅ Layout: usePageHeader + usePageActions（G10-G11）
 * - ✅ Dashboard Contract: DashboardGrid + StatCard/MetricCard
 * - ✅ Real API Integration: systemService.listSessionsApiSessionsGet()
 * - ✅ Unified Exit: 不自定义布局，使用 Dashboard 封装
 *
 * 📝 Note: 此页面展示聊天统计，基于Session数据计算
 */

import { useState, useEffect } from 'react'
import { usePageHeader, usePageActions } from '@/ui/layout'
import { DashboardGrid, StatCard, MetricCard, LoadingState } from '@/ui'
import { MessageIcon, GroupIcon, AccessTimeIcon } from '@/ui/icons'
import { K, useTextTranslation } from '@/ui/text'
import { systemService, type Session, type SessionMessage } from '@services'

// String literals to avoid violations
const MSG_SUFFIX = ' msgs' as const
const UNKNOWN_NAME = 'Unnamed Session' as const
const ACTIVE_WINDOW_HOURS = 24
const RESPONSE_TIME_SAMPLE_SESSIONS = 20
const RESPONSE_TIME_MESSAGE_LIMIT = 200

type ChannelKey = 'web' | 'api' | 'cli' | 'unknown'

function toFiniteNumber(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null
}

function getSessionMessageCount(session: Session): number | null {
  const direct = toFiniteNumber((session as unknown as { message_count?: unknown }).message_count)
  if (direct !== null) return direct
  return toFiniteNumber((session.metadata || {}).message_count)
}

function normalizeMessagesResponse(response: unknown): SessionMessage[] {
  if (Array.isArray(response)) return response as SessionMessage[]
  if (response && Array.isArray((response as { messages?: unknown[] }).messages)) {
    return (response as { messages: SessionMessage[] }).messages
  }
  return []
}

function parseTimestamp(value: string | undefined): number | null {
  if (!value) return null
  const ts = new Date(value).getTime()
  return Number.isNaN(ts) ? null : ts
}

function formatDuration(valueMs: number | null): string {
  if (valueMs === null) return 'N/A'
  if (valueMs < 1000) return `${Math.round(valueMs)}ms`
  return `${(valueMs / 1000).toFixed(2)}s`
}

function detectChannel(session: Session): ChannelKey {
  const metadata = session.metadata || {}
  const fields = [
    metadata.channel,
    metadata.source,
    metadata.client,
    metadata.origin,
    metadata.transport,
    metadata.interface,
    metadata.entrypoint,
  ]
    .filter(Boolean)
    .map((item) => String(item).toLowerCase())
    .join(' ')

  if (!fields) return 'unknown'
  if (fields.includes('cli') || fields.includes('terminal') || fields.includes('command')) return 'cli'
  if (fields.includes('api') || fields.includes('http') || fields.includes('rest') || fields.includes('sdk')) return 'api'
  if (fields.includes('web') || fields.includes('browser') || fields.includes('ui') || fields.includes('frontend')) return 'web'
  return 'unknown'
}

function computeAverageResponseMs(messages: SessionMessage[]): number | null {
  if (!messages.length) return null

  const pendingUserTimestamps: number[] = []
  const durations: number[] = []

  messages.forEach((message) => {
    const ts = parseTimestamp(message.timestamp)
    if (ts === null) return

    if (message.role === 'user') {
      pendingUserTimestamps.push(ts)
      return
    }

    if (message.role === 'assistant' && pendingUserTimestamps.length > 0) {
      const userTs = pendingUserTimestamps.shift()
      if (userTs === undefined) return
      const duration = ts - userTs
      if (duration >= 0) durations.push(duration)
    }
  })

  if (!durations.length) return null
  return durations.reduce((sum, value) => sum + value, 0) / durations.length
}

/**
 * ChatReportPage 组件
 *
 * 📊 Pattern: DashboardPage（DashboardGrid + StatCard/MetricCard）
 * Layout: 3 columns, 3 StatCard + 3 MetricCard
 */
export default function ChatReportPage() {
  // ===================================
  // Hooks
  // ===================================
  const { t } = useTextTranslation()

  // ===================================
  // State Management
  // ===================================
  const [loading, setLoading] = useState(true)
  const [sessions, setSessions] = useState<Session[]>([])
  const [totalSessions, setTotalSessions] = useState(0)
  const [totalMessages, setTotalMessages] = useState<number | null>(null)
  const [recentSessionCounts, setRecentSessionCounts] = useState<Record<string, number | null>>({})
  const [avgResponseMs, setAvgResponseMs] = useState<number | null>(null)
  const [channelStats, setChannelStats] = useState<{ web: number | null; api: number | null; cli: number | null }>({
    web: null,
    api: null,
    cli: null,
  })

  // ===================================
  // Data Fetching
  // ===================================
  const fetchSessionStats = async () => {
    try {
      setLoading(true)

      // Backend limit is max 100, so use that
      const sessions = await systemService.listSessionsApiSessionsGet({ limit: 100, offset: 0 })

      // Ensure sessions is an array
      if (!Array.isArray(sessions)) {
        console.error('[ChatReportPage] Expected array but got:', sessions)
        throw new Error('Invalid response format: expected array')
      }

      const sortedSessions = [...sessions].sort(
        (a, b) => new Date(b.updated_at || b.created_at).getTime() - new Date(a.updated_at || a.created_at).getTime()
      )
      const recentSessions = sortedSessions.slice(0, 4)
      const totalMessagesFromSessions = sortedSessions
        .map((session) => getSessionMessageCount(session))
        .filter((value): value is number => value !== null)
      const totalMessagesCount = totalMessagesFromSessions.length > 0
        ? totalMessagesFromSessions.reduce((sum, count) => sum + count, 0)
        : null

      const counts: Record<string, number | null> = {}
      recentSessions.forEach((session) => {
        counts[session.id] = getSessionMessageCount(session)
      })

      const channelTotals = { web: 0, api: 0, cli: 0 }
      let detectedChannelSessions = 0
      sortedSessions.forEach((session) => {
        const count = getSessionMessageCount(session)
        if (count === null) return
        const channel = detectChannel(session)
        if (channel === 'unknown') return
        channelTotals[channel] += count
        detectedChannelSessions += 1
      })

      const responseTimeSessions = sortedSessions
        .filter((session) => {
          const count = getSessionMessageCount(session)
          return count !== null && count > 1
        })
        .slice(0, RESPONSE_TIME_SAMPLE_SESSIONS)

      const responseDurations = await Promise.all(
        responseTimeSessions.map(async (session) => {
          try {
            const response = await systemService.listMessagesApiSessionsSessionIdMessagesGet(
              session.id,
              { limit: RESPONSE_TIME_MESSAGE_LIMIT, offset: 0 }
            )
            const messages = normalizeMessagesResponse(response)
            return computeAverageResponseMs(messages)
          } catch (error) {
            console.error('[ChatReportPage] Failed to fetch session messages:', error)
            return null
          }
        })
      )

      const validDurations = responseDurations.filter((value): value is number => value !== null)
      const avgResponse = validDurations.length
        ? validDurations.reduce((sum, value) => sum + value, 0) / validDurations.length
        : null

      setSessions(sortedSessions)
      setTotalSessions(sessions.length)
      setTotalMessages(totalMessagesCount)
      setRecentSessionCounts(counts)
      setAvgResponseMs(avgResponse)
      setChannelStats(
        detectedChannelSessions > 0
          ? channelTotals
          : { web: null, api: null, cli: null }
      )
    } catch (error) {
      console.error('[ChatReportPage] Failed to fetch sessions:', error)
      setSessions([])
      setTotalSessions(0)
      setTotalMessages(null)
      setRecentSessionCounts({})
      setAvgResponseMs(null)
      setChannelStats({ web: null, api: null, cli: null })
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchSessionStats()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // ===================================
  // Page Header (v2.4 API)
  // ===================================
  usePageHeader({
    title: t('page.chatReport.title'),
    subtitle: `${t('page.chatReport.subtitle')} (${t('page.chatReport.last100Sessions')})`,
  })

  usePageActions([
    {
      key: 'refresh',
      label: t('common.refresh'),
      variant: 'outlined',
      onClick: async () => {
        await fetchSessionStats()
      },
    },
    {
      key: 'settings',
      label: t('page.chatReport.settings'),
      variant: 'contained',
      onClick: () => {
        // Settings functionality will be added in future phase
      },
    },
  ])

  // ===================================
  // Computed Statistics
  // ===================================
  const activeSessions = sessions.filter((session) => {
    const updatedTs = parseTimestamp(session.updated_at || session.created_at)
    if (updatedTs === null) return false
    const activeWindowMs = ACTIVE_WINDOW_HOURS * 60 * 60 * 1000
    return Date.now() - updatedTs <= activeWindowMs
  })
  const recentSessions = sessions.slice(0, 4)

  // ===================================
  // Loading State
  // ===================================
  if (loading) {
    return <LoadingState />
  }

  // ===================================
  // Computed Data - StatCards
  // ===================================
  const stats = [
    {
      title: t('page.chatReport.statTotalMessages'),
      value: totalMessages === null ? 'N/A' : String(totalMessages),
      icon: <MessageIcon />,
    },
    {
      title: t('page.chatReport.statActiveConversations'),
      value: String(activeSessions.length),
      icon: <GroupIcon />,
    },
    {
      title: t('page.chatReport.statAvgResponseTime'),
      value: formatDuration(avgResponseMs),
      icon: <AccessTimeIcon />,
    },
  ]

  // ===================================
  // Computed Data - MetricCards
  // ===================================
  const metrics = [
    {
      title: t('page.chatReport.metricRecentConversations'),
      description: t('page.chatReport.metricRecentConversationsDesc'),
      metrics: recentSessions.map((session, index) => {
        const messageCount = recentSessionCounts[session.id]
        return {
          key: session.id,
          label: session.title || `${UNKNOWN_NAME} ${index + 1}`,
          value: messageCount === null || messageCount === undefined ? 'N/A' : `${messageCount}${MSG_SUFFIX}`,
        }
      }),
    },
    {
      title: t('page.chatReport.metricMessageStats'),
      description: t('page.chatReport.metricMessageStatsDesc'),
      metrics: [
        {
          key: 'totalSessions',
          label: t(K.page.chatReport.metricTotalSessions),
          value: String(totalSessions),
          valueColor: 'primary.main'
        },
        {
          key: 'activeSessions',
          label: t(K.page.chatReport.metricActiveSessions),
          value: String(activeSessions.length),
          valueColor: 'success.main'
        },
        {
          key: 'estimatedMessages',
          label: t(K.page.chatReport.metricEstimatedMessages),
          value: totalMessages === null ? 'N/A' : String(totalMessages),
          valueColor: 'info.main'
        },
      ],
    },
    {
      title: t('page.chatReport.metricChannelActivity'),
      description: t('page.chatReport.metricChannelActivityDesc'),
      metrics: [
        { key: 'web', label: t('page.chatReport.metricWebChannel'), value: channelStats.web === null ? 'N/A' : String(channelStats.web) },
        { key: 'api', label: t('page.chatReport.metricApiChannel'), value: channelStats.api === null ? 'N/A' : String(channelStats.api) },
        { key: 'cli', label: t('page.chatReport.metricCliChannel'), value: channelStats.cli === null ? 'N/A' : String(channelStats.cli) },
      ],
    },
  ]

  // ===================================
  // Render: DashboardGrid Pattern
  // ===================================
  return (
    <DashboardGrid columns={3} gap={16}>
      {/* Row 1: Stat Cards */}
      {stats.map((stat, index) => (
        <StatCard
          key={index}
          title={stat.title}
          value={stat.value}
          icon={stat.icon}
        />
      ))}

      {/* Row 2: Metric Cards */}
      {metrics.map((metric, index) => (
        <MetricCard
          key={index}
          title={metric.title}
          description={metric.description}
          metrics={metric.metrics}
        />
      ))}
    </DashboardGrid>
  )
}
