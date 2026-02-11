import { useEffect, useMemo, useState } from 'react'
import { Box, Button, Divider, List, ListItem, ListItemButton, ListItemText, Typography } from '@mui/material'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { usePageHeader } from '@/ui/layout'
import { K, useTextTranslation } from '@/ui/text'
import { toast } from '@/ui/feedback'
import { changelogService, type ChangeLogIndexEntry } from '@/services'

export default function ChangeLogPage() {
  const { t, language } = useTextTranslation()
  const [loading, setLoading] = useState(true)
  const [versions, setVersions] = useState<ChangeLogIndexEntry[]>([])
  const [selectedKey, setSelectedKey] = useState<string>('')
  const [md, setMd] = useState<string>('')
  const [mdLoading, setMdLoading] = useState(false)

  usePageHeader({
    title: t(K.page.changeLog.title),
    subtitle: t(K.page.changeLog.subtitle),
  })

  const selected = useMemo(() => versions.find((v) => v.key === selectedKey) || null, [versions, selectedKey])

  const loadIndex = async (lang: 'en' | 'zh') => {
    setLoading(true)
    try {
      const resp: any = await changelogService.getIndex(lang)
      const items = Array.isArray(resp?.versions) ? resp.versions : Array.isArray(resp?.data?.versions) ? resp.data.versions : []
      setVersions(items)
      if (items.length) {
        const current = String(selectedKey || '')
        const stillExists = current ? items.some((v: any) => String(v?.key || '') === current) : false
        if (!stillExists) {
          setSelectedKey(String(items[0].key || ''))
        }
      } else {
        setSelectedKey('')
      }
    } catch (err) {
      console.error('[ChangeLogPage] load index failed', err)
      toast.error('Request failed')
      setVersions([])
    } finally {
      setLoading(false)
    }
  }

  const loadEntry = async (key: string, lang: 'en' | 'zh') => {
    if (!key) return
    setMdLoading(true)
    try {
      const content = await changelogService.getEntry(key, lang)
      setMd(content)
    } catch (err) {
      console.error('[ChangeLogPage] load entry failed', err)
      toast.error('Load failed')
      setMd('')
    } finally {
      setMdLoading(false)
    }
  }

  useEffect(() => {
    void loadIndex(language)
  }, [language])

  useEffect(() => {
    if (!selectedKey) return
    void loadEntry(selectedKey, language)
  }, [selectedKey, language])

  return (
    <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '420px 1fr' }, gap: 2 }}>
      <Box sx={{ border: 1, borderColor: 'divider', borderRadius: 1, overflow: 'hidden' }}>
        <Box sx={{ p: 2, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Typography variant="subtitle2">{t(K.page.changeLog.versions)}</Typography>
          <Button size="small" variant="outlined" onClick={() => void loadIndex(language)} disabled={loading}>
            {t('common.refresh')}
          </Button>
        </Box>
        <Divider />
        <List dense disablePadding sx={{ maxHeight: { xs: 'auto', md: '70vh' }, overflow: 'auto' }}>
          {versions.map((v) => {
            const outline = Array.isArray(v.outline) ? v.outline : []
            return (
              <ListItem key={v.key} disablePadding>
                <ListItemButton selected={v.key === selectedKey} onClick={() => setSelectedKey(v.key)}>
                  <ListItemText
                    primary={String(v.title || v.key)}
                    secondary={
                      outline.length ? (
                        <Box component="ul" sx={{ pl: 2, m: 0.5 }}>
                          {outline.slice(0, 6).map((line, i) => (
                            <Box component="li" key={`${v.key}_${i}`} sx={{ typography: 'caption', color: 'text.secondary' }}>
                              {String(line)}
                            </Box>
                          ))}
                        </Box>
                      ) : null
                    }
                    // Prevent <ul> being nested under MUI Typography's default <p>.
                    secondaryTypographyProps={{ component: 'div' }}
                  />
                </ListItemButton>
              </ListItem>
            )
          })}
          {!versions.length && !loading ? (
            <ListItem>
              <ListItemText primary={t(K.page.changeLog.empty)} />
            </ListItem>
          ) : null}
        </List>
      </Box>

      <Box sx={{ border: 1, borderColor: 'divider', borderRadius: 1, overflow: 'hidden' }}>
        <Box sx={{ p: 2 }}>
          <Typography variant="subtitle2">{selected ? String(selected.title || selected.key) : t(K.page.changeLog.details)}</Typography>
        </Box>
        <Divider />
        <Box sx={{ p: 2, overflow: 'auto', maxHeight: { xs: 'auto', md: '70vh' } }}>
          {mdLoading ? (
            <Typography variant="body2">{t(K.page.changeLog.loading)}</Typography>
          ) : md ? (
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{md}</ReactMarkdown>
          ) : (
            <Typography variant="body2" color="text.secondary">
              {t(K.page.changeLog.noDetails)}
            </Typography>
          )}
        </Box>
      </Box>
    </Box>
  )
}
