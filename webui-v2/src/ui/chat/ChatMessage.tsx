/**
 * ChatMessage - Individual Message Bubble Component
 *
 * Displays a single chat message with:
 * - Role-based styling (user/assistant/system)
 * - Avatar
 * - Timestamp
 * - Optional metadata (model, tokens)
 * - Rich content rendering:
 *   - Markdown support (headings, lists, tables, etc.)
 *   - Code syntax highlighting
 *   - Code block actions (copy, download, format, preview)
 *   - Collapsible long code blocks
 */

import { useState, useMemo, useEffect, memo } from 'react'
import {
  Box,
  Paper,
  Typography,
  Avatar,
  IconButton,
  Tooltip,
  useTheme,
  alpha,
} from '@mui/material'
import {
  Person as PersonIcon,
  SmartToy as SmartToyIcon,
  ContentCopy as CopyIcon,
  Download as DownloadIcon,
  Code as FormatIcon,
  Visibility as PreviewIcon,
  ExpandMore as ExpandIcon,
  ExpandLess as CollapseIcon,
  Check as CheckIcon,
} from '@mui/icons-material'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeRaw from 'rehype-raw'
import { Link as RouterLink } from 'react-router-dom'
import { K, useTextTranslation } from '@/ui/text'
import { CodePreviewDialog } from './CodePreviewDialog'
import { WeatherCard } from './cards/WeatherCard'
import { FactQueryCard } from './cards/FactQueryCard'
import type { ChatMessageType } from './ChatShell'
import { usePromptDialog } from '@/ui/interaction'

interface ChatMessageProps {
  message: ChatMessageType
  onEdit?: (message: ChatMessageType) => void
}

/**
 * Pure function for HTML entity decoding
 * Replaces DOM-based innerHTML approach with efficient string operations
 */
function decodeHTMLEntities(text: string): string {
  const entities: Record<string, string> = {
    '&lt;': '<',
    '&gt;': '>',
    '&amp;': '&',
    '&quot;': '"',
    '&#39;': "'",
    '&nbsp;': ' '
  }

  let decoded = text
  let prevDecoded = ''

  // Recursive decoding (handles multiple layers of escaping)
  while (decoded !== prevDecoded) {
    prevDecoded = decoded
    for (const [entity, char] of Object.entries(entities)) {
      decoded = decoded.split(entity).join(char)
    }
  }

  return decoded
}

/**
 * CodeBlock - Enhanced code block with syntax highlighting and actions
 */
interface CodeBlockProps {
  language: string
  value: string
  inline?: boolean
}

// 🎯 Syntax Highlighting Degradation Strategy
// Long code blocks (>80 lines) default to plain text mode to prevent UI blocking
const MAX_LINES_AUTO_HIGHLIGHT = 80

type SyntaxModule = {
  SyntaxHighlighter: typeof import('react-syntax-highlighter/dist/esm/prism-light').default
  oneDark: Record<string, any>
  oneLight: Record<string, any>
}

let syntaxModulePromise: Promise<SyntaxModule> | null = null

const loadSyntaxModule = async (): Promise<SyntaxModule> => {
  if (!syntaxModulePromise) {
    syntaxModulePromise = Promise.all([
      import('react-syntax-highlighter/dist/esm/prism-light'),
      import('react-syntax-highlighter/dist/esm/styles/prism'),
      import('react-syntax-highlighter/dist/esm/languages/prism/javascript'),
      import('react-syntax-highlighter/dist/esm/languages/prism/typescript'),
      import('react-syntax-highlighter/dist/esm/languages/prism/jsx'),
      import('react-syntax-highlighter/dist/esm/languages/prism/tsx'),
      import('react-syntax-highlighter/dist/esm/languages/prism/json'),
      import('react-syntax-highlighter/dist/esm/languages/prism/bash'),
      import('react-syntax-highlighter/dist/esm/languages/prism/python'),
      import('react-syntax-highlighter/dist/esm/languages/prism/sql'),
      import('react-syntax-highlighter/dist/esm/languages/prism/yaml'),
      import('react-syntax-highlighter/dist/esm/languages/prism/markup'),
      import('react-syntax-highlighter/dist/esm/languages/prism/css'),
    ]).then(([
      prismModule,
      styleModule,
      jsModule,
      tsModule,
      jsxModule,
      tsxModule,
      jsonModule,
      bashModule,
      pythonModule,
      sqlModule,
      yamlModule,
      markupModule,
      cssModule,
    ]) => {
      const SyntaxHighlighter = prismModule.default
      SyntaxHighlighter.registerLanguage('javascript', jsModule.default)
      SyntaxHighlighter.registerLanguage('typescript', tsModule.default)
      SyntaxHighlighter.registerLanguage('jsx', jsxModule.default)
      SyntaxHighlighter.registerLanguage('tsx', tsxModule.default)
      SyntaxHighlighter.registerLanguage('json', jsonModule.default)
      SyntaxHighlighter.registerLanguage('bash', bashModule.default)
      SyntaxHighlighter.registerLanguage('python', pythonModule.default)
      SyntaxHighlighter.registerLanguage('sql', sqlModule.default)
      SyntaxHighlighter.registerLanguage('yaml', yamlModule.default)
      SyntaxHighlighter.registerLanguage('html', markupModule.default)
      SyntaxHighlighter.registerLanguage('css', cssModule.default)

      return {
        SyntaxHighlighter,
        oneDark: styleModule.oneDark,
        oneLight: styleModule.oneLight,
      }
    })
  }

  return syntaxModulePromise
}

const loadPrettierFormatter = async (parser: string) => {
  const prettierModule = await import('prettier/standalone')
  switch (parser) {
    case 'html':
      return {
        prettier: prettierModule,
        plugins: [(await import('prettier/parser-html')).default],
      }
    case 'babel':
      return {
        prettier: prettierModule,
        plugins: [(await import('prettier/parser-babel')).default],
      }
    case 'typescript':
      return {
        prettier: prettierModule,
        plugins: [(await import('prettier/parser-typescript')).default],
      }
    case 'css':
      return {
        prettier: prettierModule,
        plugins: [(await import('prettier/parser-postcss')).default],
      }
    default:
      return { prettier: prettierModule, plugins: [] }
  }
}

const CodeBlock = memo(function CodeBlock({ language, value, inline }: CodeBlockProps) {
  const theme = useTheme()
  const octopusos = (theme.palette as any).octopusos
  const { t } = useTextTranslation()
  const { alert, dialog } = usePromptDialog()

  // 🎯 All hooks must be called at the top, before any conditional returns
  const [copied, setCopied] = useState(false)
  const [collapsed, setCollapsed] = useState(false)
  const [formatted, setFormatted] = useState(false)
  const [previewOpen, setPreviewOpen] = useState(false)
  const [syntaxModule, setSyntaxModule] = useState<SyntaxModule | null>(null)

  // Calculate line count for enableHighlight initialization
  const lines = value.split('\n')
  const lineCount = lines.length

  // 🎯 Syntax Highlighting Degradation Strategy
  // For long code blocks (>80 lines), default to plain text mode
  // User can explicitly enable highlighting on demand
  const [enableHighlight, setEnableHighlight] = useState(lineCount <= MAX_LINES_AUTO_HIGHLIGHT)

  useEffect(() => {
    if (inline || !enableHighlight) {
      return
    }

    let active = true
    loadSyntaxModule()
      .then((module) => {
        if (active) {
          setSyntaxModule(module)
        }
      })
      .catch((error) => {
        console.error('[ChatMessage] Failed to load syntax highlighter', error)
      })

    return () => {
      active = false
    }
  }, [enableHighlight, inline])

  const isDark = theme.palette.mode === 'dark'
  const codeStyle = syntaxModule ? (isDark ? syntaxModule.oneDark : syntaxModule.oneLight) : undefined

  // Calculate derived state
  const isLongCode = lineCount > 20
  const displayValue = collapsed ? lines.slice(0, 10).join('\n') + '\n...' : value

  // 🎯 Memoize highlighted content to prevent re-rendering
  // Must be called before any conditional returns (React hooks rule)
  // Only re-calculate when displayValue, language, or codeStyle changes
  const highlightedContent = useMemo(() => {
    if (!enableHighlight || !syntaxModule) {
      return (
        <Box
          component="pre"
          sx={{
            margin: 0,
            borderRadius: 0,
            fontSize: '0.9em',
            fontFamily: 'monospace',
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word',
            bgcolor: octopusos?.bg?.elevated || 'background.paper',
            color: 'text.primary',
            p: 2,
          }}
        >
          {displayValue}
        </Box>
      )
    }

    const SyntaxHighlighter = syntaxModule.SyntaxHighlighter

    return (
      <SyntaxHighlighter
        language={language || 'text'}
        style={codeStyle}
        customStyle={{
          margin: 0,
          borderRadius: 0,
          fontSize: '0.9em',
        }}
        showLineNumbers={lineCount > 5}
      >
        {displayValue}
      </SyntaxHighlighter>
    )
  }, [octopusos?.bg?.elevated, codeStyle, displayValue, enableHighlight, language, lineCount, syntaxModule])

  // If inline code, render simple (after all hooks)
  if (inline) {
    return (
      <>
        <code
          style={{
            backgroundColor: alpha(theme.palette.primary.main, 0.1),
            color: theme.palette.primary.main,
            padding: '2px 6px',
            borderRadius: 4,
            fontSize: '0.9em',
            fontFamily: 'monospace',
          }}
        >
          {value}
        </code>
        {dialog}
      </>
    )
  }

  const handleCopy = () => {
    navigator.clipboard.writeText(value)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleDownload = () => {
    const blob = new Blob([value], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `code.${language || 'txt'}`
    a.click()
    URL.revokeObjectURL(url)
  }

  const handleFormat = async () => {
    try {
      // Determine parser based on language
      let parser: string | undefined

      switch (language.toLowerCase()) {
        case 'html':
        case 'xml':
          parser = 'html'
          break
        case 'javascript':
        case 'js':
          parser = 'babel'
          break
        case 'typescript':
        case 'ts':
          parser = 'typescript'
          break
        case 'jsx':
          parser = 'babel'
          break
        case 'tsx':
          parser = 'typescript'
          break
        case 'css':
        case 'scss':
        case 'less':
          parser = 'css'
          break
        case 'json':
          parser = 'json'
          break
        default:
          console.warn(`[ChatMessage] Formatting not supported for language: ${language}`)
          return
      }

      const formatterKey = parser === 'json' ? 'babel' : parser
      const { prettier, plugins } = await loadPrettierFormatter(formatterKey)

      // Format code with prettier
      const formattedCode = await prettier.format(value, {
        parser,
        plugins,
        printWidth: 80,
        tabWidth: 2,
        semi: true,
        singleQuote: true,
        trailingComma: 'es5',
      })

      // Copy formatted code to clipboard
      await navigator.clipboard.writeText(formattedCode)
      setFormatted(true)
      setTimeout(() => setFormatted(false), 2000)

      // console.log('[ChatMessage] ✅ Code formatted and copied to clipboard')
    } catch (err) {
      console.error('[ChatMessage] ❌ Format error:', err)
      await alert({
        title: t(K.common.error),
        message: t('page.chat.codeFormatFailed', {
          error: err instanceof Error ? err.message : t(K.common.unknown),
        }),
        confirmText: t(K.common.ok),
        color: 'error',
        testId: 'chat-code-format-failed-dialog',
      })
    }
  }

  const handlePreview = () => {
    if (language === 'html' || language === 'xml') {
      // Open preview dialog
      setPreviewOpen(true)
    }
  }

  const handleClosePreview = () => {
    setPreviewOpen(false)
  }

  const isHTML = language === 'html' || language === 'xml'

  // 🎯 Plain Text Mode Rendering (for long code blocks without highlighting)
  // Significantly improves performance by avoiding expensive syntax highlighting
  if (!enableHighlight) {
    return (
      <>
        <Box sx={{ my: 2 }}>
        {/* Code Block Header */}
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            px: 2,
            py: 0.5,
            bgcolor: alpha(octopusos?.bg?.elevated || theme.palette.background.paper, 0.5),
            borderTopLeftRadius: 8,
            borderTopRightRadius: 8,
            borderBottom: `1px solid ${theme.palette.divider}`,
          }}
        >
          {/* Language Label */}
          <Typography
            variant="caption"
            sx={{
              fontFamily: 'monospace',
              fontWeight: 600,
              color: 'text.secondary',
              textTransform: 'uppercase',
            }}
          >
            {language || 'text'} ({lineCount} {t('common.lines', { defaultValue: 'lines' })})
          </Typography>

          {/* Action Buttons */}
          <Box sx={{ display: 'flex', gap: 0.5 }}>
            {/* Enable Highlight Button */}
            <Tooltip title={t('common.enableHighlight', { defaultValue: 'Enable Syntax Highlighting' })}>
              <IconButton
                size="small"
                onClick={() => setEnableHighlight(true)}
                sx={{
                  color: 'primary.main',
                  '&:hover': {
                    bgcolor: alpha(theme.palette.primary.main, 0.1),
                  },
                }}
              >
                <FormatIcon fontSize="small" />
              </IconButton>
            </Tooltip>

            {/* Copy Button */}
            <Tooltip title={copied ? t('common.copied') : t('common.copy')}>
              <IconButton size="small" onClick={handleCopy}>
                {copied ? <CheckIcon fontSize="small" /> : <CopyIcon fontSize="small" />}
              </IconButton>
            </Tooltip>

            {/* Download Button */}
            <Tooltip title={t('common.download')}>
              <IconButton size="small" onClick={handleDownload}>
                <DownloadIcon fontSize="small" />
              </IconButton>
            </Tooltip>

            {/* Collapse/Expand Button (long code only) */}
            {isLongCode && (
              <Tooltip title={collapsed ? t('common.expand') : t('common.collapse')}>
                <IconButton size="small" onClick={() => setCollapsed(!collapsed)}>
                  {collapsed ? <ExpandIcon fontSize="small" /> : <CollapseIcon fontSize="small" />}
                </IconButton>
              </Tooltip>
            )}
          </Box>
        </Box>

        {/* Plain Text Content (No Highlighting) */}
        <Box
          sx={{
            position: 'relative',
            borderBottomLeftRadius: 8,
            borderBottomRightRadius: 8,
            overflow: 'auto',
            bgcolor: isDark ? '#1e1e1e' : '#f5f5f5',
          }}
        >
          <pre
            style={{
              margin: 0,
              padding: '16px',
              fontFamily: 'Monaco, Consolas, "Courier New", monospace',
              fontSize: '0.9em',
              lineHeight: 1.5,
              color: isDark ? '#d4d4d4' : '#333333',
              whiteSpace: 'pre',
              overflowX: 'auto',
            }}
          >
            {displayValue}
          </pre>
        </Box>
        </Box>
        {dialog}
      </>
    )
  }

  // 🎯 Highlighted mode rendering (syntax highlighting enabled)
  return (
    <>
      <Box sx={{ my: 2 }}>
      {/* Code Block Header */}
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          px: 2,
          py: 0.5,
          bgcolor: alpha(octopusos?.bg?.elevated || theme.palette.background.paper, 0.5),
          borderTopLeftRadius: 8,
          borderTopRightRadius: 8,
          borderBottom: `1px solid ${theme.palette.divider}`,
        }}
      >
        {/* Language Label */}
        <Typography
          variant="caption"
          sx={{
            fontFamily: 'monospace',
            fontWeight: 600,
            color: 'text.secondary',
            textTransform: 'uppercase',
          }}
        >
          {language || 'text'}
        </Typography>

        {/* Action Buttons */}
        <Box sx={{ display: 'flex', gap: 0.5 }}>
          {/* Copy Button */}
          <Tooltip title={copied ? t('common.copied') : t('common.copy')}>
            <IconButton size="small" onClick={handleCopy}>
              {copied ? <CheckIcon fontSize="small" /> : <CopyIcon fontSize="small" />}
            </IconButton>
          </Tooltip>

          {/* Download Button */}
          <Tooltip title={t('common.download')}>
            <IconButton size="small" onClick={handleDownload}>
              <DownloadIcon fontSize="small" />
            </IconButton>
          </Tooltip>

          {/* Format Button (HTML/JS/TS/CSS/JSON) */}
          {['html', 'xml', 'javascript', 'js', 'typescript', 'ts', 'jsx', 'tsx', 'css', 'scss', 'less', 'json'].includes(language.toLowerCase()) && (
            <Tooltip title={formatted ? t('common.formatted') : t('common.format')}>
              <IconButton size="small" onClick={handleFormat}>
                {formatted ? <CheckIcon fontSize="small" /> : <FormatIcon fontSize="small" />}
              </IconButton>
            </Tooltip>
          )}

          {/* Preview Button (HTML only) */}
          {isHTML && (
            <Tooltip title={t('common.preview')}>
              <IconButton size="small" onClick={handlePreview}>
                <PreviewIcon fontSize="small" />
              </IconButton>
            </Tooltip>
          )}

          {/* Collapse/Expand Button (long code only) */}
          {isLongCode && (
            <Tooltip title={collapsed ? t('common.expand') : t('common.collapse')}>
              <IconButton size="small" onClick={() => setCollapsed(!collapsed)}>
                {collapsed ? <ExpandIcon fontSize="small" /> : <CollapseIcon fontSize="small" />}
              </IconButton>
            </Tooltip>
          )}
        </Box>
      </Box>

      {/* Code Content (With Highlighting) */}
      <Box
        sx={{
          position: 'relative',
          borderBottomLeftRadius: 8,
          borderBottomRightRadius: 8,
          overflow: 'hidden',
        }}
      >
        {highlightedContent}
      </Box>

      {/* Preview Dialog */}
        <CodePreviewDialog
          open={previewOpen}
          onClose={handleClosePreview}
          code={value}
          language={language}
        />
      </Box>
      {dialog}
    </>
  )
})

export const ChatMessage = memo(function ChatMessage({ message, onEdit }: ChatMessageProps) {
  const theme = useTheme()
  const octopusos = (theme.palette as any).octopusos
  const { t } = useTextTranslation()
  const isUser = message.role === 'user'
  const isSystem = message.role === 'system'
  const canEdit = isUser && !isSystem && typeof onEdit === 'function'
  const messageStatus = (message.metadata as any)?.status
  const weatherResultType = (message.metadata as any)?.result_type
  const isCompanyResearchReport = !isUser && weatherResultType === 'company_research'
  const weatherLocation = (message.metadata as any)?.location
  const weatherProvider = (message.metadata as any)?.provider
  const factEvidenceIds = ((message.metadata as any)?.fact_evidence_ids as string[] | undefined) || []
  const firstEvidenceId = factEvidenceIds.length > 0 ? factEvidenceIds[0] : null
  const weatherPayload = (message.metadata as any)?.payload as Record<string, unknown> | undefined
  const fxPayload = (message.metadata as any)?.payload as Record<string, unknown> | undefined
  const queryFactPayload = (message.metadata as any)?.payload as Record<string, unknown> | undefined
  const queryFactCore = (queryFactPayload?.fact as Record<string, unknown> | undefined) || undefined
  const hasFxCard = !isUser && weatherResultType === 'fx' && fxPayload?.rate !== undefined
  const hasQueryFactCard = !isUser && weatherResultType === 'query_fact' && !!queryFactPayload
  const queryFactSafeSummary = String((message.metadata as any)?.fact_status || '').toLowerCase() !== 'ok'
    || queryFactPayload?.safe_summary === true
    || queryFactPayload?.value === undefined
    || queryFactPayload?.value === null
  const hasCompleteWeatherPayload = Boolean(
    weatherPayload && (
      weatherPayload?.temp_c !== undefined ||
      weatherPayload?.condition !== undefined ||
      weatherPayload?.wind_kmh !== undefined
    )
  )
  const hasWeatherCard = !isUser && weatherResultType === 'weather' && hasCompleteWeatherPayload
  const hasWeatherErrorCard = !isUser && weatherResultType === 'weather_error' && !!weatherPayload
  const hasFactCard = hasWeatherCard || hasFxCard || hasQueryFactCard || hasWeatherErrorCard
  const showMessageBody = !(hasWeatherCard || hasFxCard || hasQueryFactCard)
  const capabilityUnavailable = (message.metadata as any)?.capability_unavailable
  const integrityRecoveryApplied = Boolean((message.metadata as any)?.context_integrity_recovery_applied)
  const integrityArtifactPath = (message.metadata as any)?.context_integrity_artifact_path as string | undefined
  const weatherDailyData = Array.isArray(weatherPayload?.daily)
    ? weatherPayload.daily.map((item) => {
        const day = item as Record<string, unknown>
        return {
          date: typeof day.date === 'string' ? day.date : undefined,
          condition: typeof day.condition === 'string' ? day.condition : undefined,
          high_c: typeof day.high_c === 'number' ? day.high_c : undefined,
          low_c: typeof day.low_c === 'number' ? day.low_c : undefined,
        }
      })
    : []
  const weatherHourlyData = Array.isArray(weatherPayload?.hourly)
    ? weatherPayload.hourly.map((item) => {
        const hour = item as Record<string, unknown>
        return {
          time: typeof hour.time === 'string' ? hour.time : undefined,
          temp_c: typeof hour.temp_c === 'number' ? hour.temp_c : undefined,
        }
      })
    : []
  const queryFactMetrics = Array.isArray(queryFactPayload?.metrics)
    ? queryFactPayload.metrics
        .map((item) => {
          const metric = item as Record<string, unknown>
          const label = typeof metric.label === 'string' ? decodeHTMLEntities(metric.label) : ''
          const value = metric.value !== undefined ? decodeHTMLEntities(String(metric.value)) : ''
          if (!label || !value) return null
          return { label, value }
        })
        .filter((item): item is { label: string; value: string } => item !== null)
    : []
  const queryFactTrend = Array.isArray(queryFactPayload?.trend)
    ? queryFactPayload.trend
        .map((item) => {
          const point = item as Record<string, unknown>
          const time = typeof point.time === 'string' ? point.time : ''
          const value = typeof point.value === 'number' ? point.value : NaN
          if (!time || !Number.isFinite(value)) return null
          return { time, value }
        })
        .filter((item): item is { time: string; value: number } => item !== null)
    : []
  const queryFactCoreSeriesTrend = Array.isArray((queryFactCore?.data as any)?.series)
    ? ((queryFactCore?.data as any)?.series as Array<Record<string, unknown>>)
        .map((item) => {
          const time = typeof item.t === 'string' ? item.t : ''
          const value = typeof item.v === 'number' ? item.v : NaN
          if (!time || !Number.isFinite(value)) return null
          return { time, value }
        })
        .filter((item): item is { time: string; value: number } => item !== null)
    : []
  const effectiveQueryFactTrend = queryFactTrend.length > 0 ? queryFactTrend : queryFactCoreSeriesTrend

  // 🎯 Memoize ReactMarkdown rendering to prevent unnecessary re-renders
  const renderedContent = useMemo(() => (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      rehypePlugins={[rehypeRaw]}
      components={{
        // Custom code block renderer
        code(props: any) {
          const { inline, className, children } = props

          // Extract language from className
          const match = /language-(\w+)/.exec(className || '')
          let language = match ? match[1] : ''
          let value = String(children).replace(/\n$/, '')

          // ✅ Pure function HTML entity decoding (no DOM manipulation)
          // Handles both ReactMarkdown escaping and backend double-escaping
          if (!inline && (value.includes('&lt;') || value.includes('&gt;') || value.includes('&amp;'))) {
            value = decodeHTMLEntities(value)
          }

          // 🔧 Smart Detection: If no language specified, try to detect
          if (!language && !inline) {

            // Auto-detect language based on content
            if (value.match(/^<!DOCTYPE\s+html/i) || value.match(/<html[\s>]/i)) {
              language = 'html'
              // console.log('[ChatMessage] 🎯 Auto-detected language: HTML')
            } else if (value.match(/^import\s+\w+/m) || value.match(/^from\s+\w+\s+import/m) || value.match(/def\s+\w+\(/)) {
              language = 'python'
              // console.log('[ChatMessage] 🎯 Auto-detected language: Python')
            } else if (value.match(/function\s+\w+\(/) || value.match(/const\s+\w+\s*=/) || value.match(/=>\s*{/)) {
              language = 'javascript'
              // console.log('[ChatMessage] 🎯 Auto-detected language: JavaScript')
            } else if (value.match(/SELECT\s+.*\s+FROM/i) || value.match(/CREATE\s+TABLE/i)) {
              language = 'sql'
              // console.log('[ChatMessage] 🎯 Auto-detected language: SQL')
            } else if (value.match(/^{[\s\n]*"/) || value.match(/":\s*[{["]/)) {
              language = 'json'
              // console.log('[ChatMessage] 🎯 Auto-detected language: JSON')
            }
          }

          return (
            <CodeBlock language={language} value={value} inline={inline} />
          )
        },
        // Custom paragraph renderer (remove extra wrapping)
        p({ children }) {
          return <Typography variant="body1" component="span" sx={{ display: 'block' }}>{children}</Typography>
        },
      }}
    >
      {message.content}
    </ReactMarkdown>
  ), [message.content])

  const handleDownloadReport = () => {
    const rawName = String((message.metadata as any)?.company_research?.company_name || 'company-research')
      .replace(/[^\w\u4e00-\u9fff\- ]+/g, '')
      .trim()
      .replace(/\s+/g, '-')
    const filename = `${rawName || 'company-research'}-report.md`
    const blob = new Blob([message.content || ''], { type: 'text/markdown;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <Box
      sx={{
        display: 'flex',
        justifyContent: isUser ? 'flex-end' : 'flex-start',
        mb: 2,
        ...(isSystem && { justifyContent: 'center' }),
      }}
    >
      {/* Avatar - Assistant/System only (on left) */}
      {!isUser && !isSystem && !hasFactCard && (
        <Avatar sx={{ mr: 1, bgcolor: 'primary.main', width: 36, height: 36 }}>
          <SmartToyIcon fontSize="small" />
        </Avatar>
      )}

      {/* Message Bubble */}
      <Paper
        elevation={1}
        sx={{
          maxWidth: !isUser && hasFactCard ? 'min(820px, 88%)' : '80%',
          width: 'auto',
          p: !isUser && hasFactCard ? 0.75 : 2,
          // ✅ 使用 OctopusOS tokens 适配暗色主题
          bgcolor: isUser
            ? 'primary.main' // 用户消息：保持紫色
            : isSystem
            ? octopusos?.bg?.elevated || 'background.paper' // 系统消息：elevated
            : !isUser && hasFactCard
            ? 'transparent'
            : octopusos?.bg?.paper || 'background.paper', // 助手消息：paper
          color: isUser ? 'white' : 'text.primary',
          borderRadius: 1,
          border: !isUser && hasFactCard ? 'none' : undefined,
          boxShadow: !isUser && hasFactCard ? 'none' : undefined,
          overflow: !isUser && hasFactCard ? 'visible' : undefined,
        }}
      >
        {hasWeatherCard && (
          <WeatherCard
            location={String(weatherLocation || '')}
            summary={String(weatherPayload?.summary || '')}
            condition={String(weatherPayload?.condition || '')}
            tempC={typeof weatherPayload?.temp_c === 'number' ? weatherPayload.temp_c : undefined}
            highC={typeof weatherPayload?.high_c === 'number' ? weatherPayload.high_c : undefined}
            lowC={typeof weatherPayload?.low_c === 'number' ? weatherPayload.low_c : undefined}
            windKmh={typeof weatherPayload?.wind_kmh === 'number' ? weatherPayload.wind_kmh : undefined}
            humidityPct={typeof weatherPayload?.humidity_pct === 'number' ? weatherPayload.humidity_pct : undefined}
            daily={weatherDailyData}
            hourly={weatherHourlyData}
            updatedAt={typeof weatherPayload?.updated_at === 'string' ? weatherPayload.updated_at : undefined}
            source={typeof weatherProvider === 'string' ? weatherProvider : undefined}
          />
        )}
        {hasWeatherErrorCard && (
          <Box
            sx={{
              mb: 1.25,
              p: 1.25,
              borderRadius: 1,
              border: `1px solid ${alpha(theme.palette.error.main, 0.3)}`,
              bgcolor: alpha(theme.palette.error.main, 0.08),
            }}
          >
            <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
              Weather lookup failed · {weatherLocation || 'Unknown location'}
            </Typography>
            <Typography variant="body2" sx={{ mt: 0.25 }}>
              {String(weatherPayload?.message || 'External lookup failed in current runtime')}
            </Typography>
            <Typography variant="caption" sx={{ display: 'block', opacity: 0.75, mt: 0.25 }}>
              Type: {String(weatherPayload?.error_type || 'unknown')} · Updated: {String(weatherPayload?.updated_at || '--')}
            </Typography>
          </Box>
        )}
        {hasFxCard && (
          <FactQueryCard
            title={decodeHTMLEntities(`FX · ${String(fxPayload?.base || '---')}/${String(fxPayload?.quote || '---')}`)}
            subtitle={decodeHTMLEntities(String(fxPayload?.pair || '--'))}
            headline={decodeHTMLEntities(String(fxPayload?.rate ?? '--'))}
            summary={decodeHTMLEntities(String(fxPayload?.summary || ''))}
            metrics={[
              { label: 'Base', value: decodeHTMLEntities(String(fxPayload?.base || '--')) },
              { label: 'Quote', value: decodeHTMLEntities(String(fxPayload?.quote || '--')) },
            ]}
            trend={Array.isArray(fxPayload?.trend) ? (fxPayload?.trend as Array<Record<string, unknown>>)
              .map((p) => ({
                time: String(p.time || ''),
                value: typeof p.value === 'number' ? p.value : NaN,
              }))
              .filter((p) => p.time && Number.isFinite(p.value)) : []}
            source={typeof weatherProvider === 'string' ? weatherProvider : undefined}
            updatedAt={typeof fxPayload?.updated_at === 'string' ? fxPayload.updated_at : undefined}
          />
        )}
        {hasQueryFactCard && (
          <FactQueryCard
            kind={typeof queryFactPayload?.kind === 'string' ? queryFactPayload.kind : undefined}
            title={decodeHTMLEntities(String(queryFactPayload?.title || queryFactPayload?.kind || 'Query Fact'))}
            subtitle={decodeHTMLEntities(String(queryFactPayload?.query || ''))}
            headline={
              queryFactPayload?.value !== undefined && !queryFactSafeSummary
                ? decodeHTMLEntities(String(queryFactPayload.value))
                : undefined
            }
            unit={typeof queryFactPayload?.unit === 'string' ? decodeHTMLEntities(queryFactPayload.unit) : undefined}
            summary={typeof queryFactPayload?.summary === 'string' ? decodeHTMLEntities(queryFactPayload.summary) : undefined}
            metrics={queryFactMetrics}
            trend={effectiveQueryFactTrend}
            source={typeof queryFactPayload?.source === 'string' ? decodeHTMLEntities(queryFactPayload.source) : undefined}
            updatedAt={typeof queryFactPayload?.updated_at === 'string' ? queryFactPayload.updated_at : undefined}
            safeSummary={queryFactSafeSummary}
            sensitiveExport={
              queryFactPayload?.sensitive === true
              || ['calendar', 'package'].includes(String(queryFactPayload?.kind || '').toLowerCase())
            }
          />
        )}
        {capabilityUnavailable === 'external_lookup' && (
          <Box
            sx={{
              mb: 1.25,
              p: 1.25,
              borderRadius: 1,
              border: `1px solid ${alpha(theme.palette.warning.main, 0.3)}`,
              bgcolor: alpha(theme.palette.warning.main, 0.08),
            }}
          >
            <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
              External lookup is disabled in this runtime mode
            </Typography>
          </Box>
        )}
        {!isUser && firstEvidenceId && (
          <Box sx={{ mb: 1 }} data-testid="chat-evidence-link-container">
            <Typography
              data-testid="chat-evidence-link"
              component={RouterLink}
              to={`/external-facts/replay?evidence_id=${encodeURIComponent(firstEvidenceId)}`}
              variant="caption"
              sx={{ color: 'primary.main', textDecoration: 'underline', cursor: 'pointer' }}
            >
              {t(K.page.evidenceChain.viewEvidence)}
            </Typography>
          </Box>
        )}

        {/* Message Content - Rich Markdown Rendering */}
        {showMessageBody && (
          <Box
            sx={{
              '& > *:first-of-type': { mt: 0 },
              '& > *:last-child': { mb: 0 },
              // Markdown typography styles
              '& h1, & h2, & h3, & h4, & h5, & h6': {
                mt: 2,
                mb: 1,
                fontWeight: 600,
              },
              '& h1': { fontSize: '1.8em' },
              '& h2': { fontSize: '1.5em' },
              '& h3': { fontSize: '1.3em' },
              '& p': {
                my: 1,
                lineHeight: 1.6,
              },
              '& ul, & ol': {
                my: 1,
                pl: 3,
              },
              '& li': {
                my: 0.5,
              },
              '& blockquote': {
                borderLeft: `4px solid ${theme.palette.primary.main}`,
                pl: 2,
                py: 0.5,
                my: 2,
                color: 'text.secondary',
                fontStyle: 'italic',
              },
              '& table': {
                width: '100%',
                borderCollapse: 'collapse',
                my: 2,
              },
              '& th, & td': {
                border: `1px solid ${theme.palette.divider}`,
                px: 1.5,
                py: 1,
                textAlign: 'left',
              },
              '& th': {
                bgcolor: alpha(theme.palette.primary.main, 0.1),
                fontWeight: 600,
              },
              '& a': {
                color: theme.palette.primary.main,
                textDecoration: 'none',
                '&:hover': {
                  textDecoration: 'underline',
                },
              },
              '& hr': {
                border: 'none',
                borderTop: `1px solid ${theme.palette.divider}`,
                my: 2,
              },
              // User message: simpler styling (white text on purple)
              ...(isUser && {
                '& *': { color: 'inherit' },
                '& a': { color: 'inherit', textDecoration: 'underline' },
                '& code': { bgcolor: alpha('#fff', 0.2) },
              }),
            }}
          >
            {renderedContent}
          </Box>
        )}

        {/* Timestamp */}
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mt: 0.5 }}>
          <Typography
            variant="caption"
            sx={{
              display: 'block',
              opacity: 0.7,
            }}
          >
            {new Date(message.timestamp).toLocaleTimeString('zh-CN', {
              hour: '2-digit',
              minute: '2-digit',
            })}
          </Typography>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            {isCompanyResearchReport && (
              <Tooltip title={t(K.page.chat.downloadReport)}>
                <IconButton
                  size="small"
                  onClick={handleDownloadReport}
                  sx={{ color: isUser ? 'white' : 'text.secondary', p: 0.5 }}
                >
                  <DownloadIcon fontSize="small" />
                </IconButton>
              </Tooltip>
            )}
            {messageStatus === 'superseded' && (
              <Typography variant="caption" sx={{ opacity: 0.7 }}>
                {t('page.chat.edited')}
              </Typography>
            )}
            {integrityRecoveryApplied && (
              <Typography variant="caption" sx={{ opacity: 0.75 }}>
                truncation recovered
              </Typography>
            )}
            {canEdit && (
              <Tooltip title={t('page.chat.editAndResend')}>
                <IconButton
                  size="small"
                  onClick={() => onEdit?.(message)}
                  sx={{ color: isUser ? 'white' : 'text.secondary', p: 0.5 }}
                >
                  <FormatIcon fontSize="small" />
                </IconButton>
              </Tooltip>
            )}
          </Box>
        </Box>

        {/* Metadata - Model & Tokens */}
        {message.metadata && (
          <Typography
            variant="caption"
            sx={{
              display: 'block',
              opacity: 0.6,
              fontSize: '0.7rem',
              mt: 0.25,
              wordBreak: 'break-word', // ✅ 强制长单词换行
              overflowWrap: 'anywhere', // ✅ 允许在任意位置断行
            }}
          >
            {message.metadata.model}
            {message.metadata.tokens && ` • ${message.metadata.tokens} tokens`}
            {integrityArtifactPath && ` • integrity: ${integrityArtifactPath}`}
          </Typography>
        )}
      </Paper>

      {/* Avatar - User only (on right) */}
      {isUser && (
        <Avatar sx={{ ml: 1, bgcolor: 'secondary.main', width: 36, height: 36 }}>
          <PersonIcon fontSize="small" />
        </Avatar>
      )}
    </Box>
  )
}, (prevProps, nextProps) => {
  // Re-render when core render fields change
  return prevProps.message.id === nextProps.message.id &&
         prevProps.message.content === nextProps.message.content &&
         prevProps.message.timestamp === nextProps.message.timestamp &&
         JSON.stringify(prevProps.message.metadata || {}) === JSON.stringify(nextProps.message.metadata || {})
})
