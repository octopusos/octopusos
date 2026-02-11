import { useMemo } from 'react'
import { useWriteGate } from './useWriteGate'
import type { FeatureKey } from '@services/feature.operations'

type Handler<T extends unknown[]> = (...args: T) => void

export function useWriteDisabledProps(featureKey: FeatureKey) {
  const gate = useWriteGate(featureKey)

  return useMemo(() => {
    const tooltipKey =
      gate.reason === 'MODE_READONLY'
        ? 'gate.write.modeReadOnly.title'
        : gate.reason === 'CONTRACT_UNAVAILABLE'
          ? 'gate.write.contractUnavailable.title'
          : ''

    const onClickGuarded =
      <T extends unknown[]>(handler: Handler<T>): Handler<T> =>
      (...args: T) => {
        if (!gate.allowed) return
        handler(...args)
      }

    return {
      disabled: !gate.allowed,
      tooltipKey,
      reason: gate.reason,
      missingOperations: gate.missingOperations,
      onClickGuarded,
    }
  }, [gate.allowed, gate.missingOperations, gate.reason])
}

