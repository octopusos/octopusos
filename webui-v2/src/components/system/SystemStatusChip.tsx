import { useMemo, useState } from 'react'
import {
  Box,
  Chip,
  IconButton,
  Popover,
  Tooltip,
  Typography,
  List,
  ListItem,
  ListItemText,
} from '@mui/material'
import { CopyIcon, ExtensionIcon, InfoIcon, LockIcon, WarningIcon } from '@/ui/icons'
import { useTextTranslation } from '@/ui/text'
import { useSystemStatus } from '@/features/systemStatus/useSystemStatus'
import type { SystemStatusItem } from '@/features/systemStatus/systemStatusTypes'

function getItemIcon(item: SystemStatusItem) {
  if (item.code === 'CONTRACT_OPERATION_UNAVAILABLE') return <ExtensionIcon fontSize="small" />
  if (item.code === 'MODE_UNKNOWN') return <WarningIcon fontSize="small" />
  return <LockIcon fontSize="small" />
}

function getChipColor(item: SystemStatusItem): 'default' | 'warning' {
  if (item.code === 'CONTRACT_OPERATION_UNAVAILABLE' || item.code === 'MODE_UNKNOWN') {
    return 'warning'
  }
  return 'default'
}

function getSuggestionKeys(item?: SystemStatusItem | null): string[] {
  if (!item) return []
  if (item.code === 'MODE_UNKNOWN') return ['systemStatus.suggest.checkModeApi']
  if (item.code === 'REMOTE_NO_TOKEN') return ['systemStatus.suggest.checkToken']
  if (item.code === 'CONTRACT_OPERATION_UNAVAILABLE') {
    return ['systemStatus.suggest.checkContractSnapshot', 'systemStatus.suggest.checkMissingOps']
  }
  return ['systemStatus.suggest.checkDaemon']
}

export function SystemStatusChip() {
  const { t } = useTextTranslation()
  const { isRestricted, primary, items, debug } = useSystemStatus()
  const [anchorEl, setAnchorEl] = useState<HTMLElement | null>(null)
  const displayLabelKey = isRestricted && primary ? primary.labelKey : 'systemStatus.chip.normal'
  const displayMessageKey = isRestricted && primary ? primary.messageKey : 'systemStatus.msg.normal'
  const suggestionKeys = getSuggestionKeys(primary)

  const copyPayload = useMemo(() => {
    const missingOps = debug.contractMissingOperations || []
    const statusLines = isRestricted
      ? items.map((item) => `- ${item.code}: ${t(item.messageKey)}`)
      : [`- NORMAL: ${t('systemStatus.msg.normal')}`]
    return [
      `[${t('systemStatus.title')}]`,
      ...statusLines,
      '',
      `Mode: ${debug.mode || '-'}`,
      `Admin token: ${debug.hasAdminToken ? 'yes' : 'no'}`,
      `Contract Config API: ${debug.contractConfigWriteAllowed ? 'allowed' : 'denied'}`,
      `FEATURE_CONFIG_WRITE: ${debug.contractConfigWriteAllowed ? 'true' : 'false'}`,
      `Missing ops count: ${missingOps.length}`,
      ...(missingOps.length > 0 ? missingOps.map((op) => `- ${op}`) : []),
      `Source: ${debug.source || '-'}`,
    ].join('\n')
  }, [
    debug.contractMissingOperations,
    debug.contractConfigWriteAllowed,
    debug.hasAdminToken,
    debug.mode,
    debug.source,
    isRestricted,
    items,
    t,
  ])

  return (
    <>
      <Tooltip title={t(displayMessageKey)}>
        <Chip
          size="small"
          icon={isRestricted && primary ? getItemIcon(primary) : <InfoIcon fontSize="small" />}
          label={t(displayLabelKey)}
          color={isRestricted && primary ? getChipColor(primary) : 'default'}
          variant="outlined"
          onClick={(event) => setAnchorEl(event.currentTarget)}
          sx={{
            height: 26,
            '& .MuiChip-label': {
              px: 1,
            },
          }}
        />
      </Tooltip>

      <Popover
        open={Boolean(anchorEl)}
        anchorEl={anchorEl}
        onClose={() => setAnchorEl(null)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
        transformOrigin={{ vertical: 'top', horizontal: 'right' }}
        PaperProps={{
          sx: {
            width: 360,
            maxWidth: '90vw',
            p: 1.5,
            border: '1px solid',
            borderColor: 'divider',
          },
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 1 }}>
          <Typography variant="subtitle2">{t('systemStatus.title')}</Typography>
          <Tooltip title={t('common.copy')}>
            <IconButton
              size="small"
              onClick={async () => {
                await navigator.clipboard.writeText(copyPayload)
              }}
            >
              <CopyIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </Box>

        <List dense sx={{ py: 0.5 }}>
          {isRestricted ? (
            items.map((item) => (
              <ListItem key={`${item.code}-${item.messageKey}`} sx={{ px: 0.5 }}>
                <Box sx={{ mr: 1, mt: 0.25, color: 'text.secondary' }}>{getItemIcon(item)}</Box>
                <ListItemText primary={t(item.messageKey)} primaryTypographyProps={{ variant: 'body2' }} />
              </ListItem>
            ))
          ) : (
            <ListItem sx={{ px: 0.5 }}>
              <Box sx={{ mr: 1, mt: 0.25, color: 'text.secondary' }}>
                <InfoIcon fontSize="small" />
              </Box>
              <ListItemText
                primary={t('systemStatus.msg.normal')}
                primaryTypographyProps={{ variant: 'body2' }}
              />
            </ListItem>
          )}
        </List>

        <Box sx={{ mt: 1.25, pt: 1.25, borderTop: '1px solid', borderColor: 'divider' }}>
          <Box
            sx={{
              p: 1,
              borderRadius: 1,
              bgcolor: 'action.hover',
              border: '1px solid',
              borderColor: 'divider',
            }}
          >
            {(() => {
              const missingOps = debug.contractMissingOperations || []
              return (
                <>
                  <Typography
                    variant="caption"
                    color="text.secondary"
                    sx={{ display: 'block', fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace' }}
                  >
                    FEATURE_CONFIG_WRITE: {debug.contractConfigWriteAllowed ? 'true' : 'false'}
                  </Typography>
                  <Typography
                    variant="caption"
                    color="text.secondary"
                    sx={{ display: 'block', fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace' }}
                  >
                    Missing ops: {missingOps.length}
                  </Typography>
                  {missingOps.length > 0 && (
                    <Typography
                      variant="caption"
                      color="text.secondary"
                      sx={{
                        display: 'block',
                        whiteSpace: 'pre-wrap',
                        fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
                      }}
                    >
                      {missingOps.join(', ')}
                    </Typography>
                  )}
                  <Typography
                    variant="caption"
                    color="text.secondary"
                    sx={{ display: 'block', mt: 0.5, fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace' }}
                  >
                    Mode: {debug.mode || '-'}
                  </Typography>
                  <Typography
                    variant="caption"
                    color="text.secondary"
                    sx={{ display: 'block', fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace' }}
                  >
                    Admin token: {debug.hasAdminToken ? 'yes' : 'no'}
                  </Typography>
                  <Typography
                    variant="caption"
                    color="text.secondary"
                    sx={{ display: 'block', fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace' }}
                  >
                    Contract Config API: {debug.contractConfigWriteAllowed ? t('common.yes') : t('common.no')}
                  </Typography>
                  {debug.source && (
                    <Typography
                      variant="caption"
                      color="text.secondary"
                      sx={{ display: 'block', fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace' }}
                    >
                      Source: {debug.source}
                    </Typography>
                  )}
                </>
              )
            })()}
          </Box>

          <Box
            sx={{
              mt: 1,
              p: 1,
              borderRadius: 1,
              bgcolor: 'background.default',
              border: '1px dashed',
              borderColor: 'divider',
            }}
          >
            {isRestricted ? (
              <>
                <Typography variant="caption" color="text.secondary" sx={{ display: 'block', fontWeight: 600 }}>
                  {t('systemStatus.suggest.title')}
                </Typography>
                {suggestionKeys.map((key, index) => (
                  <Typography
                    key={key}
                    variant="caption"
                    color="text.secondary"
                    sx={{ display: 'block', mt: index === 0 ? 0.25 : 0 }}
                  >
                    - {t(key)}
                  </Typography>
                ))}
              </>
            ) : (
              <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
                {t('systemStatus.note.normal')}
              </Typography>
            )}
          </Box>
        </Box>
      </Popover>
    </>
  )
}
