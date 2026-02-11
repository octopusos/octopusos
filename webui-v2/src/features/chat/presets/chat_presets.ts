export type ChatPresetId = 'frontdesk' | 'life' | 'work' | 'free'

export interface ChatPreset {
  id: ChatPresetId
  title: string
  subtitle: string
  // Baseline injected into system prompt
  systemPrompt: string
  // Behavioral tone (UI tag + backend metadata)
  tone: 'professional' | 'warm' | 'concise' | 'adaptive'
  // Force new session creation
  createNewSession: boolean
  // Scope: frontdesk must be global
  scope: 'global' | 'project'
  // Whether to inherit current project
  inheritProject: boolean
}

export const CHAT_PRESETS: Record<ChatPresetId, ChatPreset> = {
  frontdesk: {
    id: 'frontdesk',
    title: '接待 / 回复',
    subtitle: 'Frontdesk',
    systemPrompt: [
      '你是前台/接待助手。礼貌、结构化、主动追问缺失信息。',
      '默认流程：收集 → 总结 → 下一步。',
    ].join('\n'),
    tone: 'warm',
    createNewSession: false,
    scope: 'global',
    inheritProject: false,
  },
  life: {
    id: 'life',
    title: '帮我安排',
    subtitle: 'Life',
    systemPrompt: [
      '你是日常生活助手，语气亲和、简明。',
      '避免给出医疗或法律定论；必要时提示寻求专业人士。',
    ].join('\n'),
    tone: 'warm',
    createNewSession: true,
    scope: 'project',
    inheritProject: true,
  },
  work: {
    id: 'work',
    title: '推进工作',
    subtitle: 'Work',
    systemPrompt: [
      '你是办公助手。输出结构化、少寒暄、给出可执行的下一步。',
    ].join('\n'),
    tone: 'concise',
    createNewSession: true,
    scope: 'project',
    inheritProject: true,
  },
  free: {
    id: 'free',
    title: '随便聊',
    subtitle: 'Free',
    systemPrompt: '',
    tone: 'adaptive',
    createNewSession: true,
    scope: 'project',
    inheritProject: true,
  },
}

export const CHAT_PRESET_LIST: ChatPreset[] = Object.values(CHAT_PRESETS)

export function getChatPreset(id?: string | null): ChatPreset | null {
  if (!id) return null
  return (CHAT_PRESETS as Record<string, ChatPreset>)[id] ?? null
}
