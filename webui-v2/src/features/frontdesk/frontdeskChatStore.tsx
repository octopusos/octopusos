import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react'
import { frontdeskService } from '@/services'

export type FrontdeskScope =
  | { type: 'global' }
  | { type: 'project'; project_id: string }

export type FrontdeskConnectionStatus = 'idle' | 'loading' | 'ready' | 'error'

export interface FrontdeskMessage {
  id: string
  role: 'user' | 'assistant' | 'system'
  text: string
  created_at: string
  evidence_refs?: string[]
  meta?: Record<string, any>
}

interface FrontdeskChatState {
  isOpen: boolean
  draft: string
  messages: FrontdeskMessage[]
  scope: FrontdeskScope
  connectionStatus: FrontdeskConnectionStatus
  lastSyncedAt: string | null
}

interface FrontdeskChatActions {
  open: () => void
  close: () => void
  setDraft: (text: string) => void
  sendMessage: (text: string) => Promise<void>
  hydrateFromLocalStorage: () => void
  persistToLocalStorage: () => void
  refreshHistory: (limit?: number) => Promise<void>
}

type FrontdeskChatContextValue = FrontdeskChatState & FrontdeskChatActions

const STORAGE_KEYS = {
  draft: 'frontdesk:draft:v1',
  messages: 'frontdesk:messages:v1',
  scope: 'frontdesk:scope:v1',
}

const MAX_MESSAGES = 50
const PERSIST_DELAY_MS = 300

const FrontdeskChatContext = createContext<FrontdeskChatContextValue | null>(null)

const defaultScope: FrontdeskScope = { type: 'global' }

const safeJsonParse = <T,>(value: string | null, fallback: T): T => {
  if (!value) return fallback
  try {
    return JSON.parse(value) as T
  } catch (error) {
    return fallback
  }
}

const generateLocalId = () => {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return `fdm_local_${crypto.randomUUID()}`
  }
  return `fdm_local_${Date.now()}_${Math.random().toString(16).slice(2)}`
}

const extractMentions = (text: string) => {
  const matches = Array.from(text.matchAll(/@([a-zA-Z0-9_]+)/g))
  const names = matches.map(match => match[1].toLowerCase())
  return Array.from(new Set(names))
}

export function FrontdeskChatProvider({ children }: { children: React.ReactNode }) {
  const [isOpen, setIsOpen] = useState(false)
  const [draft, setDraft] = useState('')
  const [messages, setMessages] = useState<FrontdeskMessage[]>([])
  const [scope, setScope] = useState<FrontdeskScope>(defaultScope)
  const [connectionStatus, setConnectionStatus] = useState<FrontdeskConnectionStatus>('idle')
  const [lastSyncedAt, setLastSyncedAt] = useState<string | null>(null)

  const persistTimerRef = useRef<number | null>(null)

  const hydrateFromLocalStorage = useCallback(() => {
    const storedDraft = safeJsonParse<string | null>(localStorage.getItem(STORAGE_KEYS.draft), null)
    const storedMessages = safeJsonParse<FrontdeskMessage[]>(localStorage.getItem(STORAGE_KEYS.messages), [])
    const storedScope = safeJsonParse<FrontdeskScope | null>(localStorage.getItem(STORAGE_KEYS.scope), null)

    if (storedDraft !== null) {
      setDraft(storedDraft)
    }

    if (storedMessages.length > 0) {
      setMessages(storedMessages)
    }

    if (storedScope) {
      setScope(storedScope)
    }
  }, [])

  const persistToLocalStorage = useCallback(() => {
    try {
      localStorage.setItem(STORAGE_KEYS.draft, JSON.stringify(draft))
      localStorage.setItem(STORAGE_KEYS.messages, JSON.stringify(messages.slice(-MAX_MESSAGES)))
      localStorage.setItem(STORAGE_KEYS.scope, JSON.stringify(scope))
    } catch (error) {
      console.warn('[Frontdesk] Failed to persist local state', error)
    }
  }, [draft, messages, scope])

  useEffect(() => {
    hydrateFromLocalStorage()
  }, [hydrateFromLocalStorage])

  useEffect(() => {
    if (persistTimerRef.current) {
      window.clearTimeout(persistTimerRef.current)
    }

    persistTimerRef.current = window.setTimeout(() => {
      persistToLocalStorage()
    }, PERSIST_DELAY_MS)

    return () => {
      if (persistTimerRef.current) {
        window.clearTimeout(persistTimerRef.current)
      }
    }
  }, [draft, messages, scope, persistToLocalStorage])

  const refreshHistory = useCallback(async (limit = MAX_MESSAGES) => {
    try {
      setConnectionStatus('loading')
      const response = await frontdeskService.getFrontdeskHistory(limit)
      if (response?.messages) {
        setMessages(response.messages)
      }
      setLastSyncedAt(new Date().toISOString())
      setConnectionStatus('ready')
    } catch (error) {
      console.error('[Frontdesk] Failed to load history', error)
      setConnectionStatus('error')
    }
  }, [])

  useEffect(() => {
    if (isOpen && messages.length === 0) {
      refreshHistory().catch(() => null)
    }
  }, [isOpen, messages.length, refreshHistory])

  const sendMessage = useCallback(async (text: string) => {
    const trimmed = text.trim()
    if (!trimmed) return

    const userMessage: FrontdeskMessage = {
      id: generateLocalId(),
      role: 'user',
      text: trimmed,
      created_at: new Date().toISOString(),
      evidence_refs: [],
    }

    setMessages(prev => [...prev, userMessage])
    setConnectionStatus('loading')

    try {
      const response = await frontdeskService.sendFrontdeskChat({
        text: trimmed,
        scope,
        mentions: extractMentions(trimmed),
      })

      const assistantMessage: FrontdeskMessage = {
        id: response.message_id,
        role: 'assistant',
        text: response.assistant_text,
        created_at: response.created_at || new Date().toISOString(),
        evidence_refs: response.evidence_refs || [],
        meta: response.meta || {},
      }

      setMessages(prev => [...prev, assistantMessage])
      setLastSyncedAt(response.created_at || new Date().toISOString())
      setConnectionStatus('ready')
    } catch (error) {
      console.error('[Frontdesk] Failed to send message', error)
      setConnectionStatus('error')
    }
  }, [scope])

  const value = useMemo<FrontdeskChatContextValue>(() => ({
    isOpen,
    draft,
    messages,
    scope,
    connectionStatus,
    lastSyncedAt,
    open: () => setIsOpen(true),
    close: () => setIsOpen(false),
    setDraft,
    sendMessage,
    hydrateFromLocalStorage,
    persistToLocalStorage,
    refreshHistory,
  }), [
    isOpen,
    draft,
    messages,
    scope,
    connectionStatus,
    lastSyncedAt,
    sendMessage,
    hydrateFromLocalStorage,
    persistToLocalStorage,
    refreshHistory,
  ])

  return (
    <FrontdeskChatContext.Provider value={value}>
      {children}
    </FrontdeskChatContext.Provider>
  )
}

export function useFrontdeskChatStore() {
  const context = useContext(FrontdeskChatContext)
  if (!context) {
    throw new Error('useFrontdeskChatStore must be used within FrontdeskChatProvider')
  }
  return context
}
