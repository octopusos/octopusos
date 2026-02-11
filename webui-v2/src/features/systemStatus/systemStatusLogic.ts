import type { WriteAccessResult } from '@/platform/auth/writeAccess'
import type { SystemStatusCode, SystemStatusItem } from './systemStatusTypes'

type SystemStatusDebug = {
  mode?: string
  hasAdminToken?: boolean
  source?: string
  contractConfigWriteAllowed?: boolean
  contractMissingOperations?: string[]
}

export type BuildSystemStatusInput = {
  writeAccess: WriteAccessResult
  contractWriteAllowed: boolean
  contractMissingOperations: string[]
  hasAdminToken: boolean
  source: string
}

export type BuildSystemStatusResult = {
  isRestricted: boolean
  primary: SystemStatusItem | null
  items: SystemStatusItem[]
  debug: SystemStatusDebug
}

const SEVERITY_SCORE: Record<SystemStatusItem['severity'], number> = {
  error: 3,
  warning: 2,
  info: 1,
}

const CODE_PRIORITY: Record<SystemStatusCode, number> = {
  CONTRACT_OPERATION_UNAVAILABLE: 5,
  MODE_UNKNOWN: 4,
  WRITE_DISABLED: 3,
  REMOTE_NO_TOKEN: 2,
  LOCAL_LOCKED: 1,
}

function createItem(
  code: SystemStatusCode,
  severity: SystemStatusItem['severity'],
  labelKey: string,
  messageKey: string,
  details?: Record<string, unknown>
): SystemStatusItem {
  return { code, severity, labelKey, messageKey, details }
}

export function buildSystemStatus(input: BuildSystemStatusInput): BuildSystemStatusResult {
  const items: SystemStatusItem[] = []
  const { writeAccess, contractWriteAllowed, contractMissingOperations, hasAdminToken, source } = input

  if (writeAccess.reason === 'MODE_UNKNOWN') {
    items.push(
      createItem(
        'MODE_UNKNOWN',
        'warning',
        'systemStatus.chip.modeUnknown',
        'systemStatus.msg.modeUnknown'
      )
    )
  }

  if (writeAccess.reason === 'TOKEN_REQUIRED') {
    items.push(
      createItem(
        'REMOTE_NO_TOKEN',
        'warning',
        'systemStatus.chip.readOnly',
        'systemStatus.msg.remoteNoToken'
      )
    )
  }

  if (writeAccess.reason === 'MODE_READONLY') {
    items.push(
      createItem(
        'LOCAL_LOCKED',
        'info',
        'systemStatus.chip.readOnly',
        'systemStatus.msg.localLocked'
      )
    )
  }

  if (!writeAccess.canWrite) {
    items.push(
      createItem(
        'WRITE_DISABLED',
        'warning',
        'systemStatus.chip.readOnly',
        'systemStatus.msg.writeDisabled'
      )
    )
  }

  if (!contractWriteAllowed) {
    items.push(
      createItem(
        'CONTRACT_OPERATION_UNAVAILABLE',
        'warning',
        'systemStatus.chip.contractDenied',
        'systemStatus.msg.contractOpUnavailable',
        { missingOperations: contractMissingOperations }
      )
    )
  }

  const primary = [...items].sort((left, right) => {
    const bySeverity = SEVERITY_SCORE[right.severity] - SEVERITY_SCORE[left.severity]
    if (bySeverity !== 0) return bySeverity
    return CODE_PRIORITY[right.code] - CODE_PRIORITY[left.code]
  })[0] || null

  return {
    isRestricted: items.length > 0,
    primary,
    items,
    debug: {
      mode: writeAccess.mode || undefined,
      hasAdminToken,
      source,
      contractConfigWriteAllowed: contractWriteAllowed,
      contractMissingOperations: contractMissingOperations,
    },
  }
}
