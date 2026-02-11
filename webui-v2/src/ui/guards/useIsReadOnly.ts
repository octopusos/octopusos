import { useEffect, useMemo, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { systemService } from '@services'
import { getToken } from '@/platform/auth/adminToken'
import { evaluateWriteAccess, setCachedRuntimeMode } from '@/platform/auth/writeAccess'

const READONLY_ROUTES = new Set([
  '/execution-plans',
  '/governance',
  '/audit-log',
])

export function useIsReadOnly(): boolean {
  const location = useLocation()
  const [runtimeMode, setRuntimeMode] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    const detectMode = async () => {
      try {
        const response = await systemService.getStatsApiModeStatsGet() as any
        const fromStats = response?.stats?.current_mode
        const fromRoot = response?.current_mode
        const detected = fromStats || fromRoot || null
        if (!cancelled) {
          setRuntimeMode(detected)
          setCachedRuntimeMode(detected)
        }
      } catch {
        if (!cancelled) setRuntimeMode(null)
      }
    }

    void detectMode()
    return () => {
      cancelled = true
    }
  }, [])

  return useMemo(() => {
    const writeAccess = evaluateWriteAccess(runtimeMode, getToken())
    if (writeAccess.reason !== 'MODE_UNKNOWN') return !writeAccess.canWrite

    // Fallback (temporary compatibility): keep governance-sensitive routes readonly.
    if (READONLY_ROUTES.has(location.pathname)) return true

    // Unknown mode defaults to conservative readonly.
    return true
  }, [location.pathname, runtimeMode])
}
