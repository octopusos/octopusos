import { useEffect, useRef, useState } from 'react'
import {
  Alert,
  Box,
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Stack,
  Typography,
} from '@mui/material'
import { CallWsClient, type CallWsIncomingMessage } from '@/services/callWsClient'
import { AudioPlayer } from '@/services/audioPlayer'
import { AudioRecorder } from '@/services/audioRecorder'
import { useCallStateMachine } from '@/hooks/useCallStateMachine'
import { useTextTranslation } from '@/ui/text'

export interface ActiveCall {
  callSessionId: string
  wsUrl: string
  runtime: string
  providerId?: string
  modelId?: string
}

interface InCallPanelProps {
  open: boolean
  call: ActiveCall
  onClose: () => void
}

export function InCallPanel({ open, call, onClose }: InCallPanelProps) {
  const { t } = useTextTranslation()
  const { state, send } = useCallStateMachine()
  const wsClientRef = useRef<CallWsClient | null>(null)
  const playerRef = useRef<AudioPlayer | null>(null)
  const recorderRef = useRef<AudioRecorder | null>(null)
  const helloReceivedRef = useRef(false)
  const mutedRef = useRef(false)
  const holdRef = useRef(false)
  const endRequestedRef = useRef(false)

  const [isMuted, setIsMuted] = useState(false)
  const [isHold, setIsHold] = useState(false)
  const [micError, setMicError] = useState<string | null>(null)
  const [closeEnabled, setCloseEnabled] = useState(false)
  const micPermissionDeniedText = t('page.voice.micPermissionDenied')
  const connectionLostText = t('page.voice.connectionLost')

  useEffect(() => {
    mutedRef.current = isMuted
  }, [isMuted])

  useEffect(() => {
    holdRef.current = isHold
  }, [isHold])

  useEffect(() => {
    if (!open) {
      return
    }

    let mounted = true
    endRequestedRef.current = false
    send({ type: 'START_CONNECTING' })

    playerRef.current = new AudioPlayer()

    const handleIncoming = async (message: CallWsIncomingMessage): Promise<void> => {
      if (!mounted) {
        return
      }

      if (message.type === 'status') {
        send({ type: 'SERVER_STATUS', status: message.status })
        if (message.status === 'ended') {
          setCloseEnabled(true)
        }
        return
      }

      if (message.type === 'hello') {
        helloReceivedRef.current = true
        wsClientRef.current?.setInputFormat(message.capabilities.audio_format_in)
        send({ type: 'WS_READY' })
        recorderRef.current?.start({
          sample_rate_hz: message.capabilities.audio_format_in.sample_rate_hz,
          frame_ms: message.capabilities.audio_format_in.frame_ms,
        }).catch(() => {
          setMicError(micPermissionDeniedText)
        })
        return
      }

      if (message.type === 'audio_output') {
        const sampleRate = message.format?.sample_rate_hz ?? message.sample_rate
        await playerRef.current?.play(message.samples ?? [], sampleRate)
        return
      }

      if (message.type === 'error') {
        send({ type: 'FAIL', message: message.message })
        setCloseEnabled(true)
      }
    }

    wsClientRef.current = new CallWsClient(call.wsUrl, {
      onOpen: () => {},
      onClose: () => {
        if (endRequestedRef.current) {
          send({ type: 'END_CONFIRMED' })
        } else {
          send({ type: 'FAIL', message: connectionLostText })
        }
        setCloseEnabled(true)
      },
      onError: (message) => {
        send({ type: 'FAIL', message })
        setCloseEnabled(true)
      },
      onMessage: (message) => {
        void handleIncoming(message)
      },
    })

    wsClientRef.current.connect()

    recorderRef.current = new AudioRecorder({
      onFrame: (samples, sampleRate) => {
        if (!helloReceivedRef.current) {
          return
        }
        if (mutedRef.current || holdRef.current) {
          return
        }
        wsClientRef.current?.sendAudioInput(samples, sampleRate)
      },
    })

    return () => {
      mounted = false
      wsClientRef.current?.close()
      void recorderRef.current?.stop()
      void playerRef.current?.close()
      wsClientRef.current = null
      recorderRef.current = null
      playerRef.current = null
    }
  }, [call.wsUrl, open, send])

  const handleMuteToggle = (): void => {
    const nextMuted = !isMuted
    setIsMuted(nextMuted)
    wsClientRef.current?.sendMute(nextMuted)
  }

  const handleEnd = (): void => {
    endRequestedRef.current = true
    send({ type: 'END_REQUEST' })
    wsClientRef.current?.sendEnd()
  }

  const handleHoldToggle = (): void => {
    const nextHold = !isHold
    setIsHold(nextHold)
    wsClientRef.current?.sendHold(nextHold)
  }

  const handleRetry = (): void => {
    wsClientRef.current?.close()
    send({ type: 'START_CONNECTING' })
    setCloseEnabled(false)
    wsClientRef.current?.connect()
  }

  const statusLabel: Record<string, string> = {
    connecting: t('page.voice.statusConnecting'),
    in_call_listening: t('page.voice.statusListening'),
    in_call_speaking: t('page.voice.statusSpeaking'),
    in_call_hold: t('page.voice.statusHold'),
    ending: t('page.voice.statusEnding'),
    ended: t('page.voice.statusEnded'),
    error: t('page.voice.statusError'),
    idle: t('page.voice.statusIdle'),
  }

  return (
    <Dialog open={open} onClose={closeEnabled ? onClose : undefined} maxWidth="sm" fullWidth>
      <DialogTitle>{t('page.voice.inCall')}</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ mt: 1 }}>
          <Box display="flex" justifyContent="space-between" alignItems="center">
            <Typography variant="body2">{t('page.voice.session')}: {call.callSessionId}</Typography>
            <Chip
              label={statusLabel[state.state] ?? state.state}
              color={state.state === 'error' ? 'error' : 'primary'}
              data-testid="call-status-chip"
            />
          </Box>

          <Typography variant="body2" color="text.secondary">
            {t('page.voice.runtime')}: {call.runtime} {call.providerId ? `| ${t('page.voice.provider')}: ${call.providerId}` : ''} {call.modelId ? `| ${t('page.voice.model')}: ${call.modelId}` : ''}
          </Typography>

          <Alert severity="info">{t('page.voice.transcriptBackendOnly')}</Alert>

          {micError && <Alert severity="warning">{micError}</Alert>}

          {state.state === 'error' && (
            <Alert severity="error">{state.errorMessage ?? t('page.voice.callFailed')}</Alert>
          )}
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={handleMuteToggle} data-testid="call-mute-button">
          {isMuted ? t('page.voice.unmute') : t('page.voice.mute')}
        </Button>
        <Button
          onClick={handleHoldToggle}
          data-testid="call-hold-button"
        >
          {isHold ? t('page.voice.resume') : t('page.voice.hold')}
        </Button>
        <Button color="error" variant="contained" onClick={handleEnd} data-testid="call-end-button">
          {t('page.voice.end')}
        </Button>
        {state.state === 'error' && (
          <Button onClick={handleRetry} data-testid="call-retry-button">
            {t('common.retry')}
          </Button>
        )}
        <Button onClick={onClose} disabled={!closeEnabled} data-testid="call-close-button">
          {t('common.close')}
        </Button>
      </DialogActions>
    </Dialog>
  )
}
