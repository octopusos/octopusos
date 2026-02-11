/**
 * InstallUrlDialog - Install extension from URL
 *
 * Features:
 * - URL input with validation
 * - Optional SHA256 hash verification
 * - Installation progress tracking
 * - Success/error handling
 */

import { useState } from 'react'
import { DialogForm } from '@/ui/interaction'
import { Box, Typography, TextField, LinearProgress, Alert } from '@/ui'
import { K, useTextTranslation } from '@/ui/text'
import { toast } from '@/ui/feedback'
import { useWriteGate } from '@/ui/guards/useWriteGate'
import { WriteGateBanner } from '@/components/gates/WriteGateBanner'

interface InstallUrlDialogProps {
  open: boolean
  onClose: () => void
  onSuccess: () => void
}

export function InstallUrlDialog({ open, onClose, onSuccess: _onSuccess }: InstallUrlDialogProps) {
  const { t } = useTextTranslation()
  const writeGate = useWriteGate('FEATURE_EXTENSIONS_INSTALL')

  const [url, setUrl] = useState('')
  const [sha256, setSha256] = useState('')
  const [installing, setInstalling] = useState(false)
  const [progress, setProgress] = useState(0)
  const [currentStep, setCurrentStep] = useState<string>('')
  const [error, setError] = useState<string>('')

  const handleSubmit = async () => {
    if (!writeGate.allowed) {
      toast.info(t('gate.write.contractUnavailable.title'))
      return
    }
    if (!url.trim()) {
      toast.error(t('page.extensions.urlRequired'))
      return
    }

    // Basic URL validation
    try {
      new URL(url)
    } catch {
      toast.error('Invalid URL format')
      return
    }

    setInstalling(true)
    setError('')
    setProgress(0)
    setCurrentStep('Starting installation...')

    try {
      throw new Error('Extension URL install is not available in current API contract')

    } catch (err: any) {
      console.error('Install failed:', err)
      setInstalling(false)
      const errorMsg = err?.message || 'Installation failed'
      setError(errorMsg)
      toast.error(t('page.extensions.installFailed') + ': ' + errorMsg)
    }
  }

  const handleCloseDialog = () => {
    if (!installing) {
      setUrl('')
      setSha256('')
      setProgress(0)
      setCurrentStep('')
      setError('')
      onClose()
    }
  }

  return (
    <DialogForm
      open={open}
      onClose={handleCloseDialog}
      title={t(K.page.extensions.installUrlDialogTitle)}
      submitText={t(K.common.install)}
      cancelText={t(K.common.cancel)}
      onSubmit={handleSubmit}
      loading={installing}
      submitDisabled={!url.trim() || installing || !writeGate.allowed}
      maxWidth="sm"
    >
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
        <WriteGateBanner
          featureKey="FEATURE_EXTENSIONS_INSTALL"
          reason={writeGate.reason}
          missingOperations={writeGate.missingOperations}
          compact
        />
        {/* Description */}
        <Typography variant="body2" color="text.secondary">
          {t(K.page.extensions.installUrlDialogDesc)}
        </Typography>

        {/* URL Input */}
        <TextField
          label={t(K.page.extensions.extensionUrl)}
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder={t(K.page.extensions.installUrlPlaceholder)}
          required
          fullWidth
          disabled={installing}
          autoFocus
        />

        {/* SHA256 Input (Optional) */}
        <TextField
          label={t(K.page.extensions.sha256Optional)}
          value={sha256}
          onChange={(e) => setSha256(e.target.value)}
          placeholder={t(K.page.extensions.installUrlChecksumPlaceholder)}
          fullWidth
          disabled={installing}
          helperText={t(K.page.extensions.installUrlChecksumHelper)}
        />

        {/* Progress */}
        {installing && (
          <Box sx={{ mt: 2 }}>
            <Typography variant="body2" color="text.secondary" gutterBottom>
              {currentStep || t(K.page.extensions.installing)}
            </Typography>
            <LinearProgress variant="determinate" value={progress} />
            <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5 }}>
              {progress}%
            </Typography>
          </Box>
        )}

        {/* Error */}
        {error && (
          <Alert
            severity="error"
            sx={{
              '& .MuiAlert-message': {
                width: '100%',
                wordBreak: 'break-word',
                cursor: 'pointer'
              }
            }}
            onClick={() => {
              navigator.clipboard.writeText(error)
              toast.success('Error copied to clipboard')
            }}
          >
            {error}
          </Alert>
        )}
      </Box>
    </DialogForm>
  )
}
