import { useMemo } from 'react'
import { getMissingOperations, isOperationAvailable } from '@services/contract.capabilities.gen'
import { FEATURE_OPERATIONS, type FeatureKey } from '@services/feature.operations'

export function useContractCapabilities() {
  return useMemo(() => {
    const canWriteOperation = (method: string, path: string): boolean =>
      isOperationAvailable(method, path)

    const canWriteFeature = (featureKey: FeatureKey): { allowed: boolean; missingOperations: string[] } => {
      const operations = FEATURE_OPERATIONS[featureKey] || []
      const missingOperations = getMissingOperations(operations)
      return {
        allowed: missingOperations.length === 0,
        missingOperations,
      }
    }

    return {
      canWriteOperation,
      canWriteFeature,
    }
  }, [])
}

