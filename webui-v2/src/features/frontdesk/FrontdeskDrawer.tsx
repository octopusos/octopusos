import { useEffect, useMemo, useRef, useState } from 'react'
import {
  Box,
  Chip,
  Divider,
  Drawer,
  IconButton,
  Stack,
  Typography,
  Button,
} from '@mui/material'
import { CloseIcon } from '@/ui/icons'
import { ChatInputBar, ChatMessage } from '@/ui/chat'
import { useFrontdeskChatStore } from './frontdeskChatStore'
import { useNavigate } from 'react-router-dom'
import { K, useText } from '@/ui/text'
import { frontdeskService } from '@/services'
import { replaceFirstMentionInDraft } from './mentionReplace'

export function FrontdeskDrawer() {
  const { t } = useText()
  const {
    isOpen,
    close,
    draft,
    setDraft,
    messages,
    sendMessage,
    connectionStatus,
  } = useFrontdeskChatStore()

  const navigate = useNavigate()
  const contentRef = useRef<HTMLDivElement | null>(null)
  const [agentDirectory, setAgentDirectory] = useState<Array<{ agent_id: string; title: string; lifecycle: string }>>([])
  const statusConfig = {
    idle: { label: t(K.component.frontdesk.idle), color: 'default' as const },
    loading: { label: t(K.component.frontdesk.loading), color: 'info' as const },
    ready: { label: t(K.component.frontdesk.apiReady), color: 'success' as const },
    error: { label: t(K.component.frontdesk.apiError), color: 'error' as const },
  }
  const quickActions = [
    { label: '/overview', value: '/overview' },
    { label: '@James todo', value: '@James todo' },
    { label: '@James status', value: '@James status' },
    { label: '@James blockers', value: '@James blockers' },
    { label: t(K.component.frontdesk.openReviewQueue), value: '/dispatch-review' },
  ]

  useEffect(() => {
    if (!isOpen || !contentRef.current) return
    contentRef.current.scrollTop = contentRef.current.scrollHeight
  }, [isOpen, messages.length])

  useEffect(() => {
    if (!isOpen) return
    let mounted = true
    void frontdeskService
      .getAgents(undefined, 50)
      .then(response => {
        if (!mounted) return
        setAgentDirectory((response?.agents || []).map(agent => ({
          agent_id: agent.agent_id,
          title: agent.title,
          lifecycle: agent.lifecycle,
        })))
      })
      .catch(() => {
        if (!mounted) return
        setAgentDirectory([])
      })
    return () => {
      mounted = false
    }
  }, [isOpen])

  const status = statusConfig[connectionStatus]

  const displayMessages = useMemo(() => {
    return messages.map(message => ({
      id: message.id,
      role: message.role,
      content: message.text,
      timestamp: message.created_at,
      meta: message.meta,
    }))
  }, [messages])

  return (
    <Drawer
      anchor="right"
      open={isOpen}
      onClose={close}
      disableRestoreFocus={false}
      disableEnforceFocus={false}
      disableAutoFocus
      sx={{
        zIndex: (theme) => theme.zIndex.modal + 2,
        '& .MuiDrawer-paper': {
          width: 480,
          maxWidth: '100%',
          display: 'flex',
          flexDirection: 'column',
        },
      }}
    >
      <Box sx={{ p: 3, pb: 2, display: 'flex', alignItems: 'center', gap: 2 }}>
        <Box sx={{ flex: 1 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Typography variant="h6" fontWeight="bold">
              {t(K.component.frontdesk.chatTitle)}
            </Typography>
            <Box
              component="span"
              sx={{
                fontSize: '0.75rem',
                fontWeight: 600,
                px: 1,
                py: 0.25,
                borderRadius: 1,
                bgcolor: 'action.hover',
                color: 'text.secondary',
              }}
            >
              🧭 Frontdesk
            </Box>
          </Box>
          <Typography variant="body2" color="text.secondary">
            {t(K.component.frontdesk.chatSubtitle)}
          </Typography>
        </Box>
        <Chip label={status.label} color={status.color} size="small" />
        <IconButton onClick={close} size="small">
          <CloseIcon />
        </IconButton>
      </Box>

      <Divider />

      <Box
        ref={contentRef}
        sx={{
          flex: 1,
          overflowY: 'auto',
          px: 3,
          py: 2,
          display: 'flex',
          flexDirection: 'column',
          gap: 2,
        }}
      >
        {displayMessages.length === 0 ? (
          <Typography variant="body2" color="text.secondary">
            {t(K.component.frontdesk.noMessages)}
          </Typography>
        ) : (
          displayMessages.map(message => {
            const proposalId = message.meta?.proposal_id as string | undefined
            const jobId = message.meta?.job_id as string | undefined
            const autoScheduled = Boolean(message.meta?.auto_execute_scheduled)
            return (
              <Box key={message.id} sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                <ChatMessage message={message} />
                {(proposalId || jobId || autoScheduled) && (
                  <Stack direction="row" spacing={1}>
                    {proposalId && (
                      <Button
                        size="small"
                        variant="outlined"
                        onClick={() => navigate(`/dispatch-review?proposal=${proposalId}`)}
                      >
                        查看提案
                      </Button>
                    )}
                    {proposalId && (
                      <Button
                        size="small"
                        variant="contained"
                        onClick={() => navigate(`/dispatch-review?proposal=${proposalId}`)}
                      >
                        去审批
                      </Button>
                    )}
                    {jobId && (
                      <Button
                        size="small"
                        variant="outlined"
                        onClick={() => navigate(`/dispatch-review?proposal=${proposalId ?? ''}`)}
                      >
                        查看执行状态
                      </Button>
                    )}
                    {autoScheduled && !jobId && (
                      <Button
                        size="small"
                        variant="outlined"
                        onClick={() => navigate(`/dispatch-review?proposal=${proposalId ?? ''}`)}
                      >
                        已安排执行
                      </Button>
                    )}
                  </Stack>
                )}
                {message.meta?.reason_code && (
                  <Typography variant="caption" color="text.secondary">
                    agent_resolution: {String(message.meta?.agent_resolution || 'none')} | reason_code: {String(message.meta?.reason_code)}
                  </Typography>
                )}
                {(message.meta?.reason_code === 'AGENT_NOT_FOUND' || message.meta?.reason_code === 'AGENT_PARTIAL_FOUND') &&
                  Array.isArray(message.meta?.agent_suggestions) &&
                  message.meta.agent_suggestions.length > 0 && (
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
                      <Typography variant="caption" color="text.secondary">
                        Did you mean:
                      </Typography>
                      <Stack direction="row" spacing={1} flexWrap="wrap">
                        {message.meta.agent_suggestions.map((item: any) => (
                          <Chip
                            key={String(item.agent_id)}
                            size="small"
                            variant="outlined"
                            label={`@${String(item.agent_id)}`}
                            onClick={() =>
                              setDraft(
                                replaceFirstMentionInDraft(
                                  draft,
                                  String(item.agent_id),
                                  Array.isArray(message.meta?.raw_mentions) ? message.meta.raw_mentions : [],
                                ),
                              )
                            }
                          />
                        ))}
                      </Stack>
                    </Box>
                  )}
              </Box>
            )
          })
        )}
      </Box>

      <Divider />

      <Box sx={{ p: 3, pt: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
        <ChatInputBar
          value={draft}
          onChange={setDraft}
          onSend={sendMessage}
          placeholder={t(K.component.frontdesk.inputPlaceholder)}
        />
        <Stack direction="row" spacing={1} flexWrap="wrap">
          {quickActions.map(action => (
            <Chip
              key={action.value}
              label={action.label}
              size="small"
              variant="outlined"
              onClick={() => {
                if (action.value.startsWith('/dispatch-review')) {
                  navigate(action.value)
                  return
                }
                setDraft(action.value)
              }}
            />
          ))}
        </Stack>
        {agentDirectory.length > 0 && (
          <Box>
            <Typography variant="caption" color="text.secondary">
              Agent Directory ({agentDirectory.length})
            </Typography>
            <Stack direction="row" spacing={1} flexWrap="wrap" sx={{ mt: 1 }}>
              {agentDirectory.slice(0, 12).map(agent => (
                <Chip
                  key={agent.agent_id}
                  size="small"
                  variant="outlined"
                  label={`${agent.title} · ${agent.lifecycle}`}
                  onClick={() => setDraft(`@${agent.agent_id} status`)}
                />
              ))}
            </Stack>
          </Box>
        )}
      </Box>
    </Drawer>
  )
}
