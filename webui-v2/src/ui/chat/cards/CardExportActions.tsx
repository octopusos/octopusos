import ContentCopyIcon from '@mui/icons-material/ContentCopy'
import GridOnIcon from '@mui/icons-material/GridOn'
import DownloadIcon from '@mui/icons-material/Download'
import { IconButton, Stack, Tooltip } from '@mui/material'
import { toBlob } from 'html-to-image'
import { type RefObject, useState } from 'react'
import { usePromptDialog } from '@/ui/interaction'
import { useTextTranslation } from '@/ui/text'

type CardExportActionsProps = {
  targetRef: RefObject<HTMLElement>
  fileBaseName: string
  sensitive?: boolean
  tableData?: {
    columns: string[]
    rows: Array<Record<string, unknown>>
  }
}

const EXPORT_IGNORE_ATTR = 'data-export-ignore'

function sanitizeFileName(input: string): string {
  return (input || 'query-card')
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9-_]+/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '')
}

async function buildPngBlob(target: HTMLElement): Promise<Blob | null> {
  return toBlob(target, {
    cacheBust: true,
    pixelRatio: 2,
    filter: (node) => {
      if (!(node instanceof HTMLElement)) return true
      return node.getAttribute(EXPORT_IGNORE_ATTR) !== 'true'
    },
  })
}

function toCsv(tableData: { columns: string[]; rows: Array<Record<string, unknown>> }): string {
  const { columns, rows } = tableData
  const escape = (value: unknown) => `"${String(value ?? '').replace(/"/g, '""')}"`
  const header = columns.map(escape).join(',')
  const body = rows.map((row) => columns.map((c) => escape(row[c])).join(',')).join('\n')
  return `${header}\n${body}`
}

export function CardExportActions({ targetRef, fileBaseName, sensitive = false, tableData }: CardExportActionsProps) {
  const { t } = useTextTranslation()
  const { confirm, dialog } = usePromptDialog()
  const [copyTitle, setCopyTitle] = useState(t('page.chat.cardExport.copyPng'))
  const [downloadTitle, setDownloadTitle] = useState(t('page.chat.cardExport.downloadPng'))
  const [csvTitle, setCsvTitle] = useState(t('page.chat.cardExport.exportCsv'))
  const [xlsxTitle, setXlsxTitle] = useState(t('page.chat.cardExport.exportExcel'))

  const handleDownload = async () => {
    if (sensitive) {
      const proceed = await confirm({
        title: t('page.chat.cardExport.sensitiveTitle'),
        message: t('page.chat.cardExport.confirmExportPng'),
        confirmText: t('common.confirm'),
        cancelText: t('common.cancel'),
        color: 'warning',
        testId: 'card-export-confirm-dialog',
      })
      if (!proceed) return
    }
    const target = targetRef.current
    if (!target) return
    const blob = await buildPngBlob(target)
    if (!blob) return
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${sanitizeFileName(fileBaseName)}.png`
    link.click()
    URL.revokeObjectURL(url)
    setDownloadTitle(t('page.chat.cardExport.downloaded'))
    setTimeout(() => setDownloadTitle(t('page.chat.cardExport.downloadPng')), 1200)
  }

  const handleCopy = async () => {
    if (sensitive) {
      const proceed = await confirm({
        title: t('page.chat.cardExport.sensitiveTitle'),
        message: t('page.chat.cardExport.confirmCopyPng'),
        confirmText: t('common.confirm'),
        cancelText: t('common.cancel'),
        color: 'warning',
        testId: 'card-copy-confirm-dialog',
      })
      if (!proceed) return
    }
    const target = targetRef.current
    if (!target) return
    const blob = await buildPngBlob(target)
    if (!blob) return
    if (!('clipboard' in navigator) || typeof ClipboardItem === 'undefined') {
      setCopyTitle(t('page.chat.cardExport.unsupported'))
      setTimeout(() => setCopyTitle(t('page.chat.cardExport.copyPng')), 1200)
      return
    }
    await navigator.clipboard.write([new ClipboardItem({ 'image/png': blob })])
    setCopyTitle(t('page.chat.cardExport.copied'))
    setTimeout(() => setCopyTitle(t('page.chat.cardExport.copyPng')), 1200)
  }

  const handleExportCsv = async () => {
    if (!tableData || !tableData.columns.length || !tableData.rows.length) return
    if (sensitive) {
      const proceed = await confirm({
        title: t('page.chat.cardExport.sensitiveTitle'),
        message: t('page.chat.cardExport.confirmExportCsv'),
        confirmText: t('common.confirm'),
        cancelText: t('common.cancel'),
        color: 'warning',
        testId: 'card-export-csv-confirm-dialog',
      })
      if (!proceed) return
    }
    const csv = toCsv(tableData)
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${sanitizeFileName(fileBaseName)}.csv`
    link.click()
    URL.revokeObjectURL(url)
    setCsvTitle(t('page.chat.cardExport.exported'))
    setTimeout(() => setCsvTitle(t('page.chat.cardExport.exportCsv')), 1200)
  }

  const handleExportXlsx = async () => {
    if (!tableData || !tableData.columns.length || !tableData.rows.length) return
    if (sensitive) {
      const proceed = await confirm({
        title: t('page.chat.cardExport.sensitiveTitle'),
        message: t('page.chat.cardExport.confirmExportExcel'),
        confirmText: t('common.confirm'),
        cancelText: t('common.cancel'),
        color: 'warning',
        testId: 'card-export-excel-confirm-dialog',
      })
      if (!proceed) return
    }
    const XLSX = await import('xlsx')
    const rows = tableData.rows.map((row) => {
      const next: Record<string, unknown> = {}
      for (const col of tableData.columns) next[col] = row[col]
      return next
    })
    const worksheet = XLSX.utils.json_to_sheet(rows)
    const workbook = XLSX.utils.book_new()
    XLSX.utils.book_append_sheet(workbook, worksheet, 'data')
    XLSX.writeFile(workbook, `${sanitizeFileName(fileBaseName)}.xlsx`)
    setXlsxTitle(t('page.chat.cardExport.exported'))
    setTimeout(() => setXlsxTitle(t('page.chat.cardExport.exportExcel')), 1200)
  }

  return (
    <Stack
      direction="row"
      spacing={0.5}
      sx={{ flexShrink: 0 }}
      {...{ [EXPORT_IGNORE_ATTR]: 'true' }}
    >
      <Tooltip title={copyTitle}>
        <IconButton size="small" onClick={handleCopy} sx={{ color: 'rgba(255,255,255,0.78)' }}>
          <ContentCopyIcon sx={{ fontSize: 16 }} />
        </IconButton>
      </Tooltip>
      <Tooltip title={downloadTitle}>
        <IconButton size="small" onClick={handleDownload} sx={{ color: 'rgba(255,255,255,0.78)' }}>
          <DownloadIcon sx={{ fontSize: 16 }} />
        </IconButton>
      </Tooltip>
      <Tooltip title={csvTitle}>
        <span>
          <IconButton
            size="small"
            onClick={handleExportCsv}
            disabled={!tableData?.rows?.length}
            sx={{ color: 'rgba(255,255,255,0.78)' }}
          >
            <GridOnIcon sx={{ fontSize: 16 }} />
          </IconButton>
        </span>
      </Tooltip>
      <Tooltip title={xlsxTitle}>
        <span>
          <IconButton
            size="small"
            onClick={handleExportXlsx}
            disabled={!tableData?.rows?.length}
            sx={{ color: 'rgba(255,255,255,0.78)' }}
          >
            <DownloadIcon sx={{ fontSize: 16 }} />
          </IconButton>
        </span>
      </Tooltip>
      {dialog}
    </Stack>
  )
}
