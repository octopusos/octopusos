import { Alert, Box, Link, Typography } from '@/ui'
import { useTextTranslation } from '@/ui/text'
import type { FeatureKey } from '@services/feature.operations'
import type { WriteGateReason } from '@/ui/guards/useWriteGate'

type WriteGateBannerProps = {
  featureKey: FeatureKey
  reason: WriteGateReason
  missingOperations?: string[]
  compact?: boolean
}

export function WriteGateBanner({ featureKey, reason, missingOperations = [], compact = false }: WriteGateBannerProps) {
  const { t } = useTextTranslation()

  if (reason === 'OK') return null

  const isModeReadOnly = reason === 'MODE_READONLY'
  const titleKey = isModeReadOnly ? 'gate.write.modeReadOnly.title' : 'gate.write.contractUnavailable.title'
  const descKey = isModeReadOnly ? 'gate.write.modeReadOnly.desc' : 'gate.write.contractUnavailable.desc'

  return (
    <Alert severity={isModeReadOnly ? 'info' : 'warning'} sx={{ mb: compact ? 1 : 2 }}>
      <Typography sx={{ fontWeight: 600 }}>{t(titleKey)}</Typography>
      <Typography variant="body2">{t(descKey, { featureKey })}</Typography>
      {!isModeReadOnly && missingOperations.length > 0 && !compact && (
        <Box sx={{ mt: 1 }}>
          {missingOperations.slice(0, 4).map((op) => (
            <Typography key={op} variant="caption" sx={{ display: 'block' }}>
              {op}
            </Typography>
          ))}
        </Box>
      )}
      <Link href="/docs/contracts" target="_blank" rel="noreferrer" sx={{ display: 'inline-block', mt: 0.5 }}>
        {t('gate.write.learnMore')}
      </Link>
    </Alert>
  )
}
