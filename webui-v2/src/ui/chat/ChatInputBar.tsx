/**
 * ChatInputBar - Message Input Component
 *
 * Provides:
 * - Multi-line text input
 * - Attach button (disabled in No-Interaction mode)
 * - Send button
 * - Enter to send (Shift+Enter for new line)
 *
 * 🎯 支持受控和非受控两种模式：
 * - 非受控模式：组件内部管理状态（默认）
 * - 受控模式：通过 value/onChange 外部控制（用于 Draft 保护）
 */

import { useEffect, useMemo, useRef, useState } from 'react'
import { Box, TextField, IconButton } from '@mui/material'
import { Send as SendIcon, AttachFile as AttachFileIcon, Stop as StopIcon } from '@mui/icons-material'
import { t, K } from '@/ui/text'
import { clearDraft, makeDraftKey, readDraft, writeDraft } from './draftStorage'

interface ChatInputBarProps {
  onSend?: (text: string) => boolean | void | Promise<boolean | void>
  placeholder?: string
  disabled?: boolean
  // 🎯 受控模式支持（用于 Draft 保护）
  value?: string
  onChange?: (value: string) => void
  draftScope?: string
  isStreaming?: boolean
  onStop?: () => void
  onFocusChange?: (focused: boolean) => void
}

export function ChatInputBar({
  onSend,
  placeholder = 'Type a message...',
  disabled = false,
  value: controlledValue,
  onChange: controlledOnChange,
  draftScope,
  isStreaming = false,
  onStop,
  onFocusChange,
}: ChatInputBarProps) {
  // 非受控模式的内部状态
  const [internalText, setInternalText] = useState('')

  // 判断是否为受控模式
  const isControlled = controlledValue !== undefined
  const text = isControlled ? controlledValue : internalText
  const setText = isControlled ? controlledOnChange! : setInternalText
  const draftKey = useMemo(() => makeDraftKey(draftScope), [draftScope])
  const restoredRef = useRef(false)
  const persistTimerRef = useRef<number | null>(null)
  const latestTextRef = useRef(text)

  latestTextRef.current = text

  useEffect(() => {
    if (restoredRef.current) return
    restoredRef.current = true
    const cached = readDraft(draftKey)
    if (!text && cached) setText(cached)
    // text/setText only for first restore; keep dependency list stable on key changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [draftKey])

  useEffect(() => {
    if (persistTimerRef.current) {
      window.clearTimeout(persistTimerRef.current)
    }
    persistTimerRef.current = window.setTimeout(() => {
      writeDraft(draftKey, text || '')
    }, 250)

    return () => {
      if (persistTimerRef.current) window.clearTimeout(persistTimerRef.current)
    }
  }, [draftKey, text])

  useEffect(() => {
    return () => {
      writeDraft(draftKey, latestTextRef.current || '')
    }
  }, [draftKey])

  const handleSend = async () => {
    if (!text.trim() || !onSend) return
    const result = await onSend(text.trim())
    // Only clear input after confirmed successful send.
    if (result === false) return
    setText('')
    clearDraft(draftKey)
  }

  const handleInputChange = (nextValue: string) => {
    setText(nextValue)
    writeDraft(draftKey, nextValue)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      void handleSend()
    }
  }

  return (
    <Box sx={{ display: 'flex', gap: 1, alignItems: 'flex-end' }}>
      {/* Attach Button */}
      <IconButton disabled={disabled} size="large" color="default">
        <AttachFileIcon />
      </IconButton>

      {/* Text Input */}
      <TextField
        fullWidth
        multiline
        maxRows={4}
        value={text}
        onChange={(e) => handleInputChange(e.target.value)}
        onKeyDown={handleKeyDown}
        onFocus={() => onFocusChange?.(true)}
        onBlur={() => onFocusChange?.(false)}
        placeholder={placeholder}
        disabled={disabled}
        variant="outlined"
        inputProps={{
          'data-testid': 'chat-input',
        }}
        sx={{
          '& .MuiOutlinedInput-root': {
            borderRadius: 1,
          },
        }}
      />

      {/* Send Button */}
      {isStreaming && onStop ? (
        <IconButton
          color="warning"
          disabled={disabled}
          onClick={onStop}
          size="large"
          title={t(K.common.stop)}
        >
          <StopIcon />
        </IconButton>
      ) : (
        <IconButton
          color="primary"
          disabled={disabled || !text.trim()}
          onClick={() => {
            void handleSend()
          }}
          size="large"
        >
          <SendIcon />
        </IconButton>
      )}
    </Box>
  )
}
