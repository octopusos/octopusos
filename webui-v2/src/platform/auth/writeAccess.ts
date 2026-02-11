import { getToken } from './adminToken'

const RUNTIME_MODE_CACHE_KEY = 'octopusos_runtime_mode'

export type WriteAccessReason = 'OK' | 'MODE_READONLY' | 'TOKEN_REQUIRED' | 'MODE_UNKNOWN'

export type WriteAccessResult = {
  canWrite: boolean
  reason: WriteAccessReason
  mode: string | null
}

export function normalizeMode(mode: string | null | undefined): string {
  return String(mode || '').trim().toLowerCase()
}

export function setCachedRuntimeMode(mode: string | null | undefined): void {
  try {
    if (!mode) {
      localStorage.removeItem(RUNTIME_MODE_CACHE_KEY)
      return
    }
    localStorage.setItem(RUNTIME_MODE_CACHE_KEY, String(mode))
  } catch {
    // ignore storage failures
  }
}

export function getCachedRuntimeMode(): string | null {
  try {
    return localStorage.getItem(RUNTIME_MODE_CACHE_KEY)
  } catch {
    return null
  }
}

export function evaluateWriteAccess(mode: string | null | undefined, token: string | null): WriteAccessResult {
  const normalized = normalizeMode(mode)
  const hasToken = Boolean(token && token.trim().length > 0)

  if (normalized === 'local_open' || normalized === 'localopen' || normalized === 'open') {
    return { canWrite: true, reason: 'OK', mode: normalized }
  }
  if (normalized === 'local_locked' || normalized === 'locallocked' || normalized === 'locked') {
    return { canWrite: false, reason: 'MODE_READONLY', mode: normalized }
  }
  if (
    normalized === 'remote_exposed' ||
    normalized === 'remoteexposed' ||
    normalized === 'exposed' ||
    normalized === 'remote'
  ) {
    if (!hasToken) return { canWrite: false, reason: 'TOKEN_REQUIRED', mode: normalized }
    return { canWrite: true, reason: 'OK', mode: normalized }
  }
  return { canWrite: false, reason: 'MODE_UNKNOWN', mode: normalized || null }
}

export async function resolveWriteAccess(): Promise<WriteAccessResult> {
  const token = getToken()
  const cachedMode = getCachedRuntimeMode()
  if (cachedMode) return evaluateWriteAccess(cachedMode, token)

  try {
    const res = await fetch('/api/mode/stats', { credentials: 'include' })
    if (!res.ok) {
      return evaluateWriteAccess(null, token)
    }
    const body = await res.json()
    const mode = body?.stats?.current_mode || body?.current_mode || null
    setCachedRuntimeMode(mode)
    return evaluateWriteAccess(mode, token)
  } catch {
    return evaluateWriteAccess(null, token)
  }
}
