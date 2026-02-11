export interface AudioRecorderOptions {
  onFrame: (samples: number[], sampleRate: number) => void
  frameSize?: number
}

export interface RecorderAudioFormat {
  sample_rate_hz: number
  frame_ms: number
}

export class AudioRecorder {
  private stream: MediaStream | null = null
  private context: AudioContext | null = null
  private processor: ScriptProcessorNode | null = null
  private source: MediaStreamAudioSourceNode | null = null
  private readonly onFrame: (samples: number[], sampleRate: number) => void
  private readonly frameSize: number

  constructor(options: AudioRecorderOptions) {
    this.onFrame = options.onFrame
    this.frameSize = options.frameSize ?? 2048
  }

  async start(format?: RecorderAudioFormat): Promise<void> {
    this.stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    const sampleRate = format?.sample_rate_hz ?? 24000
    const frameSize = this.frameSize || Math.max(Math.floor(sampleRate * ((format?.frame_ms ?? 20) / 1000)), 256)

    this.context = new AudioContext({ sampleRate })
    if (this.context.state === 'suspended') {
      await this.context.resume()
    }

    this.source = this.context.createMediaStreamSource(this.stream)
    this.processor = this.context.createScriptProcessor(frameSize, 1, 1)

    this.processor.onaudioprocess = (event: AudioProcessingEvent) => {
      const channel = event.inputBuffer.getChannelData(0)
      this.onFrame(Array.from(channel), event.inputBuffer.sampleRate)
    }

    this.source.connect(this.processor)
    this.processor.connect(this.context.destination)
  }

  async stop(): Promise<void> {
    if (this.processor) {
      this.processor.disconnect()
      this.processor.onaudioprocess = null
      this.processor = null
    }

    if (this.source) {
      this.source.disconnect()
      this.source = null
    }

    if (this.stream) {
      this.stream.getTracks().forEach((track) => track.stop())
      this.stream = null
    }

    if (this.context) {
      await this.context.close()
      this.context = null
    }
  }
}
