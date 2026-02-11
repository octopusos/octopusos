import { useEffect, useMemo, useState } from 'react'
import { Box, Button, Chip, Dialog, DialogActions, DialogContent, DialogTitle, Typography } from '@/ui'
import type { GridColDef } from '@/ui'
import { FilterBar, TableShell } from '@/ui'
import { usePageActions, usePageHeader } from '@/ui/layout'
import { K, useTextTranslation } from '@/ui/text'
import { toast } from '@/ui/feedback'
import { execTasksService } from '@/services'
import { systemService } from '@services/system.service'

type TaskRow = {
  task_id: string
  work_id?: string | null
  card_id?: string | null
  task_type: string
  status: string
  risk_level: string
  requires_confirmation: boolean
  created_at_ms: number
  updated_at_ms: number
  started_at_ms?: number | null
  finished_at_ms?: number | null
  input_json: string
  output_json: string
  error_json?: string | null
  evidence_paths_json: string
  idempotency_key: string
}

function fmtTs(ms: number): string {
  try {
    return new Date(Number(ms)).toISOString()
  } catch {
    return ''
  }
}

export default function TaskListPage() {
  const { t } = useTextTranslation()
  const [loading, setLoading] = useState(true)
  const [rows, setRows] = useState<TaskRow[]>([])
  const [mode, setMode] = useState<string>('reactive')
  const [autoExec, setAutoExec] = useState<boolean>(false)
  const [autoRefresh, setAutoRefresh] = useState<boolean>(true)
  const [detail, setDetail] = useState<TaskRow | null>(null)

  usePageHeader({
    title: t(K.page.taskList.title),
    subtitle: t(K.page.taskList.subtitle),
  })

  const load = async () => {
    setLoading(true)
    try {
      const resp: any = await execTasksService.list({ status: 'queued,running,succeeded,failed,cancelled', limit: 100 })
      const modeResp: any = await systemService.resolveConfig('work.mode.global')
      const autoResp: any = await systemService.resolveConfig('work.auto_execute.enabled')
      const items = Array.isArray(resp?.items) ? resp.items : Array.isArray(resp?.data?.items) ? resp.data.items : []
      setRows(items as TaskRow[])
      setMode(String(modeResp?.value || 'reactive'))
      setAutoExec(Boolean(autoResp?.value))
    } catch (err) {
      console.error('[TaskListPage] load failed', err)
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
      variant: 'outlined',
      onClick: async () => {
        await setConfigKey('work.mode.global', 'reactive')
        toast.success(t('common.success'))
        await load()
      },
    },
    {
      key: 'modeProactive',
      label: t(K.page.workList.modeProactive),
      variant: 'outlined',
      onClick: async () => {
        await setConfigKey('work.mode.global', 'proactive')
        toast.success(t('common.success'))
        await load()
      },
    },
    {
      key: 'modeSilent',
      label: t(K.page.workList.modeSilent),
      variant: 'outlined',
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
    {
      key: 'modeLabel',
      label: `${t(K.page.taskList.currentMode)}: ${mode}`,
      variant: 'outlined',
      onClick: () => {},
    },
  ])

  const columns: GridColDef[] = [
    { field: 'status', headerName: 'status', width: 120, renderCell: (p) => <Chip size="small" label={String(p.value)} variant="outlined" /> },
    { field: 'task_type', headerName: 'type', width: 220 },
    { field: 'risk_level', headerName: 'risk', width: 120 },
    { field: 'card_id', headerName: 'card_id', width: 180 },
    { field: 'work_id', headerName: 'work_id', width: 180 },
    { field: 'updated_at_ms', headerName: 'updated_at', width: 200, valueFormatter: (p: any) => fmtTs(Number(p?.value)) },
  ]

  const tableRows = useMemo(() => rows.map((r) => ({ id: r.task_id, ...r })), [rows])

  return (
    <>
      <TableShell
        loading={loading}
        rows={tableRows}
        columns={columns}
        onRowClick={(params: any) => setDetail(params.row as TaskRow)}
        filterBar={<FilterBar filters={[]} actions={[]} />}
      />

      <Dialog open={!!detail} onClose={() => setDetail(null)} maxWidth="md" fullWidth>
        <DialogTitle>{t(K.page.taskList.detailTitle)}</DialogTitle>
        <DialogContent>
          {detail ? (
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
              <Typography variant="body2">task_id: {detail.task_id}</Typography>
              <Typography variant="body2">status: {detail.status}</Typography>
              <Typography variant="body2">task_type: {detail.task_type}</Typography>
              <Typography variant="body2">risk_level: {detail.risk_level}</Typography>
              <Typography variant="body2">card_id: {String(detail.card_id || '')}</Typography>
              <Typography variant="body2">work_id: {String(detail.work_id || '')}</Typography>
              <Typography variant="body2">input_json: {detail.input_json}</Typography>
              <Typography variant="body2">output_json: {detail.output_json}</Typography>
              <Typography variant="body2">error_json: {String(detail.error_json || '')}</Typography>
              <Typography variant="body2">evidence_paths_json: {detail.evidence_paths_json}</Typography>
            </Box>
          ) : null}
        </DialogContent>
        <DialogActions>
          {detail ? (
            <>
              <Button
                variant="outlined"
                onClick={async () => {
                  await execTasksService.cancel(detail.task_id)
                  toast.success(t('common.success'))
                  setDetail(null)
                  await load()
                }}
              >
                {t('common.cancel')}
              </Button>
              <Button
                variant="outlined"
                onClick={async () => {
                  await execTasksService.retry(detail.task_id)
                  toast.success(t('common.success'))
                  setDetail(null)
                  await load()
                }}
              >
                {t('common.retry')}
              </Button>
            </>
          ) : null}
          <Button variant="contained" onClick={() => setDetail(null)}>
            {t('common.close')}
          </Button>
        </DialogActions>
      </Dialog>
    </>
  )
}
