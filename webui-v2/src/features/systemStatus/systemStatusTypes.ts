export type SystemStatusSeverity = 'info' | 'warning' | 'error'

export type SystemStatusCode =
  | 'MODE_UNKNOWN'
  | 'WRITE_DISABLED'
  | 'REMOTE_NO_TOKEN'
  | 'LOCAL_LOCKED'
  | 'CONTRACT_OPERATION_UNAVAILABLE'

export interface SystemStatusItem {
  code: SystemStatusCode
  severity: SystemStatusSeverity
  labelKey: string
  messageKey: string
  details?: Record<string, unknown>
}
