/**
 * UploadExtensionDialog - Upload extension ZIP file
 *
 * Features:
 * - File upload with validation (.zip only)
 * - Installation progress tracking
 * - Success/error handling
 */

import { useState, useRef } from 'react'
import { DialogForm } from '@/ui/interaction'
import { Box, Typography, Button, LinearProgress, Alert } from '@/ui'
import { UploadIcon } from '@/ui/icons'
import { K, useTextTranslation } from '@/ui/text'
import { toast } from '@/ui/feedback'

interface UploadExtensionDialogProps {
  open: boolean
  onClose: () => void
  onSuccess: () => void
}

export function UploadExtensionDialog({ open, onClose, onSuccess: _onSuccess }: UploadExtensionDialogProps) {
  const { t } = useTextTranslation()
  const fileInputRef = useRef<HTMLInputElement>(null)

  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [installing] = useState(false)
  const [progress, setProgress] = useState(0)
  const [currentStep, setCurrentStep] = useState<string>('')
  const [error, setError] = useState<string>('')

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (file) {
      if (!file.name.endsWith('.zip')) {
        toast.error(t('page.extensions.uploadFailed') + ': Only .zip files are allowed')
        return
      }
      setSelectedFile(file)
      setError('')
    }
  }

  const handleSubmit = async () => {
    if (!selectedFile) {
      toast.error(t('page.extensions.selectFile'))
      return
    }

    setUploading(true)
    setError('')

    try {
      throw new Error('Extension upload install is not available in current API contract')

    } catch (err: any) {
      console.error('Upload failed:', err)
      setUploading(false)
      const errorMsg = err?.message || 'Upload failed'
      setError(errorMsg)
      toast.error(t('page.extensions.uploadFailed') + ': ' + errorMsg)
    }
  }

  const handleCloseDialog = () => {
    if (!uploading && !installing) {
      setSelectedFile(null)
      setProgress(0)
      setCurrentStep('')
      setError('')
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
      onClose()
    }
  }

  const isLoading = uploading || installing

  return (
    <DialogForm
      open={open}
      onClose={handleCloseDialog}
      title={t(K.page.extensions.uploadDialogTitle)}
      submitText={t(K.common.upload)}
      cancelText={t(K.common.cancel)}
      onSubmit={handleSubmit}
      loading={isLoading}
      submitDisabled={!selectedFile || isLoading}
      maxWidth="sm"
    >
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
        {/* Description */}
        <Typography variant="body2" color="text.secondary">
          {t(K.page.extensions.uploadDialogDesc)}
        </Typography>

        {/* File Input */}
        <Box>
          <input
            ref={fileInputRef}
            type="file"
            accept=".zip"
            onChange={handleFileSelect}
            style={{ display: 'none' }}
            id="extension-file-input"
          />
          <label htmlFor="extension-file-input">
            <Button
              variant="outlined"
              component="span"
              startIcon={<UploadIcon />}
              fullWidth
              disabled={isLoading}
            >
              {t(K.page.extensions.selectFile)}
            </Button>
          </label>
        </Box>

        {/* Selected File */}
        {selectedFile && (
          <Alert severity="info">
            {t(K.page.extensions.fileSelected)}: {selectedFile.name} ({Math.round(selectedFile.size / 1024)} KB)
          </Alert>
        )}

        {/* Progress */}
        {(uploading || installing) && (
          <Box sx={{ mt: 2 }}>
            <Typography variant="body2" color="text.secondary" gutterBottom>
              {currentStep || (uploading ? 'Uploading...' : t(K.page.extensions.installing))}
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
