import { useEffect, useMemo, useState } from 'react'
import {
  Box,
  Button,
  Paper,
  Stack,
  TextField,
  Typography,
  MenuItem,
  FormControl,
  InputLabel,
  Select,
} from '@mui/material'
import { get, post, put } from '@platform/http/httpClient'
import { getToken } from '@platform/auth/adminToken'
import { K, t } from '@/ui/text'


type SchemaRow = {
  kind: string
  version: number
  source: string
  schema: Record<string, unknown>
}

type HistoryRow = {
  kind: string
  action: string
  actor: string
  from_version: number
  to_version: number
  created_at: string
}

export default function FactsSchemaPage() {
  const [rows, setRows] = useState<SchemaRow[]>([])
  const [history, setHistory] = useState<HistoryRow[]>([])
  const [selectedKind, setSelectedKind] = useState('')
  const [editor, setEditor] = useState('{}')
  const [note, setNote] = useState('')
  const [status, setStatus] = useState('')
  const [targetVersion, setTargetVersion] = useState('')

  useEffect(() => {
    void refreshAll()
  }, [])

  const selected = useMemo(() => rows.find((r) => r.kind === selectedKind) || null, [rows, selectedKind])

  useEffect(() => {
    if (!selected) return
    setEditor(JSON.stringify(selected.schema, null, 2))
    setTargetVersion(String(selected.version || 1))
  }, [selected])

  useEffect(() => {
    if (rows.length === 0) {
      if (selectedKind !== '') {
        setSelectedKind('')
      }
      return
    }
    if (!rows.some((r) => r.kind === selectedKind)) {
      setSelectedKind(rows[0].kind)
    }
  }, [rows, selectedKind])

  async function refreshAll() {
    const [schemaRes, historyRes] = await Promise.all([
      get<{ ok: boolean; data: SchemaRow[] }>('/api/compat/external-facts/schema'),
      get<{ ok: boolean; data: HistoryRow[] }>('/api/compat/external-facts/schema/history', { params: { limit: 100 } }),
    ])
    setRows(schemaRes.data || [])
    setHistory(historyRes.data || [])
  }

  async function exportJson() {
    const result = await get<{ ok: boolean; data: Record<string, unknown> }>('/api/compat/external-facts/schema/export')
    const blob = new Blob([JSON.stringify(result.data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'external-facts-schemas.json'
    a.click()
    URL.revokeObjectURL(url)
  }

  async function applySchema() {
    try {
      const token = getToken()
      if (!token) {
        setStatus(t(K.page.factsSchema.adminTokenRequired))
        return
      }
      const parsed = JSON.parse(editor)
      await put('/api/compat/external-facts/schema/apply', {
        schemas: { [selectedKind]: parsed },
        note,
      }, {
        headers: { 'X-Admin-Token': token },
      })
      setStatus(t(K.page.factsSchema.applied))
      await refreshAll()
    } catch (err: any) {
      setStatus(err?.message || t(K.page.factsSchema.applyFailed))
    }
  }

  async function rollbackSchema() {
    try {
      const token = getToken()
      if (!token) {
        setStatus(t(K.page.factsSchema.adminTokenRequired))
        return
      }
      await post('/api/compat/external-facts/schema/rollback', {
        kind: selectedKind,
        target_version: Number(targetVersion),
      }, {
        headers: { 'X-Admin-Token': token },
      })
      setStatus(t(K.page.factsSchema.rolledBack))
      await refreshAll()
    } catch (err: any) {
      setStatus(err?.message || t(K.page.factsSchema.rollbackFailed))
    }
  }

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h5" sx={{ mb: 1 }}>{t(K.page.factsSchema.title)}</Typography>
      <Typography variant="body2" sx={{ mb: 2, opacity: 0.8 }}>
        {t(K.page.factsSchema.subtitle)}
      </Typography>

      <Stack direction={{ xs: 'column', md: 'row' }} spacing={2}>
        <Paper sx={{ p: 2, minWidth: 280 }}>
          <FormControl fullWidth size="small" sx={{ mb: 1.5 }}>
            <InputLabel>{t(K.page.factsSchema.kind)}</InputLabel>
            <Select value={selectedKind} label={t(K.page.factsSchema.kind)} onChange={(e) => setSelectedKind(String(e.target.value))}>
              {rows.map((r) => (
                <MenuItem key={r.kind} value={r.kind}>
                  {t(K.page.factsSchema.kindVersion, { kind: r.kind, version: r.version })}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <Stack direction="row" spacing={1} sx={{ mb: 1.5 }}>
            <Button size="small" variant="outlined" onClick={() => void refreshAll()}>{t(K.page.factsSchema.refresh)}</Button>
            <Button size="small" variant="outlined" onClick={() => void exportJson()}>{t(K.page.factsSchema.exportJson)}</Button>
          </Stack>

          <TextField
            label={t(K.page.factsSchema.rollbackTargetVersion)}
            size="small"
            fullWidth
            value={targetVersion}
            onChange={(e) => setTargetVersion(e.target.value)}
            sx={{ mb: 1 }}
          />
          <Button size="small" color="warning" variant="contained" onClick={() => void rollbackSchema()}>
            {t(K.page.factsSchema.rollback)}
          </Button>

          <Typography variant="caption" sx={{ display: 'block', mt: 1.5, opacity: 0.75 }}>
            {t(K.page.factsSchema.writesRequireAdmin)}
          </Typography>
        </Paper>

        <Paper sx={{ p: 2, flex: 1 }}>
          <TextField
            label={t(K.page.factsSchema.schemaJsonLabel)}
            multiline
            minRows={16}
            fullWidth
            value={editor}
            onChange={(e) => setEditor(e.target.value)}
            sx={{ mb: 1.5 }}
          />
          <TextField
            size="small"
            fullWidth
            label={t(K.page.factsSchema.changeNote)}
            value={note}
            onChange={(e) => setNote(e.target.value)}
            sx={{ mb: 1.5 }}
          />
          <Stack direction="row" spacing={1}>
            <Button variant="contained" onClick={() => void applySchema()}>{t(K.page.factsSchema.applyAdmin)}</Button>
          </Stack>
          {status && (
            <Typography variant="caption" sx={{ display: 'block', mt: 1.5 }}>{status}</Typography>
          )}
        </Paper>
      </Stack>

      <Paper sx={{ p: 2, mt: 2 }}>
        <Typography variant="h6" sx={{ mb: 1 }}>{t(K.page.factsSchema.auditHistory)}</Typography>
        {history.length === 0 && <Typography variant="body2">{t(K.page.factsSchema.noHistory)}</Typography>}
        {history.map((h, idx) => (
          <Typography key={`${h.kind}-${h.created_at}-${idx}`} variant="body2" sx={{ mb: 0.5 }}>
            {t(K.page.factsSchema.historyRecord, {
              createdAt: h.created_at,
              kind: h.kind,
              action: h.action,
              actor: h.actor,
              fromVersion: h.from_version,
              toVersion: h.to_version,
            })}
          </Typography>
        ))}
      </Paper>
    </Box>
  )
}
