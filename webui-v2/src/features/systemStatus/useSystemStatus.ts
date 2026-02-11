import { useEffect, useMemo, useState } from 'react'
import { getToken } from '@/platform/auth/adminToken'
import {
  evaluateWriteAccess,
  getCachedRuntimeMode,
  resolveWriteAccess,
  type WriteAccessResult,
} from '@/platform/auth/writeAccess'
import { useWriteGate } from '@/ui/guards/useWriteGate'
import { buildSystemStatus, type BuildSystemStatusResult } from './systemStatusLogic'

export function useSystemStatus(): BuildSystemStatusResult {
  const cachedMode = getCachedRuntimeMode()
  const initialToken = getToken()
  const [source, setSource] = useState(cachedMode ? 'mode-cache' : 'mode-resolve')
  const [writeAccess, setWriteAccess] = useState<WriteAccessResult>(() =>
    evaluateWriteAccess(cachedMode, initialToken)
  )
  const writeGate = useWriteGate('FEATURE_CONFIG_WRITE')

  useEffect(() => {
    let cancelled = false

    const resolve = async () => {
      const next = await resolveWriteAccess()
      if (cancelled) return
      setWriteAccess(next)
      setSource('mode-api')
    }

    void resolve()
    return () => {
      cancelled = true
    }
  }, [])

  return useMemo(
    () =>
      buildSystemStatus({
        writeAccess,
        contractWriteAllowed: writeGate.allowed || writeGate.reason !== 'CONTRACT_UNAVAILABLE',
        contractMissingOperations: writeGate.missingOperations,
        hasAdminToken: Boolean(getToken()),
        source,
      }),
    [source, writeAccess, writeGate.allowed, writeGate.missingOperations, writeGate.reason]
  )
}
