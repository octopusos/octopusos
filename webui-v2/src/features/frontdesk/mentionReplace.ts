export function replaceFirstMentionInDraft(
  currentDraft: string,
  replacementAgentId: string,
  rawMentions?: string[]
): string {
  const trimmed = currentDraft.trim()
  const replacement = `@${replacementAgentId}`
  if (!trimmed) {
    return replacement
  }

  const normalizedMentions = Array.isArray(rawMentions)
    ? rawMentions
      .map(item => String(item || '').trim().replace(/^@+/, '').toLowerCase())
      .filter(Boolean)
    : []

  const mentionMatches = Array.from(currentDraft.matchAll(/@([a-zA-Z0-9._-]+)/g))
  for (const match of mentionMatches) {
    const fullToken = match[0]
    const tokenBody = (match[1] || '').toLowerCase()
    if (!normalizedMentions.includes(tokenBody)) {
      continue
    }
    const index = match.index ?? currentDraft.indexOf(fullToken)
    if (index < 0) {
      continue
    }
    return `${currentDraft.slice(0, index)}${replacement}${currentDraft.slice(index + fullToken.length)}`
  }

  const firstMention = mentionMatches[0]
  if (firstMention) {
    const fullToken = firstMention[0]
    const index = firstMention.index ?? currentDraft.indexOf(fullToken)
    if (index >= 0) {
      return `${currentDraft.slice(0, index)}${replacement}${currentDraft.slice(index + fullToken.length)}`
    }
  }

  return replacement
}

