import { useEffect, useMemo, useState } from 'react'
import { Box, Button, Chip, Dialog, DialogActions, DialogContent, DialogTitle, Typography } from '@/ui'
import type { GridColDef } from '@/ui'
import { FilterBar, TableShell } from '@/ui'
import { usePageActions, usePageHeader } from '@/ui/layout'
import { K, useTextTranslation } from '@/ui/text'
import { toast } from '@/ui/feedback'
import { execTasksService, workItemsService } from '@/services'
import { systemService } from '@services/system.service'

type WorkRow = {
  work_id: string
  type: string
  title: string
  status: string
  priority: number
  scope_id: string
  source_card_id?: string | null
  updated_at_ms: number
  summary: string
  detail_json: string
  evidence_ref_json: string
}

function fmtTs(ms: number): string {
  try {
    return new Date(Number(ms)).toISOString()
  } catch {
    return ''
  }
}

export default function WorkListPage() {
  const { t } = useTextTranslation()
  const [loading, setLoading] = useState(true)
  const [rows, setRows] = useState<WorkRow[]>([])
  const [mode, setMode] = useState<string>('reactive')
  const [autoExec, setAutoExec] = useState<boolean>(false)
  const [detail, setDetail] = useState<WorkRow | null>(null)
  const [exporting, setExporting] = useState(false)
  const [autoRefresh, setAutoRefresh] = useState<boolean>(true)

  usePageHeader({
    title: t(K.page.workList.title),
    subtitle: t(K.page.workList.subtitle),
  })

  const load = async () => {
    setLoading(true)
    try {
      const workResp: any = await workItemsService.list({ status: 'queued,running,succeeded,failed,cancelled', limit: 100 })
      const modeResp: any = await systemService.resolveConfig('work.mode.global')
      const autoResp: any = await systemService.resolveConfig('work.auto_execute.enabled')
      const items = Array.isArray(workResp?.items) ? workResp.items : Array.isArray(workResp?.data?.items) ? workResp.data.items : []
      setRows(items as WorkRow[])
      setMode(String(modeResp?.value || 'reactive'))
      setAutoExec(Boolean(autoResp?.value))
    } catch (err) {
      console.error('[WorkListPage] load failed', err)
      toast.error('Request failed')
      setRows([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
  }, [])

  useEffect(() => {
    if (!autoRefresh) return
    const id = window.setInterval(() => {
      if (document.visibilityState !== 'visible') return
      void load()
    }, 8000)
    return () => window.clearInterval(id)
  }, [autoRefresh])

  const exportTransparencyBundle = async () => {
    if (exporting) return
    setExporting(true)
    try {
      const resp = await fetch('/api/transparency/export?limit=50', { method: 'GET' })
      if (!resp.ok) {
        throw new Error(`export_failed_${resp.status}`)
      }
      const blob = await resp.blob()
      const cd = resp.headers.get('content-disposition') || ''
      const match = cd.match(/filename=\"?([^\";]+)\"?/i)
      const filename = match?.[1] || `transparency-bundle-${Date.now()}.zip`

      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      document.body.appendChild(a)
      a.click()
      a.remove()
      window.URL.revokeObjectURL(url)
      toast.success(t('common.success'))
    } catch (err) {
      console.error('[WorkListPage] export bundle failed', err)
      toast.error('Export failed')
    } finally {
      setExporting(false)
    }
  }

  const setConfigKey = async (key: string, value: any) => {
    try {
      await systemService.createConfigEntry({
        key,
        value,
        type: typeof value === 'boolean' ? 'Boolean' : 'String',
        scope: 'global',
        is_secret: false,
        is_hot_reload: true,
        confirm: true,
      } as any)
      if (key === 'work.mode.global') {
        window.dispatchEvent(new CustomEvent('octopusos:work-mode-updated', { detail: { mode: String(value) } }))
      }
    } catch (err: any) {
      // Retry with dry_run/confirm patterns when required.
      const code = err?.response?.data?.error
      if (code === 'CONFIG_REQUIRES_DRY_RUN') {
        await systemService.createConfigEntry({ key, value, type: typeof value === 'boolean' ? 'Boolean' : 'String', scope: 'global', is_secret: false, is_hot_reload: true, dry_run: true } as any)
        await systemService.createConfigEntry({ key, value, type: typeof value === 'boolean' ? 'Boolean' : 'String', scope: 'global', is_secret: false, is_hot_reload: true, confirm: true } as any)
      } else if (code === 'CONFIG_HIGH_RISK_CONFIRMATION_REQUIRED') {
        await systemService.createConfigEntry({ key, value, type: typeof value === 'boolean' ? 'Boolean' : 'String', scope: 'global', is_secret: false, is_hot_reload: true, confirm: true } as any)
      } else {
        throw err
      }
      if (key === 'work.mode.global') {
        window.dispatchEvent(new CustomEvent('octopusos:work-mode-updated', { detail: { mode: String(value) } }))
      }
    }
  }

  usePageActions([
    {
      key: 'refresh',
      label: t('common.refresh'),
      variant: 'outlined',
      onClick: () => void load(),
    },
    {
      key: 'modeReactive',
      label: t(K.page.workList.modeReactive),
      variant: mode === 'reactive' ? 'contained' : 'outlined',
      onClick: async () => {
        await setConfigKey('work.mode.global', 'reactive')
        toast.success(t('common.success'))
        await load()
      },
    },
    {
      key: 'modeProactive',
      label: t(K.page.workList.modeProactive),
      variant: mode === 'proactive' ? 'contained' : 'outlined',
      onClick: async () => {
        await setConfigKey('work.mode.global', 'proactive')
        toast.success(t('common.success'))
        await load()
      },
    },
    {
      key: 'modeSilent',
      label: t(K.page.workList.modeSilent),
      variant: mode === 'silent_proactive' ? 'contained' : 'outlined',
      onClick: async () => {
        await setConfigKey('work.mode.global', 'silent_proactive')
        toast.success(t('common.success'))
        await load()
      },
    },
    {
      key: 'autoExec',
      label: autoExec ? t(K.page.workList.autoExecOn) : t(K.page.workList.autoExecOff),
      variant: 'outlined',
      onClick: async () => {
        await setConfigKey('work.auto_execute.enabled', !autoExec)
        toast.success(t('common.success'))
        await load()
      },
    },
    {
      key: 'autoRefresh',
      label: autoRefresh ? 'Auto-refresh: ON' : 'Auto-refresh: OFF',
      variant: 'outlined',
      onClick: () => setAutoRefresh(!autoRefresh),
    },
  ])

  const columns: GridColDef[] = [
    { field: 'status', headerName: 'status', width: 120, renderCell: (p) => <Chip size="small" label={String(p.value)} variant="outlined" /> },
    { field: 'type', headerName: 'type', width: 160 },
    { field: 'title', headerName: 'title', flex: 1, minWidth: 240 },
    { field: 'priority', headerName: 'priority', width: 120 },
    { field: 'scope_id', headerName: 'scope', width: 220 },
    { field: 'source_card_id', headerName: 'card_id', width: 180 },
    { field: 'updated_at_ms', headerName: 'updated_at', width: 200, valueFormatter: (p: any) => fmtTs(Number(p?.value)) },
  ]

  const tableRows = useMemo(() => rows.map((r) => ({ id: r.work_id, ...r })), [rows])

  return (
    <>
      <Box
        sx={{
          mb: 2,
          p: 2,
          border: 1,
          borderColor: 'divider',
          borderRadius: 1,
          display: 'flex',
          flexDirection: 'column',
          gap: 0.5,
        }}
      >
        <Typography variant="subtitle2">{t(K.page.workList.modeExplainTitle)}</Typography>
        <Typography variant="body2">
          <b>{t(K.page.workList.modeReactive)}:</b> {t(K.page.workList.modeExplainReactive)}
        </Typography>
        <Typography variant="body2">
          <b>{t(K.page.workList.modeProactive)}:</b> {t(K.page.workList.modeExplainProactive)}
        </Typography>
        <Typography variant="body2">
          <b>{t(K.page.workList.modeSilent)}:</b> {t(K.page.workList.modeExplainSilent)}
        </Typography>
      </Box>

      <TableShell
        loading={loading}
        rows={tableRows}
        columns={columns}
        onRowClick={(params: any) => setDetail(params.row as WorkRow)}
        filterBar={
          <FilterBar
            filters={[]}
            actions={[
              {
                key: 'openTasks',
                label: t(K.page.workList.openTaskList),
                variant: 'outlined',
                onClick: async () => {
                  // Lightweight sanity ping: list tasks to ensure API is reachable.
                  await execTasksService.list({ status: 'queued,running,succeeded,failed', limit: 5 })
                  toast.info(t(K.page.workList.taskListHint))
                },
              },
              {
                key: 'exportBundle',
                label: exporting ? `${t(K.page.workList.exportBundle)}...` : t(K.page.workList.exportBundle),
                variant: 'outlined',
                onClick: async () => {
                  await exportTransparencyBundle()
                },
              },
            ]}
          />
        }
      />

      <Dialog open={!!detail} onClose={() => setDetail(null)} maxWidth="md" fullWidth>
        <DialogTitle>{t(K.page.workList.detailTitle)}</DialogTitle>
        <DialogContent>
          {detail ? (
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
              <Typography variant="body2">work_id: {detail.work_id}</Typography>
              <Typography variant="body2">status: {detail.status}</Typography>
              <Typography variant="body2">type: {detail.type}</Typography>
              <Typography variant="body2">title: {detail.title}</Typography>
              <Typography variant="body2">summary: {detail.summary}</Typography>
              <Typography variant="body2">detail_json: {detail.detail_json}</Typography>
              <Typography variant="body2">evidence_ref_json: {detail.evidence_ref_json}</Typography>
            </Box>
          ) : null}
        </DialogContent>
        <DialogActions>
          {detail ? (
            <Button
              variant="outlined"
              onClick={async () => {
                await workItemsService.cancel(detail.work_id)
                toast.success(t('common.success'))
                setDetail(null)
                await load()
              }}
            >
              {t('common.cancel')}
            </Button>
          ) : null}
          <Button variant="contained" onClick={() => setDetail(null)}>
            {t('common.close')}
          </Button>
        </DialogActions>
      </Dialog>
    </>
  )
}
