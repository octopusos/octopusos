export type CallWsIncomingMessage =
  | {
      type: 'hello'
      protocol_version: number
      call_session_id: string
      capabilities: {
        audio_input: boolean
        audio_output: boolean
        transcript: 'none' | 'partial' | 'final'
        codec_in: string[]
        codec_out: string[]
        audio_format_in: {
          codec: string
          sample_rate_hz: number
          channels: number
          frame_ms: number
        }
        audio_format_out: {
          codec: string
          sample_rate_hz: number
          channels: number
          frame_ms: number
        }
      }
    }
  | { type: 'status'; status: 'connecting' | 'listening' | 'speaking' | 'hold' | 'ended' }
  | {
      type: 'audio_output'
      codec: string
      sample_rate: number
      format?: {
        codec: string
        sample_rate_hz: number
        channels: number
        frame_ms: number
      }
      samples: number[]
    }
  | { type: 'transcript.partial'; speaker: string; text: string }
  | { type: 'transcript.final'; speaker: string; text: string }
  | { type: 'error'; message: string }

export interface CallWsClientHandlers {
  onOpen?: () => void
  onClose?: () => void
  onError?: (message: string) => void
  onMessage?: (message: CallWsIncomingMessage) => void
}

export class CallWsClient {
  private ws: WebSocket | null = null
  private readonly wsUrl: string
  private readonly handlers: CallWsClientHandlers
  private inputFormat: {
    codec: string
    sample_rate_hz: number
    channels: number
    frame_ms: number
  } | null = null

  constructor(wsUrl: string, handlers: CallWsClientHandlers) {
    this.wsUrl = wsUrl
    this.handlers = handlers
  }

  connect(): void {
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return
    }

    this.ws = new WebSocket(this.wsUrl)
    this.ws.onopen = () => {
      this.handlers.onOpen?.()
    }

    this.ws.onmessage = (event: MessageEvent<string>) => {
      try {
        const payload = JSON.parse(event.data) as CallWsIncomingMessage
        this.handlers.onMessage?.(payload)
      } catch {
        this.handlers.onError?.('Invalid call websocket message')
      }
    }

    this.ws.onerror = () => {
      this.handlers.onError?.('Call websocket error')
    }

    this.ws.onclose = () => {
      this.handlers.onClose?.()
    }
  }

  sendMute(muted: boolean): void {
    this.send({ type: 'control.mute', muted })
  }

  sendHold(hold: boolean): void {
    this.send({ type: 'control.hold', hold })
  }

  sendEnd(): void {
    this.send({ type: 'control.end' })
  }

  setInputFormat(format: { codec: string; sample_rate_hz: number; channels: number; frame_ms: number }): void {
    this.inputFormat = format
  }

  sendAudioInput(samples: number[], sampleRate: number): void {
    this.send({
      type: 'audio_input',
      codec: this.inputFormat?.codec ?? 'pcm_f32',
      sample_rate: sampleRate,
      format: this.inputFormat,
      samples,
    })
  }

  close(): void {
    if (!this.ws) {
      return
    }
    this.ws.close()
    this.ws = null
  }

  private send(payload: Record<string, unknown>): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      return
    }
    this.ws.send(JSON.stringify(payload))
  }
}
