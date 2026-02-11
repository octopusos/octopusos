/**
 * ChatShell - Chat Interface Pattern Component
 *
 * 🏛️ Pattern Component for chat/messaging interfaces
 * - Provides message list + input bar layout
 * - Supports loading states and empty states
 * - Built-in skeleton screen
 * - No-Interaction friendly (disabled mode)
 */

import React, { useRef, useState, useMemo, useEffect, useCallback } from 'react'
import { Box, Paper, Chip, useTheme, FormControl, InputLabel, Select, MenuItem } from '@mui/material'
import { Virtuoso, type VirtuosoHandle } from 'react-virtuoso'
import { ChatMessage } from './ChatMessage'
import { ChatInputBar } from './ChatInputBar'
import { ChatSkeleton } from './ChatSkeleton'
import { ModelSelectionBar, type ModelSelectionBarProps } from './ModelSelectionBar'
import { EmptyState, type EmptyStateProps } from '@/ui'
import { MessageIcon, ArrowDownIcon } from '@/ui/icons'
import { t, K } from '@/ui/text'

export interface ChatMessageType {
  id: string
  role: 'user' | 'assistant' | 'system' | 'tool'
  content: string
  timestamp: string
  avatar?: string
  metadata?: {
    model?: string
    tokens?: number
    status?: string
    revision?: number
    parent_message_id?: string
    [key: string]: unknown
  }
}

export interface ChatShellProps {
  messages: ChatMessageType[]
  loading?: boolean
  onSendMessage?: (text: string) => boolean | void | Promise<boolean | void>
  inputPlaceholder?: string
  disabled?: boolean
  emptyState?: EmptyStateProps
  emptyDescriptionText?: string

  // Model Selection Bar (optional)
  modelSelection?: Omit<ModelSelectionBarProps, 'disabled'>
  showModelSelection?: boolean

  // Chat Context Bar (above message bubbles)
  contextSelection?: {
    conversationMode: 'chat' | 'discussion' | 'plan' | 'development' | 'task'
    executionPhase: 'planning' | 'execution'
    onConversationModeChange?: (mode: 'chat' | 'discussion' | 'plan' | 'development' | 'task') => void
    onExecutionPhaseChange?: (phase: 'planning' | 'execution') => void
  }

  // Streaming message (displayed as temporary assistant message)
  streamingMessage?: string
  isStreaming?: boolean
  awaitingReply?: boolean
  awaitingReplyMessage?: string

  // 🎯 受控输入支持（用于 Draft 保护）
  inputValue?: string
  onInputChange?: (value: string) => void
  onStopStreaming?: () => void
  onEditMessage?: (message: ChatMessageType) => void
  suppressAutoFollow?: boolean
  onInputFocusChange?: (focused: boolean) => void
}

/**
 * ChatShell Pattern Component
 *
 * Layout:
 * - Messages Container (scrollable)
 * - Model Selection Bar (optional)
 * - Input Bar (fixed at bottom)
 *
 * States:
 * - loading: shows ChatSkeleton
 * - empty: shows EmptyState
 * - normal: shows messages + model selection + input
 */
export function ChatShell({
  messages,
  loading = false,
  onSendMessage,
  inputPlaceholder = 'Type a message...',
  disabled = false,
  emptyState,
  emptyDescriptionText,
  modelSelection,
  showModelSelection = true,
  contextSelection,
  streamingMessage = '',
  isStreaming = false,
  awaitingReply = false,
  awaitingReplyMessage = t(K.page.chat.replyPending),
  inputValue,
  onInputChange,
  onStopStreaming,
  onEditMessage,
  suppressAutoFollow = false,
  onInputFocusChange,
}: ChatShellProps) {
  const theme = useTheme()
  const octopusos = theme.palette.octopusos

  // ===================================
  // Virtuoso Ref & Scroll State
  // ===================================
  const virtuosoRef = useRef<VirtuosoHandle>(null)
  const scrollerRef = useRef<HTMLDivElement | null>(null)
  const [isAtBottom, setIsAtBottom] = useState(true)
  const [unseenMessageCount, setUnseenMessageCount] = useState(0)
  const [waitingDotCount, setWaitingDotCount] = useState(0)
  const previousMessageCountRef = useRef(messages.length)
  const atBottomRef = useRef(true)
  // ✅ P1 优化：移除 atBottom 状态，Virtuoso 的 followOutput 函数会接收 isAtBottom 参数

  useEffect(() => {
    if (!awaitingReply || isStreaming) {
      setWaitingDotCount(0)
      return
    }

    const timer = window.setInterval(() => {
      setWaitingDotCount((prev) => (prev + 1) % 4)
    }, 450)

    return () => {
      window.clearInterval(timer)
    }
  }, [awaitingReply, isStreaming])

  useEffect(() => {
    const previous = previousMessageCountRef.current
    const next = messages.length
    if (next > previous && !isAtBottom) {
      setUnseenMessageCount((count) => count + (next - previous))
    }
    previousMessageCountRef.current = next
  }, [messages.length, isAtBottom])

  useEffect(() => {
    if (isAtBottom && unseenMessageCount > 0) {
      setUnseenMessageCount(0)
    }
  }, [isAtBottom, unseenMessageCount])

  // Prepare display messages (combine messages + streaming message)
  const displayMessages = useMemo(() => {
    const allMessages = [...messages]

    if (awaitingReply && !streamingMessage) {
      allMessages.push({
        id: 'awaiting-reply',
        role: 'assistant' as const,
        content: `${awaitingReplyMessage}${'.'.repeat(waitingDotCount)}`,
        timestamp: new Date().toISOString(),
      })
    }

    // Add streaming message as temporary assistant message
    if (isStreaming && streamingMessage) {
      allMessages.push({
        id: 'streaming',
        role: 'assistant' as const,
        content: streamingMessage,
        timestamp: new Date().toISOString(),
      })
    }

    return allMessages
  }, [messages, awaitingReply, awaitingReplyMessage, waitingDotCount, isStreaming, streamingMessage])

  const bindScrollerRef = useCallback((
    forwardedRef: React.ForwardedRef<HTMLDivElement>,
    node: HTMLDivElement | null
  ) => {
    scrollerRef.current = node
    if (typeof forwardedRef === 'function') {
      forwardedRef(node)
      return
    }
    if (forwardedRef) {
      forwardedRef.current = node
    }
  }, [])

  const scrollerComponent = useMemo(
    () =>
      React.forwardRef<HTMLDivElement, React.HTMLProps<HTMLDivElement>>((props, ref) => (
        <div
          {...props}
          ref={(node) => bindScrollerRef(ref, node)}
          data-testid="chat-scroller"
          style={{
            ...(props.style || {}),
            scrollbarWidth: 'none', // Firefox
            overscrollBehavior: 'contain',
          }}
          className="custom-scroller"
        />
      )),
    [bindScrollerRef]
  )

  const footerComponent = useMemo(() => () => <Box sx={{ height: 16 }} />, [])

  const virtuosoComponents = useMemo(
    () => ({
      Footer: footerComponent,
      Scroller: scrollerComponent,
    }),
    [footerComponent, scrollerComponent]
  )

  // Scroll to bottom using real scroller first, fallback to Virtuoso API.
  const scrollToBottom = () => {
    setUnseenMessageCount(0)
    const scroller = scrollerRef.current
    if (scroller) {
      const top = scroller.scrollHeight
      scroller.scrollTo({ top, behavior: 'auto' })
      window.requestAnimationFrame(() => {
        scroller.scrollTo({ top: scroller.scrollHeight, behavior: 'auto' })
      })
      return
    }

    virtuosoRef.current?.scrollToIndex({
      index: displayMessages.length - 1,
      behavior: 'auto',
      align: 'end',
    })
  }

  // ✅ P1 优化：移除手动滚动的 useEffect，避免与 Virtuoso followOutput 冲突
  // followOutput 函数会自动处理滚动逻辑

  // ===================================
  // Loading State
  // ===================================
  // ✅ Only show skeleton when truly loading, not when streaming
  if (loading && !isStreaming) {
    return <ChatSkeleton />
  }

  // ===================================
  // Empty State
  // ===================================
  if (messages.length === 0 && emptyState) {
    return <EmptyState {...emptyState} />
  }

  const showExecutionPhaseControl = contextSelection
    ? contextSelection.conversationMode === 'development' || contextSelection.conversationMode === 'task'
    : false

  // ===================================
  // Normal State - Messages + Input
  // ===================================
  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        position: 'relative',
        gap: 0,
      }}
    >
      {/* Context Bar: Chat Mode / Execution Phase */}
      {contextSelection && (
        <Paper
          sx={{
            px: 2,
            py: 1.5,
            mb: 1.5,
            borderRadius: 1,
            display: 'flex',
            gap: 2,
            alignItems: 'center',
            flexWrap: 'wrap',
          }}
        >
          <FormControl size="small" sx={{ minWidth: 180 }}>
            <InputLabel>{t('page.chat.conversationMode')}</InputLabel>
            <Select
              value={contextSelection.conversationMode}
              label={t('page.chat.conversationMode')}
              onChange={(e) =>
                contextSelection.onConversationModeChange?.(
                  e.target.value as 'chat' | 'discussion' | 'plan' | 'development' | 'task'
                )
              }
              disabled={disabled}
            >
              <MenuItem value="chat">{t('page.chat.chatModeChat')}</MenuItem>
              <MenuItem value="discussion">{t('page.chat.chatModeDiscussion')}</MenuItem>
              <MenuItem value="plan">{t('page.chat.chatModePlan')}</MenuItem>
              <MenuItem value="development">{t('page.chat.chatModeDevelopment')}</MenuItem>
              <MenuItem value="task">{t('page.chat.chatModeTask')}</MenuItem>
            </Select>
          </FormControl>

          {showExecutionPhaseControl && (
            <FormControl size="small" sx={{ minWidth: 170 }}>
              <InputLabel>{t('page.chat.executionPhase')}</InputLabel>
              <Select
                value={contextSelection.executionPhase}
                label={t('page.chat.executionPhase')}
                onChange={(e) =>
                  contextSelection.onExecutionPhaseChange?.(
                    e.target.value as 'planning' | 'execution'
                  )
                }
                disabled={disabled}
              >
                <MenuItem value="planning">{t('page.chat.phasePlanning')}</MenuItem>
                <MenuItem value="execution">
                  {t('page.chat.phaseExecution')}
                </MenuItem>
              </Select>
            </FormControl>
          )}
        </Paper>
      )}

      {/* Messages Container */}
      <Paper
        sx={{
          flex: 1,
          mb: '12px',
          overflow: 'hidden',
          // ✅ 使用 OctopusOS tokens 适配暗色主题
          bgcolor: octopusos?.bg?.section || 'background.default',
          borderRadius: 1,
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        {displayMessages.length === 0 ? (
          <Box
            sx={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              flex: 1,
              gap: 1.5,
              p: 3,
            }}
          >
            <MessageIcon
              sx={{
                fontSize: 64,
                color: 'text.secondary',
                opacity: 0.3,
              }}
            />
            <Box
              sx={{
                textAlign: 'center',
                color: 'text.secondary',
                opacity: 0.7,
                fontSize: '0.875rem',
              }}
            >
              {emptyDescriptionText ?? t(K.page.chat.emptyDescription)}
            </Box>
          </Box>
        ) : (
          <Virtuoso
            ref={virtuosoRef}
            data={displayMessages}
            followOutput={(isAtBottom) => {
              // ✅ P1 优化：动态控制滚动行为
              // 只有在底部时才自动跟随新消息滚动，避免打断用户查看历史消息
              return isAtBottom && !suppressAutoFollow ? 'auto' : false
            }}
            atBottomStateChange={(bottom) => {
              if (atBottomRef.current === bottom) return
              atBottomRef.current = bottom
              setIsAtBottom(bottom)
            }}
            itemContent={(_index, message) => (
              <Box sx={{ px: 3, py: 1 }}>
                <ChatMessage key={message.id} message={message} onEdit={onEditMessage} />
              </Box>
            )}
            components={virtuosoComponents}
            style={{
              height: '100%',
              width: '100%',
            }}
          />
        )}
      </Paper>

      {/* Floating new-message chip */}
      {!isAtBottom && unseenMessageCount > 0 && (
        <Chip
          icon={<ArrowDownIcon />}
          label={`${t(K.page.chat.newMessages)} (${unseenMessageCount})`}
          color="primary"
          clickable
          onClick={scrollToBottom}
          data-testid="chat-unread-chip"
          sx={{
            position: 'absolute',
            bottom: showModelSelection && modelSelection ? 92 : 20,
            right: 24,
            zIndex: 10,
            boxShadow: theme.shadows[4],
          }}
        />
      )}

      {/* Model Selection Bar */}
      {showModelSelection && modelSelection && (
        <ModelSelectionBar {...modelSelection} disabled={disabled} />
      )}

      {/* Input Bar */}
      <ChatInputBar
        onSend={onSendMessage}
        placeholder={inputPlaceholder}
        disabled={disabled}
        value={inputValue}
        onChange={onInputChange}
        isStreaming={isStreaming}
        onStop={onStopStreaming}
        onFocusChange={onInputFocusChange}
      />
    </Box>
  )
}
