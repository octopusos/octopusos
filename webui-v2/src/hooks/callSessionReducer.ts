export type CallState =
  | 'idle'
  | 'connecting'
  | 'in_call_listening'
  | 'in_call_speaking'
  | 'in_call_hold'
  | 'ending'
  | 'ended'
  | 'error'

export interface CallStateData {
  state: CallState
  errorMessage?: string
}

export type CallAction =
  | { type: 'START_CONNECTING' }
  | { type: 'WS_READY' }
  | { type: 'SERVER_STATUS'; status: string }
  | { type: 'END_REQUEST' }
  | { type: 'END_CONFIRMED' }
  | { type: 'FAIL'; message: string }
  | { type: 'RESET' }

export const initialCallState: CallStateData = {
  state: 'idle',
}

export function callSessionReducer(current: CallStateData, action: CallAction): CallStateData {
  switch (action.type) {
    case 'START_CONNECTING':
      return { state: 'connecting' }
    case 'WS_READY':
      return { state: 'in_call_listening' }
    case 'SERVER_STATUS':
      if (action.status === 'speaking') {
        return { state: 'in_call_speaking' }
      }
      if (action.status === 'listening') {
        return { state: 'in_call_listening' }
      }
      if (action.status === 'hold') {
        return { state: 'in_call_hold' }
      }
      if (action.status === 'ended') {
        return { state: 'ended' }
      }
      return current
    case 'END_REQUEST':
      return { state: 'ending' }
    case 'END_CONFIRMED':
      return { state: 'ended' }
    case 'FAIL':
      return { state: 'error', errorMessage: action.message }
    case 'RESET':
      return initialCallState
    default:
      return current
  }
}
