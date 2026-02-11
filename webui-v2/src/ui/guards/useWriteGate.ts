import { useMemo } from 'react'
import { useIsReadOnly } from './useIsReadOnly'
import { useContractCapabilities } from './useContractCapabilities'
import type { FeatureKey } from '@services/feature.operations'

export type WriteGateReason = 'OK' | 'MODE_READONLY' | 'CONTRACT_UNAVAILABLE'

export type WriteGateResult = {
  allowed: boolean
  reason: WriteGateReason
  missingOperations: string[]
}

export function useWriteGate(featureKey: FeatureKey): WriteGateResult {
  const isReadOnlyByMode = useIsReadOnly()
  const { canWriteFeature } = useContractCapabilities()

  return useMemo(() => {
    if (isReadOnlyByMode) {
      return {
        allowed: false,
        reason: 'MODE_READONLY' as const,
        missingOperations: [],
      }
    }

    const featureAvailability = canWriteFeature(featureKey)
    if (!featureAvailability.allowed) {
      return {
        allowed: false,
        reason: 'CONTRACT_UNAVAILABLE' as const,
        missingOperations: featureAvailability.missingOperations,
      }
    }

    return {
      allowed: true,
      reason: 'OK' as const,
      missingOperations: [],
    }
  }, [canWriteFeature, featureKey, isReadOnlyByMode])
}

