/**
 * NotificationsPage - 通知管理页面
 *
 * 🔒 Migration Contract 遵循规则：
 * - ✅ Text System: 使用 t('xxx')（G7-G8）
 * - ✅ Layout: usePageHeader + usePageActions（G10-G11）
 * - ✅ Table Contract: TableShell 三行结构
 * - ✅ No Interaction: mock 数据，onClick 空函数（G12-G16）
 * - ✅ Unified Exit: TableShell 封装
 *
 * ⚠️ 待补充 i18n keys:
 * - page.notifications.*
 * - form.field.notificationType
 */

import { useState, useEffect, useMemo } from 'react'
import { TextField, Select, MenuItem, Chip, Dialog, DialogTitle, DialogContent, DialogActions, Button, Box, Typography, Divider } from '@mui/material'
import { usePageHeader, usePageActions } from '@/ui/layout'
import { TableShell, FilterBar } from '@/ui'
import { K, useTextTranslation } from '@/ui/text'
import { toast } from '@/ui/feedback'
import type { GridColDef } from '@/ui'
import { inboxService } from '@/services'

/**
 * NotificationsPage 组件
 *
 * 📊 Pattern: TablePage（FilterBar + Table + Pagination）
 */

interface NotificationRow {
  id: string
  title: string
  message: string
  type: string
  timestamp: string
  read: boolean
  cardId?: string
  inboxItemId?: string
}

export default function NotificationsPage() {
  // ===================================
  // i18n Hook - Subscribe to language changes
  // ===================================
  const { t } = useTextTranslation()

  // ===================================
  // State (Filter - 迁移阶段不触发过滤)
  // ===================================
  const [searchQuery, setSearchQuery] = useState('')
  const [typeFilter, setTypeFilter] = useState('all')
  const [priorityFilter, setPriorityFilter] = useState('all')

  // ===================================
  // Page Header (v2.4 API)
  // ===================================
  // ===================================
  // State Management
  // ===================================
  const [notifications, setNotifications] = useState<NotificationRow[]>([])
  const [loading, setLoading] = useState(true)
  const [detailOpen, setDetailOpen] = useState(false)
  const [detailLoading, setDetailLoading] = useState(false)
  const [detail, setDetail] = useState<any>(null)
  const [selectedRow, setSelectedRow] = useState<NotificationRow | null>(null)

  const loadNotifications = async () => {
    setLoading(true)
    try {
      const response: any = await inboxService.listItems({ status: 'unread', limit: 100 })
      const items = Array.isArray(response?.items) ? response.items : Array.isArray(response?.data?.items) ? response.data.items : []
      const rows: NotificationRow[] = items.map((item: any) => ({
        id: String(item.inbox_item_id),
        title: String(item?.card?.title || item.scope_type || 'inbox'),
        message: String(item?.card?.summary || `card_id=${String(item.card_id)}`),
        type: String(item?.card?.severity || item.delivery_type || 'inbox_only'),
        timestamp: new Date(Number(item.updated_at_ms || item.created_at_ms || Date.now())).toISOString(),
        read: String(item.status) !== 'unread',
        cardId: String(item.card_id),
        inboxItemId: String(item.inbox_item_id),
      }))
      setNotifications(rows)
    } catch (err) {
      console.error('[NotificationsPage] failed to load inbox items', err)
      setNotifications([])
    } finally {
      setLoading(false)
    }
  }

  // ===================================
  // Data Fetching
  // ===================================
  useEffect(() => {
    void loadNotifications()
  }, [])

  usePageHeader({
    title: t(K.page.notifications.title),
    subtitle: t(K.page.notifications.subtitle),
  })

  usePageActions([
    {
      key: 'markAllRead',
      label: t(K.page.notifications.markAllRead),
      variant: 'outlined',
      onClick: () => {
        toast.info(t(K.page.notifications.markAllRead))
      },
    },
    {
      key: 'clear',
      label: t(K.page.notifications.clearAll),
      variant: 'outlined',
      onClick: () => {
        toast.info(t(K.page.notifications.clearAll))
      },
    },
  ])

  // ===================================
  // Table Columns Definition
  // ===================================
  const columns: GridColDef[] = [
    {
      field: 'id',
      headerName: t(K.page.notifications.columnId),
      width: 70,
    },
    {
      field: 'type',
      headerName: t(K.page.notifications.columnType),
      width: 100,
      renderCell: (params) => (
        <Chip
          label={String(params.value || '')}
          size="small"
          variant="outlined"
          color="info"
        />
      ),
    },
    {
      field: 'title',
      headerName: t(K.page.notifications.columnTitle),
      flex: 1,
      minWidth: 200,
    },
    {
      field: 'message',
      headerName: t(K.page.notifications.columnMessage),
      flex: 2,
      minWidth: 300,
    },
    {
      field: 'timestamp',
      headerName: t(K.page.notifications.columnTimestamp),
      width: 180,
    },
    {
      field: 'priority',
      headerName: t('form.field.priority'),
      width: 100,
    },
    {
      field: 'read',
      headerName: t(K.page.notifications.columnRead),
      width: 80,
      renderCell: (params) => (
        <Chip
          label={params.value ? 'read' : 'unread'}
          size="small"
          variant="outlined"
          color={params.value ? 'default' : 'warning'}
        />
      ),
    },
  ]

  const filteredRows = useMemo(() => {
    const q = searchQuery.trim().toLowerCase()
    return notifications.filter((row) => {
      if (typeFilter !== 'all' && row.type !== typeFilter) return false
      if (q && !(row.title.toLowerCase().includes(q) || row.message.toLowerCase().includes(q))) return false
      return true
    })
  }, [notifications, searchQuery, typeFilter])

  // ===================================
  // Render: TableShell Pattern
  // ===================================
  return (
    <>
      <TableShell
        loading={loading}
        rows={filteredRows}
        columns={columns}
        filterBar={
          <FilterBar
            filters={[
              {
                width: 6,
                component: (
                  <TextField
                    label={t(K.common.search)}
                    placeholder={t(K.page.notifications.searchPlaceholder)}
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
                    value={typeFilter}
                    onChange={(e) => setTypeFilter(e.target.value)}
                  >
                    <MenuItem value="all">{t(K.page.notifications.allTypes)}</MenuItem>
                    <MenuItem value="info">info</MenuItem>
                    <MenuItem value="warn">warn</MenuItem>
                    <MenuItem value="high">high</MenuItem>
                    <MenuItem value="critical">critical</MenuItem>
                  </Select>
                ),
              },
              {
                width: 3,
                component: (
                  <Select
                    fullWidth
                    size="small"
                    value={priorityFilter}
                    onChange={(e) => setPriorityFilter(e.target.value)}
                  >
                    <MenuItem value="all">{t(K.page.notifications.allPriority)}</MenuItem>
                    <MenuItem value="critical">{t(K.page.notifications.priorityCritical)}</MenuItem>
                    <MenuItem value="high">{t(K.page.notifications.priorityHigh)}</MenuItem>
                    <MenuItem value="medium">{t(K.page.notifications.priorityMedium)}</MenuItem>
                    <MenuItem value="low">{t(K.page.notifications.priorityLow)}</MenuItem>
                  </Select>
                ),
              },
            ]}
            actions={[
              {
                key: 'reset',
                label: t('common.reset'),
                onClick: () => {
                  setSearchQuery('')
                  setTypeFilter('all')
                  setPriorityFilter('all')
                },
              },
              {
                key: 'apply',
                label: t('common.apply'),
                variant: 'contained',
                onClick: () => {},
              },
            ]}
          />
        }
        emptyState={{
          title: t(K.page.notifications.noNotifications),
          description: t(K.page.notifications.noNotificationsDescription),
          actions: [
            {
              label: t(K.common.refresh),
              onClick: () => void loadNotifications(),
              variant: 'contained',
            },
          ],
        }}
        pagination={{
          page: 0,
          pageSize: 25,
          total: notifications.length,
          onPageChange: () => {},
        }}
        onRowClick={(row) => {
          const r = row as any as NotificationRow
          setSelectedRow(r)
          setDetailOpen(true)
          setDetailLoading(true)
          setDetail(null)
          void (async () => {
            try {
              const resp: any = await inboxService.getCard(String(r.cardId || ''), { limit: 50 })
              setDetail(resp?.card ? resp : resp?.data)
              if (r.inboxItemId) {
                await inboxService.markRead(String(r.inboxItemId))
                await loadNotifications()
              }
            } catch (err) {
              console.error('[NotificationsPage] load card detail failed', err)
              toast.error('Load failed')
            } finally {
              setDetailLoading(false)
            }
          })()
        }}
      />

      <Dialog open={detailOpen} onClose={() => setDetailOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>{selectedRow?.title || 'Card'}</DialogTitle>
        <DialogContent>
          {detailLoading ? (
            <Typography variant="body2">{t('common.loading')}</Typography>
          ) : detail?.card ? (
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
              <Typography variant="body2">card_id: {String(detail.card.card_id)}</Typography>
              <Typography variant="body2">type: {String(detail.card.card_type)}</Typography>
              <Typography variant="body2">severity: {String(detail.card.severity)}</Typography>
              <Typography variant="body2">status: {String(detail.card.status)}</Typography>
              <Typography variant="body2">resolution_status: {String(detail.card.resolution_status)}</Typography>
              <Typography variant="body2">summary: {String(detail.card.summary)}</Typography>
              <Typography variant="body2">linked_task_id: {String(detail.card.linked_task_id || '')}</Typography>
              <Divider sx={{ my: 1 }} />
              <Typography variant="subtitle2">state_card_events</Typography>
              <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>{JSON.stringify(detail.state_card_events || [], null, 2)}</Typography>
              <Typography variant="subtitle2">chat_injection_events</Typography>
              <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>{JSON.stringify(detail.chat_injection_events || [], null, 2)}</Typography>
              <Typography variant="subtitle2">work_items</Typography>
              <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>{JSON.stringify(detail.work_items || [], null, 2)}</Typography>
              <Typography variant="subtitle2">tasks</Typography>
              <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>{JSON.stringify(detail.tasks || [], null, 2)}</Typography>
            </Box>
          ) : (
            <Typography variant="body2" color="text.secondary">
              {t(K.page.notifications.noNotificationsDescription)}
            </Typography>
          )}
        </DialogContent>
        <DialogActions>
          {detail?.card?.card_id ? (
            <>
              <Button variant="outlined" onClick={() => void inboxService.closeCard(String(detail.card.card_id))}>
                close
              </Button>
              <Button variant="outlined" onClick={() => void inboxService.markRead(String(selectedRow?.inboxItemId || ''))}>
                mark read
              </Button>
            </>
          ) : null}
          <Button variant="contained" onClick={() => setDetailOpen(false)}>
            {t('common.close')}
          </Button>
        </DialogActions>
      </Dialog>
    </>
  )
}
