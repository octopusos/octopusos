import { get } from '@/platform/http'

export type ChangeLogIndexEntry = {
  key: string
  title: string
  outline: string[]
  md_path: string
}

export const changelogService = {
  async getIndex(lang?: 'en' | 'zh'): Promise<{ ok: boolean; versions: ChangeLogIndexEntry[] }> {
    const qs = lang ? `?lang=${encodeURIComponent(lang)}` : ''
    return get(`/api/changelog/index${qs}`)
  },
  async getEntry(key: string, lang?: 'en' | 'zh'): Promise<string> {
    // Use fetch instead of platform http wrapper to preserve text/markdown response.
    const qs = new URLSearchParams({ key })
    if (lang) qs.set('lang', lang)
    const resp = await fetch(`/api/changelog/entry?${qs.toString()}`, { method: 'GET' })
    if (!resp.ok) {
      throw new Error(`CHANGELOG_ENTRY_${resp.status}`)
    }
    return await resp.text()
  },
}
