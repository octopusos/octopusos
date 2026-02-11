/**
 * LogsPage - 系统日志页面
 *
 * 🔒 Migration Contract 遵循规则：
 * - ✅ Text System: 使用 t('xxx')（G7-G8）
 * - ✅ Layout: usePageHeader + usePageActions（G10-G11）
 * - ✅ Table Contract: TableShell 三行结构
 * - ✅ Phase 3 Integration: 添加 DetailDrawer (无删除)
 * - ✅ Unified Exit: TableShell 封装
 *
 * ⚠️ 待补充 i18n keys:
 * - page.logs.*
 * - form.field.level
 */

import { useEffect, useState } from 'react'
import { TextField, Select, MenuItem, Box, Typography, Chip } from '@mui/material'
import { usePageHeader, usePageActions } from '@/ui/layout'
import { TableShell, FilterBar } from '@/ui'
import { K, useTextTranslation } from '@/ui/text'
import { DetailDrawer } from '@/ui/interaction'
import { httpClient } from '@platform/http'
import type { GridColDef } from '@/ui'

// ===================================
// Types
// ===================================

interface LogRow {
  id: number
  timestamp: string
  level: string
  source: string
  message: string
  duration: string
}

type RawLogRecord = Record<string, unknown>

/**
 * LogsPage 组件
 *
 * 📊 Pattern: TablePage（FilterBar + Table + Pagination）
 */
export default function LogsPage() {
  // ===================================
  // i18n Hook - Subscribe to language changes
  // ===================================
  const { t } = useTextTranslation()

  // ===================================
  // State (Filter - 迁移阶段不触发过滤)
  // ===================================
  const [searchQuery, setSearchQuery] = useState('')
  const [levelFilter, setLevelFilter] = useState('all')
  const [sourceFilter, setSourceFilter] = useState('all')
  const [logs, setLogs] = useState<LogRow[]>([])
  const [loading, setLoading] = useState(true)

  // ===================================
  // Phase 3 Integration - Interaction State
  // ===================================
  const [selectedLog, setSelectedLog] = useState<LogRow | null>(null)
  const [drawerOpen, setDrawerOpen] = useState(false)

  const FALLBACK_TIMESTAMP = 'N/A'

  const extractTimestamp = (line: string): string | null => {
    const patterns = [
      /^(\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?(?:Z|[+-]\d{2}:\d{2})?)/,
      /(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}(?:[.,]\d+)?)/,
      /(\d{2}\/[A-Za-z]{3}\/\d{4}[:\s]\d{2}:\d{2}:\d{2})/,
    ]
    for (const pattern of patterns) {
      const match = line.match(pattern)
      if (match?.[1]) return match[1]
    }
    return null
  }

  const normalizeLogRow = (entry: RawLogRecord, index: number): LogRow => {
    const messageCandidate = entry.message ?? entry.msg ?? entry.content ?? entry.text
    const message = typeof messageCandidate === 'string' ? messageCandidate : JSON.stringify(entry)

    const levelCandidate = entry.level ?? entry.severity
    const level = typeof levelCandidate === 'string' ? levelCandidate.toUpperCase() : 'INFO'

    const sourceCandidate = entry.source ?? entry.logger ?? entry.module ?? entry.component
    const source = typeof sourceCandidate === 'string' ? sourceCandidate : 'daemon'

    const durationCandidate = entry.duration ?? entry.duration_ms ?? entry.elapsed_ms
    const duration =
      typeof durationCandidate === 'number'
        ? `${durationCandidate}ms`
        : typeof durationCandidate === 'string'
        ? durationCandidate
        : '-'

    const timestampCandidate =
      entry.timestamp ?? entry.ts ?? entry.time ?? entry.created_at ?? entry.createdAt
    const timestampFromField =
      typeof timestampCandidate === 'string' && timestampCandidate.trim() ? timestampCandidate : null
    const timestamp = timestampFromField ?? extractTimestamp(message) ?? FALLBACK_TIMESTAMP

    const idCandidate = entry.id
    const id = typeof idCandidate === 'number' ? idCandidate : index + 1

    return {
      id,
      timestamp,
      level,
      source,
      message,
      duration,
    }
  }

  const parseDaemonLine = (line: string, index: number): LogRow => {
    const levelMatch = line.match(/\b(ERROR|WARN|WARNING|INFO|DEBUG|TRACE)\b/i)
    const normalizedLevel = (levelMatch?.[1] || 'INFO').toUpperCase()
    const level = normalizedLevel === 'WARNING' ? 'WARN' : normalizedLevel
    const timestamp = extractTimestamp(line) ?? FALLBACK_TIMESTAMP
    const sourceMatch = line.match(/\[([a-zA-Z0-9_.:-]+)\]/)

    return {
      id: index + 1,
      timestamp,
      level,
      source: sourceMatch?.[1] || 'daemon',
      message: line,
      duration: '-',
    }
  }

  const loadLogs = async () => {
    setLoading(true)
    try {
      const response = await httpClient.get<any>('/api/daemon/logs', {
        params: { lines: 200 },
      })
      const payload = response?.data ?? response

      if (Array.isArray(payload)) {
        setLogs(payload.map((entry, index) => normalizeLogRow(entry as RawLogRecord, index)))
        return
      }

      if (Array.isArray(payload?.logs)) {
        setLogs(payload.logs.map((entry: unknown, index: number) => normalizeLogRow(entry as RawLogRecord, index)))
        return
      }

      const rawContent = typeof payload?.content === 'string' ? payload.content : ''
      const records = rawContent
        .split('\n')
        .map((line: string) => line.trim())
        .filter(Boolean)
        .map(parseDaemonLine)
      setLogs(records)
    } catch {
      setLogs([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadLogs()
  }, [])

  // ===================================
  // Page Header (v2.4 API)
  // ===================================
  usePageHeader({
    title: t(K.page.logs.title),
    subtitle: t(K.page.logs.subtitle),
  })

  usePageActions([
    {
      key: 'export',
      label: t(K.common.download),
      variant: 'outlined',
      onClick: async () => {
        // API skeleton for export
        // await logsService.exportLogs()  // Placeholder for Phase 6.1
        console.log('Export logs (API not implemented)')
      },
    },
    {
      key: 'refresh',
      label: t(K.common.refresh),
      variant: 'contained',
      onClick: async () => loadLogs(),
    },
  ])

  // ===================================
  // Phase 3 Integration - Handlers
  // ===================================
  const handleRowClick = (row: LogRow) => {
    setSelectedLog(row)
    setDrawerOpen(true)
  }

  // ===================================
  // Table Columns Definition
  // ===================================
  const columns: GridColDef[] = [
    {
      field: 'id',
      headerName: t(K.page.logs.columnId),
      width: 70,
    },
    {
      field: 'timestamp',
      headerName: t(K.page.logs.columnTimestamp),
      width: 180,
    },
    {
      field: 'level',
      headerName: t(K.page.logs.columnLevel),
      width: 100,
    },
    {
      field: 'source',
      headerName: t(K.page.logs.columnSource),
      flex: 1,
      minWidth: 200,
    },
    {
      field: 'message',
      headerName: t(K.page.logs.columnMessage),
      flex: 2,
      minWidth: 300,
    },
    {
      field: 'duration',
      headerName: t(K.page.logs.columnDuration),
      width: 100,
    },
  ]

  // ===================================
  // Render: TableShell Pattern + Phase 3 Interactions
  // ===================================
  return (
    <>
      <TableShell
      loading={loading}
      rows={logs}
      columns={columns}
      filterBar={
        <FilterBar
          filters={[
            {
              width: 6,
              component: (
                <TextField
                  label={t(K.common.search)}
                  placeholder={t(K.page.logs.searchPlaceholder)}
                  fullWidth
                  size="small"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
              ),
            },
            {
              width: 3,
              component: (
                <Select
                  fullWidth
                  size="small"
                  value={levelFilter}
                  onChange={(e) => setLevelFilter(e.target.value)}
                >
                  <MenuItem value="all">{t(K.page.logs.allLevels)}</MenuItem>
                  <MenuItem value="debug">{t(K.page.logs.levelDebug)}</MenuItem>
                  <MenuItem value="info">{t(K.page.logs.levelInfo)}</MenuItem>
                  <MenuItem value="warn">{t(K.page.logs.levelWarn)}</MenuItem>
                  <MenuItem value="error">{t(K.page.logs.levelError)}</MenuItem>
                </Select>
              ),
            },
            {
              width: 3,
              component: (
                <Select
                  fullWidth
                  size="small"
                  value={sourceFilter}
                  onChange={(e) => setSourceFilter(e.target.value)}
                >
                  <MenuItem value="all">{t(K.page.logs.allSources)}</MenuItem>
                  <MenuItem value="core">{t(K.page.logs.sourceCore)}</MenuItem>
                  <MenuItem value="webui">{t(K.page.logs.sourceWebui)}</MenuItem>
                  <MenuItem value="store">{t(K.page.logs.sourceStore)}</MenuItem>
                </Select>
              ),
            },
          ]}
          actions={[
            {
              key: 'reset',
              label: t('common.reset'),
              onClick: () => {
                // 🔒 No-Interaction: 仅重置 state
                setSearchQuery('')
                setLevelFilter('all')
                setSourceFilter('all')
              },
            },
            {
              key: 'apply',
              label: t('common.apply'),
              variant: 'contained',
              onClick: () => {}, // 🔒 No-Interaction: 空函数
            },
          ]}
        />
      }
      emptyState={{
        title: t(K.page.logs.noLogs),
        description: t(K.page.logs.noLogsDesc),
        actions: [
          {
            label: t('common.reset'),
            onClick: () => {
              setSearchQuery('')
              setLevelFilter('all')
              setSourceFilter('all')
            },
            variant: 'contained',
          },
        ],
      }}
      pagination={{
        page: 0,
        pageSize: 25,
        total: logs.length,
        onPageChange: () => {}, // 🔒 No-Interaction: 空函数
      }}
      onRowClick={handleRowClick}
      />

      {/* Detail Drawer - Phase 3 Integration */}
      <DetailDrawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        title={`${t(K.page.logs.logEntry)} #${selectedLog?.id || ''}`}
      >
        {selectedLog && (
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
            {/* Timestamp */}
            <Box>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                {t(K.page.logs.columnTimestamp)}
              </Typography>
              <Typography variant="body1">{selectedLog.timestamp}</Typography>
            </Box>

            {/* Level */}
            <Box>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                {t(K.page.logs.columnLevel)}
              </Typography>
              <Chip
                label={selectedLog.level}
                color={
                  selectedLog.level === 'ERROR'
                    ? 'error'
                    : selectedLog.level === 'WARN'
                    ? 'warning'
                    : selectedLog.level === 'INFO'
                    ? 'success'
                    : 'default'
                }
                size="small"
              />
            </Box>

            {/* Source */}
            <Box>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                {t(K.page.logs.columnSource)}
              </Typography>
              <Typography variant="body1">{selectedLog.source}</Typography>
            </Box>

            {/* Message */}
            <Box>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                {t(K.page.logs.columnMessage)}
              </Typography>
              <Typography variant="body1">{selectedLog.message}</Typography>
            </Box>

            {/* Duration */}
            <Box>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                {t(K.page.logs.columnDuration)}
              </Typography>
              <Typography variant="body1">{selectedLog.duration}</Typography>
            </Box>
          </Box>
        )}
      </DetailDrawer>
    </>
  )
}
