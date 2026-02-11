import type { ReactNode } from 'react'
import { useIsReadOnly } from './useIsReadOnly'
import { useWriteGate } from './useWriteGate'
import type { FeatureKey } from '@services/feature.operations'

export function WriteActionGuard({ children, featureKey }: { children: ReactNode; featureKey?: FeatureKey }) {
  const isReadOnly = useIsReadOnly()
  const gate = featureKey ? useWriteGate(featureKey) : null
  if (isReadOnly) return null
  if (gate && !gate.allowed) return null
  return <>{children}</>
}
