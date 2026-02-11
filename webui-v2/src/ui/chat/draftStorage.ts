const NS = 'octopusos:webui:chatDraft'

export function makeDraftKey(scope?: string): string {
  return `${NS}:${scope || 'global'}`
}

export function readDraft(key: string): string {
  try {
    return sessionStorage.getItem(key) || ''
  } catch {
    return ''
  }
}

export function writeDraft(key: string, value: string): void {
  try {
    sessionStorage.setItem(key, value)
  } catch {
    // ignore
  }
}

export function clearDraft(key: string): void {
  try {
    sessionStorage.removeItem(key)
  } catch {
    // ignore
  }
}
