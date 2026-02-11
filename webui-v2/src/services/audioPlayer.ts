export class AudioPlayer {
  private context: AudioContext | null = null

  async play(samples: number[], sampleRate: number): Promise<void> {
    if (samples.length === 0) {
      return
    }

    if (!this.context) {
      this.context = new AudioContext()
    }
    if (this.context.state === 'suspended') {
      await this.context.resume()
    }

    const buffer = this.context.createBuffer(1, samples.length, sampleRate)
    buffer.copyToChannel(Float32Array.from(samples), 0)

    const source = this.context.createBufferSource()
    source.buffer = buffer
    source.connect(this.context.destination)
    source.start()
  }

  async close(): Promise<void> {
    if (!this.context) {
      return
    }
    await this.context.close()
    this.context = null
  }
}
