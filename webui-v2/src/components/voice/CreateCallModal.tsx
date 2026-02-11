import { useEffect, useMemo, useState } from 'react'
import {
  Alert,
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  TextField,
} from '@mui/material'
import { type CallRuntime, type CreateCallSessionRequest } from '@/services/callService'
import { useTextTranslation } from '@/ui/text'
import { PROVIDERS, PROVIDER_MODELS } from './callOptions'

interface CreateCallModalProps {
  open: boolean
  creating: boolean
  error?: string | null
  onClose: () => void
  onStart: (payload: CreateCallSessionRequest, idempotencyKey: string) => Promise<void>
}

export function CreateCallModal({ open, creating, error, onClose, onStart }: CreateCallModalProps) {
  const { t } = useTextTranslation()
  const [runtime, setRuntime] = useState<CallRuntime>('local')
  const [providerId, setProviderId] = useState('')
  const [modelId, setModelId] = useState('')
  const [voiceProfileId, setVoiceProfileId] = useState('')
  const [idempotencyKey, setIdempotencyKey] = useState('')

  const generateIdempotencyKey = (): string => {
    if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
      return crypto.randomUUID()
    }
    return `idem_${Date.now()}_${Math.random().toString(16).slice(2)}`
  }

  useEffect(() => {
    if (!open) {
      return
    }
    setIdempotencyKey(generateIdempotencyKey())
  }, [open])

  const modelOptions = useMemo(() => {
    if (!providerId) {
      return []
    }
    return PROVIDER_MODELS[providerId] ?? []
  }, [providerId])

  const cloudInvalid = runtime === 'cloud' && (!providerId || !modelId)
  const startDisabled = creating || cloudInvalid

  const handleRuntimeChange = (value: CallRuntime): void => {
    setRuntime(value)
    if (value === 'local') {
      setProviderId('')
      setModelId('')
    }
    setIdempotencyKey(generateIdempotencyKey())
  }

  const handleProviderChange = (value: string): void => {
    setProviderId(value)
    setModelId('')
    setIdempotencyKey(generateIdempotencyKey())
  }

  const handleStart = async (): Promise<void> => {
    const key = idempotencyKey || generateIdempotencyKey()
    if (!idempotencyKey) {
      setIdempotencyKey(key)
    }
    await onStart({
      runtime,
      provider_id: runtime === 'cloud' ? providerId : undefined,
      model_id: runtime === 'cloud' ? modelId : undefined,
      voice_profile_id: voiceProfileId || undefined,
    }, key)
  }

  return (
    <Dialog open={open} onClose={creating ? undefined : onClose} maxWidth="sm" fullWidth>
      <DialogTitle>{t('page.voice.createCall')}</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ mt: 1 }}>
          {error && <Alert severity="error">{error}</Alert>}

          <FormControl fullWidth>
            <InputLabel id="call-runtime-label">{t('page.voice.runtime')}</InputLabel>
            <Select
              labelId="call-runtime-label"
              label={t('page.voice.runtime')}
              value={runtime}
              onChange={(event) => handleRuntimeChange(event.target.value as CallRuntime)}
              data-testid="call-runtime-select"
            >
              <MenuItem value="local">{t('page.voice.local')}</MenuItem>
              <MenuItem value="cloud">{t('page.voice.cloud')}</MenuItem>
            </Select>
          </FormControl>

          {runtime === 'cloud' && (
            <>
              <FormControl fullWidth>
                <InputLabel id="call-provider-label">{t('page.voice.provider')}</InputLabel>
                <Select
                  labelId="call-provider-label"
                  label={t('page.voice.provider')}
                  value={providerId}
                  onChange={(event) => handleProviderChange(event.target.value)}
                  data-testid="call-provider-select"
                >
                  {PROVIDERS.map((provider) => (
                    <MenuItem key={provider} value={provider}>
                      {provider}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              <FormControl fullWidth disabled={!providerId}>
                <InputLabel id="call-model-label">{t('page.voice.model')}</InputLabel>
                <Select
                  labelId="call-model-label"
                  label={t('page.voice.model')}
                  value={modelId}
                  onChange={(event) => {
                    setModelId(event.target.value)
                    setIdempotencyKey(generateIdempotencyKey())
                  }}
                  data-testid="call-model-select"
                >
                  {modelOptions.map((model) => (
                    <MenuItem key={model} value={model}>
                      {model}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </>
          )}

          <TextField
            label={t('page.voice.voiceProfileOptional')}
            value={voiceProfileId}
            onChange={(event) => {
              setVoiceProfileId(event.target.value)
              setIdempotencyKey(generateIdempotencyKey())
            }}
            placeholder={t('page.voice.defaultPlaceholder')}
            data-testid="call-voice-profile-input"
          />

          {cloudInvalid && (
            <Box>
              <Alert severity="warning">{t('page.voice.cloudRequiresProviderModel')}</Alert>
            </Box>
          )}
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={creating}>
          {t('common.cancel')}
        </Button>
        <Button
          variant="contained"
          onClick={() => {
            void handleStart()
          }}
          disabled={startDisabled}
          data-testid="start-call-button"
        >
          {t('page.voice.startCall')}
        </Button>
      </DialogActions>
    </Dialog>
  )
}
