import { useCallback, useReducer } from 'react'
import { callSessionReducer, initialCallState, type CallAction } from './callSessionReducer'

export function useCallStateMachine() {
  const [state, dispatch] = useReducer(callSessionReducer, initialCallState)

  const send = useCallback((action: CallAction): void => {
    dispatch(action)
  }, [])

  return { state, send }
}
