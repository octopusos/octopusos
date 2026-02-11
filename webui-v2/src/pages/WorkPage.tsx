import { useCallback, useEffect, useMemo, useRef, useState, type MouseEvent as ReactMouseEvent } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import {
  Autocomplete,
  Chip,
  Box,
  Button,
  Divider,
  IconButton,
  List,
  ListItem,
  ListItemText,
  Paper,
  Tab,
  Tabs,
  TextField,
  Tooltip,
  Typography,
  useMediaQuery,
  useTheme,
} from '@mui/material'
import { ChatShell, ModelSelectionBar, type ChatMessageType } from '@/ui'
import { DownloadIcon, EditIcon, MoreIcon, SaveIcon, VisibilityIcon } from '@/ui/icons'
import { usePageHeader } from '@/ui/layout'
import { toast } from '@/ui/feedback'
import { K, useTextTranslation } from '@/ui/text'
import { useWebSocket, type WebSocketMessage } from '@/hooks/useWebSocket'
import { workService, type WorkArtifact, type WorkRightTab, type WorkSessionListItem, type WorkSessionState } from '@/services/work.service'
import { systemService } from '@services'
import { providersApi } from '@/api/providers'

type SelectionState = { start: number; end: number; text?: string } | null

const MIN_LEFT_WIDTH = 360
const MAX_LEFT_WIDTH = 860
const LEFT_WIDTH_STORAGE_KEY = 'work.left.width'
const HIDE_SCROLLBAR_SX = {
  scrollbarWidth: 'none',
  '&::-webkit-scrollbar': {
    display: 'none',
  },
} as const

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value))
}

function buildOutline(markdown: string): Array<{ level: number; title: string }> {
  const lines = markdown.split('\n')
  const result: Array<{ level: number; title: string }> = []
  for (const line of lines) {
    const match = /^(#{1,6})\s+(.+)$/.exec(line.trim())
    if (!match) continue
    result.push({ level: match[1].length, title: match[2].trim() })
  }
  return result
}

export default function WorkPage() {
  const theme = useTheme()
  const isMobile = useMediaQuery(theme.breakpoints.down('md'))
  const { t } = useTextTranslation()

  const [sessions, setSessions] = useState<WorkSessionListItem[]>([])
  const [sessionQuery, setSessionQuery] = useState('')
  const [currentSessionId, setCurrentSessionId] = useState('')
  const [sessionTitle, setSessionTitle] = useState('')
  const [messages, setMessages] = useState<ChatMessageType[]>([])
  const [artifacts, setArtifacts] = useState<WorkArtifact[]>([])
  const [activeArtifactId, setActiveArtifactId] = useState('')
  const [activeTab, setActiveTab] = useState<WorkRightTab>('preview')
  const [markdownDraft, setMarkdownDraft] = useState('')
  const [editMode, setEditMode] = useState(false)
  const [selection, setSelection] = useState<SelectionState>(null)
  const [leftWidth, setLeftWidth] = useState(() => {
    const raw = localStorage.getItem(LEFT_WIDTH_STORAGE_KEY)
    const parsed = raw ? Number(raw) : 520
    return Number.isFinite(parsed) ? clamp(parsed, MIN_LEFT_WIDTH, MAX_LEFT_WIDTH) : 520
  })
  const [mobileCanvasCollapsed, setMobileCanvasCollapsed] = useState(false)
  const [loadingSession, setLoadingSession] = useState(true)
  const [streamingMessage, setStreamingMessage] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const [awaitingReply, setAwaitingReply] = useState(false)
  const [inputValue, setInputValue] = useState('')
  const [serviceStatus, setServiceStatus] = useState<'ok' | 'degraded'>('ok')
  const [serviceStatusText, setServiceStatusText] = useState('')
  const [saveStatus, setSaveStatus] = useState<'saved' | 'saving'>('saved')
  const [mode, setMode] = useState<'local' | 'cloud'>('local')
  const [provider, setProvider] = useState('')
  const [model, setModel] = useState('')
  const [providers, setProviders] = useState<string[]>([])
  const [models, setModels] = useState<string[]>([])

  const resizeStateRef = useRef<{ startX: number; startWidth: number } | null>(null)

  usePageHeader({
    title: t(K.page.work.title),
    subtitle: t(K.page.work.subtitle),
  })

  const activeArtifact = useMemo(
    () => artifacts.find((item) => item.artifact_id === activeArtifactId) || artifacts[0] || null,
    [artifacts, activeArtifactId]
  )

  const outline = useMemo(
    () => buildOutline(activeArtifact?.content || ''),
    [activeArtifact?.content]
  )

  const loadSessionState = useCallback(async (sessionId: string) => {
    setLoadingSession(true)
    try {
      const state = await workService.getSession(sessionId)
      setCurrentSessionId(state.session_id)
      setSessionTitle(state.title || t(K.page.work.defaultSessionName))
      setMessages((state.messages || []).filter((m) => m.role !== 'tool'))
      setArtifacts(state.artifacts || [])
      setActiveArtifactId(state.active_artifact_id || state.artifacts?.[0]?.artifact_id || '')
      setActiveTab(state.ui_state?.right_tab || 'preview')
      setLeftWidth((prev) => clamp(state.ui_state?.left_width || prev, MIN_LEFT_WIDTH, MAX_LEFT_WIDTH))
      setSelection(state.ui_state?.selection || null)
    } catch (error) {
      console.error('[WorkPage] failed to load session', error)
      setServiceStatus('degraded')
      setServiceStatusText(t(K.page.work.statusSessionLoadFailed))
    } finally {
      setLoadingSession(false)
    }
  }, [])

  const loadWorkSessions = useCallback(async (query = '') => {
    try {
      const response = await workService.listSessions({ recent: 20, query })
      const next = response.sessions || []
      setServiceStatus('ok')
      setServiceStatusText(t(K.page.work.statusReady))
      setSessions(next)
      if (!next.length) {
        try {
          const created = await workService.createSession()
          setSessions([{
            session_id: created.session_id,
            title: created.title,
            updated_at: created.updated_at,
            created_at: created.created_at,
          }])
          await loadSessionState(created.session_id)
        } catch (createError) {
          console.error('[WorkPage] failed to auto-create session', createError)
          setServiceStatus('degraded')
          setServiceStatusText(t(K.page.work.statusServiceUnavailable))
          setLoadingSession(false)
        }
        return
      }
      if (!currentSessionId || !next.some((item) => item.session_id === currentSessionId)) {
        await loadSessionState(next[0].session_id)
      }
    } catch (error) {
      console.error('[WorkPage] failed to list sessions', error)
      setServiceStatus('degraded')
      setServiceStatusText(t(K.page.work.statusServiceUnavailable))
      setLoadingSession(false)
    }
  }, [currentSessionId, loadSessionState])

  useEffect(() => {
    void loadWorkSessions('')
  }, [loadWorkSessions])

  useEffect(() => {
    localStorage.setItem(LEFT_WIDTH_STORAGE_KEY, String(leftWidth))
  }, [leftWidth])

  useEffect(() => {
    setMarkdownDraft(activeArtifact?.content || '')
  }, [activeArtifact?.artifact_id, activeArtifact?.content])

  const persistSessionState = useCallback(async (overrides?: Partial<WorkSessionState>) => {
    if (!currentSessionId) return
    setSaveStatus('saving')
    try {
      await workService.updateSession(currentSessionId, {
        title: overrides?.title ?? sessionTitle,
        artifacts: overrides?.artifacts ?? artifacts,
        active_artifact_id: overrides?.active_artifact_id ?? activeArtifactId,
        ui_state: overrides?.ui_state ?? {
          right_tab: activeTab,
          left_width: leftWidth,
          selection,
        },
      })
      setSessions((prev) =>
        prev.map((item) => (
          item.session_id === currentSessionId
            ? { ...item, title: overrides?.title ?? sessionTitle, updated_at: new Date().toISOString() }
            : item
        ))
      )
      setSaveStatus('saved')
      setServiceStatus('ok')
      setServiceStatusText(t(K.page.work.statusReady))
    } catch (error) {
      console.error('[WorkPage] failed to persist state', error)
      setSaveStatus('saved')
      setServiceStatus('degraded')
      setServiceStatusText(t(K.page.work.statusSaveFailed))
    }
  }, [currentSessionId, sessionTitle, artifacts, activeArtifactId, activeTab, leftWidth, selection])

  const applyArtifactPatch = useCallback((patch?: Record<string, any>) => {
    if (!patch || typeof patch !== 'object') return
    const patchArtifactId = String(patch.artifact_id || activeArtifactId || 'artifact-md-1')
    const patchContent = String(patch.content || '')
    const nextArtifacts = [...artifacts]
    const foundIndex = nextArtifacts.findIndex((item) => item.artifact_id === patchArtifactId)
    const historyEntry = patch.history_entry && typeof patch.history_entry === 'object'
      ? patch.history_entry
      : {
          id: `edit-${Date.now()}`,
          created_at: new Date().toISOString(),
          actor: 'assistant',
          summary: t(K.page.work.assistantPatchSummary),
          operation: 'replace',
          version: Number(patch.version || 1),
        }

    if (foundIndex === -1) {
      nextArtifacts.push({
        artifact_id: patchArtifactId,
        type: 'markdown',
        title: String(patch.title || t(K.page.work.markdownArtifact)),
        content: patchContent,
        version: Number(patch.version || 1),
        history: [historyEntry],
      })
    } else {
      const target = nextArtifacts[foundIndex]
      nextArtifacts[foundIndex] = {
        ...target,
        title: String(patch.title || target.title),
        content: patchContent,
        version: Number(patch.version || (target.version + 1)),
        history: [...(target.history || []), historyEntry],
      }
    }

    setArtifacts(nextArtifacts)
    setActiveArtifactId(patchArtifactId)
    void persistSessionState({
      artifacts: nextArtifacts,
      active_artifact_id: patchArtifactId,
    })
  }, [artifacts, activeArtifactId, persistSessionState])

  const { isConnected, connect, sendMessage } = useWebSocket({
    sessionId: currentSessionId,
    autoConnect: false,
    onMessage: useCallback((msg: WebSocketMessage) => {
      const messageId = String(msg.message_id || msg.messageId || `msg-${Date.now()}`)
      if (msg.type === 'run.started') {
        return
      }
      if (msg.type === 'message.start') {
        setIsStreaming(true)
        setStreamingMessage('')
        return
      }
      if (msg.type === 'message.delta') {
        const delta = String(msg.delta || msg.content || '')
        setStreamingMessage((prev) => prev + delta)
        return
      }
      if (msg.type === 'message.end') {
        const finalContent = String(msg.content || streamingMessage || '')
        setIsStreaming(false)
        setStreamingMessage('')
        setAwaitingReply(false)
        setMessages((prev) => [
          ...prev,
          {
            id: messageId,
            role: 'assistant',
            content: finalContent,
            timestamp: new Date().toISOString(),
            metadata: msg.metadata as Record<string, unknown> | undefined,
          },
        ])
        applyArtifactPatch(msg.artifact_patch as Record<string, any> | undefined)
        return
      }
      if (msg.type === 'message.cancelled') {
        setIsStreaming(false)
        setStreamingMessage('')
        setAwaitingReply(false)
        return
      }
      if (msg.type === 'message.error' || msg.type === 'error') {
        setIsStreaming(false)
        setStreamingMessage('')
        setAwaitingReply(false)
        toast.error(String(msg.content || t(K.page.work.toastGenerationFailed)))
      }
    }, [applyArtifactPatch, streamingMessage]),
    onError: useCallback(() => {
      setIsStreaming(false)
      setStreamingMessage('')
      setAwaitingReply(false)
      setServiceStatus('degraded')
      setServiceStatusText(t(K.page.work.statusConnectionInterrupted))
    }, []),
    onDisconnect: useCallback(() => {
      setIsStreaming(false)
      setStreamingMessage('')
      setAwaitingReply(false)
    }, []),
  })

  useEffect(() => {
    if (currentSessionId) {
      connect()
    }
  }, [currentSessionId, connect])

  useEffect(() => {
    if (!awaitingReply) return
    const timer = window.setTimeout(() => {
      setIsStreaming(false)
      setStreamingMessage('')
      setAwaitingReply(false)
      toast.warning(t(K.page.work.statusConnectionInterrupted))
    }, 120000)
    return () => {
      window.clearTimeout(timer)
    }
  }, [awaitingReply, t])

  const loadModelsForProvider = useCallback(async (targetProvider: string) => {
    try {
      const modelsResp = await providersApi.getProviderModels(targetProvider)
      const loadedModels = Array.isArray(modelsResp?.models)
        ? modelsResp.models.map((m: any) => m.id || m.name || m.label).filter(Boolean)
        : []
      setModels(loadedModels)

      if (loadedModels.length > 0 && !loadedModels.includes(model)) {
        setModel(loadedModels[0])
      }
    } catch (error) {
      console.error(`[WorkPage] failed to load models for ${targetProvider}`, error)
      try {
        const installedResp = await systemService.listModelsApiModelsListGet()
        const providerModels = installedResp.models
          .filter((m: any) => m.provider === targetProvider)
          .map((m: any) => m.name)
        setModels(providerModels.length > 0 ? providerModels : [])

        if (providerModels.length > 0 && !providerModels.includes(model)) {
          setModel(providerModels[0])
        }
      } catch (installedError) {
        console.error('[WorkPage] failed to load installed models', installedError)
        setModels([])
        setModel('')
      }
    }
  }, [model])

  const loadProvidersAndModels = useCallback(async () => {
    try {
      try {
        await providersApi.getProvidersStatus()
      } catch (statusError) {
        console.warn('[WorkPage] failed to read provider status', statusError)
      }

      const providersResp = await systemService.listProvidersApiProvidersGet()
      if (!Array.isArray(providersResp.local) || !Array.isArray(providersResp.cloud)) {
        throw new Error('Invalid providers response: expected { local: [], cloud: [] }')
      }

      const filteredProviders =
        mode === 'local'
          ? providersResp.local.map((p: any) => p.id).filter(Boolean)
          : providersResp.cloud.map((p: any) => p.id).filter(Boolean)

      setProviders(filteredProviders)

      if (provider && filteredProviders.includes(provider)) {
        await loadModelsForProvider(provider)
      } else if (filteredProviders.length > 0) {
        const firstProvider = filteredProviders[0]
        setProvider(firstProvider)
        await loadModelsForProvider(firstProvider)
      } else {
        setProvider('')
        setModels([])
        setModel('')
      }
    } catch (error) {
      console.error('[WorkPage] failed to load providers/models', error)
      setProviders([])
      setModels([])
      setProvider('')
      setModel('')
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode])

  useEffect(() => {
    void loadProvidersAndModels()
  }, [mode, loadProvidersAndModels])

  const handleNewSession = useCallback(async () => {
    try {
      const created = await workService.createSession()
      setSessions((prev) => [
        {
          session_id: created.session_id,
          title: created.title,
          updated_at: created.updated_at,
          created_at: created.created_at,
        },
        ...prev,
      ])
      await loadSessionState(created.session_id)
      toast.success(t(K.page.work.toastSessionCreated))
    } catch (error) {
      console.error('[WorkPage] failed to create session', error)
      toast.error(t(K.page.work.toastCreateSessionFailed))
    }
  }, [loadSessionState])

  const handleSessionSwitch = useCallback(async (session: WorkSessionListItem | null) => {
    if (!session) return
    await loadSessionState(session.session_id)
  }, [loadSessionState])

  const handleRenameSession = useCallback(async () => {
    await persistSessionState({ title: sessionTitle })
    toast.success(t(K.page.work.toastSessionRenamed))
  }, [persistSessionState, sessionTitle])

  const handleSendMessage = useCallback(async (text: string) => {
    if (!text.trim()) return
    if (!isConnected) {
      toast.warning(t(K.page.work.toastWsDisconnected))
      return
    }
    if (isStreaming || awaitingReply) {
      toast.info(t(K.page.work.toastWaitForReply))
      return
    }

    const userMessage: ChatMessageType = {
      id: `msg-${Date.now()}`,
      role: 'user',
      content: text,
      timestamp: new Date().toISOString(),
    }
    setMessages((prev) => [...prev, userMessage])
    setAwaitingReply(true)
    setInputValue('')

    const sent = sendMessage(text, {
      model_type: mode,
      provider,
      model,
      work_mode: true,
      work_session_id: currentSessionId,
      active_artifact_id: activeArtifactId,
      selection,
    })
    if (!sent) {
      setAwaitingReply(false)
      toast.error(t(K.page.work.toastSendFailed))
      return
    }
    await persistSessionState()
  }, [isConnected, isStreaming, awaitingReply, sendMessage, mode, provider, model, currentSessionId, activeArtifactId, selection, persistSessionState])

  const handleApplyDraft = useCallback(async () => {
    if (!activeArtifact) return
    const nextVersion = activeArtifact.version + 1
    const nextArtifacts = artifacts.map((item) => (
      item.artifact_id === activeArtifact.artifact_id
        ? {
            ...item,
            content: markdownDraft,
            version: nextVersion,
            history: [
              ...(item.history || []),
              {
                id: `edit-${Date.now()}`,
                created_at: new Date().toISOString(),
                actor: 'user',
                summary: t(K.page.work.inlineEditSummary),
                operation: 'replace',
                version: nextVersion,
              },
            ],
          }
        : item
    ))
    setArtifacts(nextArtifacts)
    setEditMode(false)
    await persistSessionState({ artifacts: nextArtifacts })
    toast.success(t(K.page.work.toastArtifactUpdated))
  }, [activeArtifact, artifacts, markdownDraft, persistSessionState])

  const handleExportMarkdown = useCallback(() => {
    if (!activeArtifact) return
    const blob = new Blob([activeArtifact.content || ''], { type: 'text/markdown;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    const safeTitle = (activeArtifact.title || 'work-artifact').replace(/[^\w\-]+/g, '-').toLowerCase()
    a.href = url
    a.download = `${safeTitle || 'work-artifact'}.md`
    a.click()
    URL.revokeObjectURL(url)
  }, [activeArtifact])

  const onResizeMouseDown = useCallback((event: ReactMouseEvent) => {
    event.preventDefault()
    resizeStateRef.current = { startX: event.clientX, startWidth: leftWidth }
  }, [leftWidth])

  useEffect(() => {
    const onMove = (event: MouseEvent) => {
      if (!resizeStateRef.current || isMobile) return
      const delta = event.clientX - resizeStateRef.current.startX
      const nextWidth = clamp(resizeStateRef.current.startWidth + delta, MIN_LEFT_WIDTH, MAX_LEFT_WIDTH)
      setLeftWidth(nextWidth)
    }
    const onUp = () => {
      if (!resizeStateRef.current) return
      resizeStateRef.current = null
      void persistSessionState({
        ui_state: {
          right_tab: activeTab,
          left_width: leftWidth,
          selection,
        },
      })
    }
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
    return () => {
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseup', onUp)
    }
  }, [isMobile, persistSessionState, activeTab, leftWidth, selection])

  return (
      <Paper
        sx={{
          display: 'flex',
          flexDirection: 'column',
          height: '100%',
          minHeight: 0,
          overflow: 'hidden',
          borderRadius: 2,
          boxShadow: 2,
          bgcolor: 'background.paper',
          '& .custom-scroller': HIDE_SCROLLBAR_SX,
        }}
      >
        <Box
          sx={{
          px: 2,
          py: 1.5,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 1,
          flexWrap: 'wrap',
        }}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Chip size="small" label={t(K.page.work.workModeBadge)} color="primary" variant="outlined" />
          <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
            {t(K.page.work.workModeTitle)}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {t(K.page.work.workModeDesc)}
          </Typography>
          </Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
          <Tooltip title={isConnected ? t(K.page.work.connected) : t(K.page.work.disconnected)}>
            <Box
              sx={{
                width: 10,
                height: 10,
                borderRadius: '50%',
                bgcolor: isConnected ? 'success.main' : 'warning.main',
              }}
            />
          </Tooltip>
          <Tooltip title={serviceStatusText}>
            <Typography variant="caption" color="text.secondary">
              {serviceStatus === 'ok' ? t(K.page.work.statusServiceReady) : t(K.page.work.statusServiceDegraded)}
            </Typography>
          </Tooltip>
          <Typography variant="caption" color="text.secondary">
            {saveStatus === 'saving' ? t(K.page.work.autoSaving) : t(K.page.work.autoSaved)}
          </Typography>
          </Box>
        </Box>

      <Divider />

      <Box
        sx={{
          px: 2,
          py: 1.25,
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          gap: 1.25,
        }}
      >
        <Typography variant="h6" sx={{ minWidth: 60, fontWeight: 700 }}>{t(K.page.work.session)}</Typography>
        <TextField
          size="small"
          label={t(K.page.work.sessionName)}
          value={sessionTitle}
          onChange={(event) => setSessionTitle(event.target.value)}
          sx={{ minWidth: 220, flexShrink: 0 }}
        />
        <Autocomplete
          size="small"
          options={sessions}
          getOptionLabel={(option) => option.title || option.session_id}
          value={sessions.find((item) => item.session_id === currentSessionId) || null}
          onChange={(_, value) => { void handleSessionSwitch(value) }}
          inputValue={sessionQuery}
          onInputChange={(_, value) => {
            setSessionQuery(value)
            void loadWorkSessions(value)
          }}
          renderInput={(params) => <TextField {...params} label={t(K.page.work.sessionSwitcher)} />}
          sx={{ minWidth: 280, flex: 1, maxWidth: 520 }}
        />
        <Button variant="outlined" onClick={handleNewSession}>{t(K.page.work.new)}</Button>
        <Button variant="outlined" onClick={handleRenameSession} startIcon={<SaveIcon />}>{t(K.page.work.rename)}</Button>
        <Button variant="outlined" onClick={handleExportMarkdown} startIcon={<DownloadIcon />}>{t(K.page.work.export)}</Button>
        {isMobile && (
          <Button
            variant="outlined"
            onClick={() => setMobileCanvasCollapsed((prev) => !prev)}
            startIcon={mobileCanvasCollapsed ? <VisibilityIcon /> : <EditIcon />}
          >
            {mobileCanvasCollapsed ? t(K.page.work.showCanvas) : t(K.page.work.hideCanvas)}
          </Button>
        )}
        <IconButton size="small"><MoreIcon /></IconButton>
      </Box>

      <Divider />
      <Box sx={{ px: 2, py: 0.5, overflowX: 'auto', ...HIDE_SCROLLBAR_SX }}>
        <ModelSelectionBar
          mode={mode}
          provider={provider}
          model={model}
          providers={providers}
          models={models}
          onModeChange={(newMode) => {
            setMode(newMode)
          }}
          onProviderChange={(newProvider) => {
            setProvider(newProvider)
            void loadModelsForProvider(newProvider)
          }}
          onModelChange={(newModel) => {
            setModel(newModel)
          }}
          onEmpty={() => {
            setInputValue('')
          }}
          disabled={loadingSession}
        />
      </Box>

      <Divider />

      <Box sx={{ display: 'flex', flex: 1, minHeight: 0, overflow: 'hidden', bgcolor: 'background.default' }}>
        <Box
          sx={{
            width: isMobile ? '100%' : `${leftWidth}px`,
            minWidth: 0,
            display: mobileCanvasCollapsed && isMobile ? 'flex' : 'flex',
            flexDirection: 'column',
            minHeight: 0,
            bgcolor: 'action.hover',
          }}
        >
          <Box sx={{ p: 1, flex: 1, minHeight: 0, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
            {messages.length === 0 && (
              <Box sx={{ px: 1.5, py: 1.25, borderRadius: 1, bgcolor: 'background.paper', mb: 1, border: '1px solid', borderColor: 'divider' }}>
                <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>{t(K.page.work.leftEmptyTitle)}</Typography>
                <Typography variant="body2" color="text.secondary">
                  {t(K.page.work.leftEmptyDesc)}
                </Typography>
              </Box>
            )}
            <Box sx={{ flex: 1, minHeight: 0 }}>
              <ChatShell
                messages={messages}
                loading={loadingSession}
                onSendMessage={(text) => { void handleSendMessage(text) }}
                showModelSelection={false}
                inputPlaceholder={t(K.page.work.chatInputPlaceholder)}
                emptyDescriptionText={t(K.page.work.leftEmptyDesc)}
                streamingMessage={streamingMessage}
                isStreaming={isStreaming}
                awaitingReply={awaitingReply}
                inputValue={inputValue}
                onInputChange={setInputValue}
              />
            </Box>
          </Box>
        </Box>

        {!isMobile && (
          <Box
            onMouseDown={onResizeMouseDown}
            sx={{
              width: 6,
              cursor: 'col-resize',
              alignSelf: 'stretch',
              bgcolor: 'divider',
              transition: 'background-color 120ms ease',
              '&:hover': { bgcolor: 'primary.main' },
            }}
          />
        )}

        {(!isMobile || !mobileCanvasCollapsed) && (
          <Box sx={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', borderLeft: '1px solid', borderColor: 'divider', bgcolor: 'background.paper' }}>
            <Box sx={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
              <Tabs
                value={activeTab}
                onChange={(_, value: WorkRightTab) => {
                  setActiveTab(value)
                  void persistSessionState({
                    ui_state: {
                      right_tab: value,
                      left_width: leftWidth,
                      selection,
                    },
                  })
                }}
                variant="scrollable"
              >
                <Tab value="preview" label={t(K.page.work.tabContent)} />
                <Tab value="outline" label={t(K.page.work.tabStructure)} />
                <Tab value="edits" label={t(K.page.work.tabEdits)} sx={{ color: 'text.secondary' }} />
                <Tab value="assets" label={t(K.page.work.tabAssets)} sx={{ color: 'text.secondary' }} />
              </Tabs>
              <Divider />

              <Box sx={{ p: 2, flex: 1, minHeight: 0, overflow: 'auto', ...HIDE_SCROLLBAR_SX }}>
                {activeTab === 'preview' && (
                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5, minHeight: '100%' }}>
                    <Box sx={{ display: 'flex', gap: 1, alignItems: 'center', flexWrap: 'wrap' }}>
                      <Typography variant="subtitle2">
                        {`${activeArtifact?.title || t(K.page.work.markdownArtifact)} · ${editMode ? t(K.page.work.edit) : t(K.page.work.preview)}`}
                      </Typography>
                      <Button size="small" variant="outlined" onClick={() => setEditMode((prev) => !prev)}>
                        {editMode ? t(K.page.work.previewMode) : t(K.page.work.editMode)}
                      </Button>
                      {editMode && (
                        <Button size="small" variant="contained" onClick={() => { void handleApplyDraft() }}>
                          {t(K.page.work.saveEdit)}
                        </Button>
                      )}
                    </Box>
                    {editMode ? (
                      <TextField
                        multiline
                        minRows={20}
                        value={markdownDraft}
                        onChange={(event) => setMarkdownDraft(event.target.value)}
                        onSelect={(event) => {
                          const target = event.target as HTMLTextAreaElement
                          const nextSelection = {
                            start: target.selectionStart,
                            end: target.selectionEnd,
                            text: target.value.slice(target.selectionStart, target.selectionEnd),
                          }
                          setSelection(nextSelection)
                        }}
                        sx={{ flex: 1, ...HIDE_SCROLLBAR_SX }}
                      />
                    ) : (
                      <Box
                        sx={{
                          p: 2,
                          border: '1px solid',
                          borderColor: 'divider',
                          borderRadius: 1,
                          minHeight: 320,
                          overflow: 'auto',
                          ...HIDE_SCROLLBAR_SX,
                        }}
                      >
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                          {activeArtifact?.content || t(K.page.work.rightEmptyMarkdown)}
                        </ReactMarkdown>
                      </Box>
                    )}
                  </Box>
                )}

                {activeTab === 'outline' && (
                  <List dense>
                    {outline.length === 0 && <ListItem><ListItemText primary={t(K.page.work.noHeadings)} /></ListItem>}
                    {outline.map((item, index) => (
                      <ListItem key={`${item.title}-${index}`} sx={{ pl: item.level * 2 }}>
                        <ListItemText primary={item.title} secondary={`H${item.level}`} />
                      </ListItem>
                    ))}
                  </List>
                )}

                {activeTab === 'edits' && (
                  <List dense>
                    {(activeArtifact?.history || []).slice().reverse().map((entry) => (
                      <ListItem key={entry.id}>
                        <ListItemText
                          primary={`${entry.summary} · v${entry.version}`}
                          secondary={`${entry.actor} · ${entry.created_at}`}
                        />
                      </ListItem>
                    ))}
                    {(!activeArtifact?.history || activeArtifact.history.length === 0) && (
                      <ListItem>
                        <ListItemText primary={t(K.page.work.noEdits)} />
                      </ListItem>
                    )}
                  </List>
                )}

                {activeTab === 'assets' && (
                  <Box sx={{ p: 1.5, borderRadius: 1, bgcolor: 'action.hover' }}>
                    <Typography variant="body2" color="text.secondary">
                      {t(K.page.work.assetsDesc)}
                    </Typography>
                  </Box>
                )}
              </Box>
            </Box>
          </Box>
        )}
      </Box>
    </Paper>
  )
}
