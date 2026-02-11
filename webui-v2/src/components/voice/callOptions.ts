export const PROVIDER_MODELS: Record<string, string[]> = {
  openai: ['gpt-4o-realtime-preview', 'gpt-4o-mini-realtime-preview'],
  volc: ['doubao-realtime-o', 'doubao-realtime-sc'],
  anthropic: ['claude-sonnet-4.5-voice'],
  deepseek: ['deepseek-chat-voice-v1'],
}

export const PROVIDERS = Object.keys(PROVIDER_MODELS)
