export type RuntimeConfig = {
  public_origin?: string
}

let runtimeConfig: RuntimeConfig = {}
let initialized = false

export async function initializeRuntimeConfig(): Promise<void> {
  if (initialized) return
  initialized = true

  try {
    const response = await fetch('/runtime/runtime-config.json', { cache: 'no-store' })
    if (!response.ok) return
    runtimeConfig = (await response.json()) as RuntimeConfig
  } catch {
    runtimeConfig = {}
  }
}

export function getRuntimePublicOrigin(): string {
  const fromFile = String(runtimeConfig.public_origin || '').trim()
  if (fromFile) return fromFile
  return window.location.origin
}

export function assertRuntimeOriginConsistency(): void {
  const configured = String(runtimeConfig.public_origin || '').trim()
  if (!configured) return
  if (configured !== window.location.origin) {
    console.error('[Platform] public_origin mismatch', {
      configured,
      actual: window.location.origin,
    })
  }
}
