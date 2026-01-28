/**
 * Code Block Parsing Utilities
 *
 * Provides functions to parse Markdown fenced code blocks and render them
 * with syntax highlighting and preview capabilities for HTML content.
 */

/**
 * Parse Markdown fenced code blocks from text
 *
 * @param {string} input - Raw text containing code blocks
 * @returns {Array} Array of {type:'text'|'code', content|lang|code}
 *
 * @example
 * parseFencedCodeBlocks("Hello\n```js\nconsole.log('hi')\n```\nWorld")
 * // Returns:
 * // [
 * //   {type: 'text', content: 'Hello\n'},
 * //   {type: 'code', lang: 'js', code: "console.log('hi')"},
 * //   {type: 'text', content: '\nWorld'}
 * // ]
 */
function parseFencedCodeBlocks(input) {
    if (!input || typeof input !== 'string') {
        return [{type: 'text', content: input || ''}];
    }

    // Match: ```language\ncode\n```
    const re = /```([\w-]+)?\n([\s\S]*?)```/g;
    const out = [];
    let lastIndex = 0;
    let m;

    while ((m = re.exec(input)) !== null) {
        // Add text before code block
        if (m.index > lastIndex) {
            out.push({
                type: 'text',
                content: input.slice(lastIndex, m.index)
            });
        }

        // Add code block
        const lang = (m[1] || '').trim().toLowerCase();
        const code = (m[2] || '').replace(/\s+$/, ''); // Trim trailing whitespace
        out.push({
            type: 'code',
            lang: lang,
            code: code
        });

        lastIndex = re.lastIndex;
    }

    // Add remaining text
    if (lastIndex < input.length) {
        out.push({
            type: 'text',
            content: input.slice(lastIndex)
        });
    }

    return out;
}

/**
 * Check if a code block is HTML content
 *
 * @param {string} lang - Language identifier (e.g., 'html', 'javascript')
 * @param {string} code - Code content
 * @returns {boolean} True if the code block is HTML
 */
function isHtmlBlock(lang, code) {
    // Check explicit language identifier
    if (lang === 'html' || lang === 'htm') {
        return true;
    }

    // Heuristic check for HTML content when language is not specified
    if (!lang || lang === '') {
        const s = (code || '').trim().toLowerCase();
        return (
            s.startsWith('<!doctype html') ||
            s.startsWith('<html') ||
            (s.includes('<head') && s.includes('<body')) ||
            (s.includes('<div') && s.includes('</div>')) ||
            (s.includes('<p>') && s.includes('</p>'))
        );
    }

    return false;
}

/**
 * Normalize language identifiers to Prism language names
 *
 * @param {string} lang - Original language identifier
 * @returns {string} Prism language name
 */
function normalizeLang(lang) {
    if (!lang) return 'clike';

    const l = lang.toLowerCase().trim();

    // Language mappings for Prism
    const langMap = {
        'js': 'javascript',
        'ts': 'typescript',
        'py': 'python',
        'sh': 'bash',
        'shell': 'bash',
        'yml': 'yaml',
        'htm': 'markup',
        'html': 'markup',
        'xml': 'markup',
        'svg': 'markup',
        'md': 'markdown',
        'dockerfile': 'docker',
        'makefile': 'makefile',
        'c++': 'cpp',
        'c#': 'csharp',
        'go': 'go',
        'rust': 'rust',
        'ruby': 'ruby',
        'rb': 'ruby',
        'php': 'php',
        'java': 'java',
        'kt': 'kotlin',
        'swift': 'swift',
        'r': 'r',
        'matlab': 'matlab',
        'scala': 'scala',
    };

    return langMap[l] || l;
}

/**
 * Escape HTML special characters
 *
 * @param {string} text - Text to escape
 * @returns {string} Escaped text safe for HTML insertion
 */
function escapeHtmlUtil(text) {
    if (!text) return '';

    return String(text)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

/**
 * Render a code block with syntax highlighting and action buttons
 *
 * @param {Object} options - Code block options
 * @param {string} options.lang - Language identifier
 * @param {string} options.code - Code content
 * @returns {string} HTML string for the code block
 */
function renderCodeBlock({lang, code}) {
    const canPreview = isHtmlBlock(lang, code);
    const displayLang = lang || 'plaintext';
    const prismLang = normalizeLang(lang);

    // Check if code is long enough to collapse
    const lineCount = code.split('\n').length;
    const isLong = lineCount > 20;

    // Determine if this language can be formatted
    const formatableLangs = ['html', 'htm', 'markup', 'javascript', 'js', 'css', 'json', 'typescript', 'ts'];
    const canFormat = formatableLangs.includes(lang?.toLowerCase()) || formatableLangs.includes(prismLang);

    // Get current theme from localStorage
    const currentTheme = typeof localStorage !== 'undefined'
        ? (localStorage.getItem('prism-theme') || 'tomorrow')
        : 'tomorrow';

    // Generate theme options with current selection
    const themeOptions = [
        { value: 'tomorrow', label: 'Tomorrow Night' },
        { value: 'okaidia', label: 'Okaidia' },
        { value: 'dracula', label: 'Dracula' },
        { value: 'one-dark', label: 'One Dark' },
        { value: 'solarized-dark', label: 'Solarized Dark' },
        { value: 'monokai', label: 'Monokai' }
    ].map(opt =>
        `<option value="${opt.value}" ${opt.value === currentTheme ? 'selected' : ''}>${opt.label}</option>`
    ).join('');

    return `
    <div class="codeblock ${isLong ? 'collapsible' : ''}"
         data-lang="${escapeHtmlUtil(lang || '')}"
         data-snippet-id=""
         data-session-id=""
         data-message-id="">
        <div class="codeblock__hdr">
            <span class="codeblock__lang">${escapeHtmlUtil(displayLang)}</span>
            <div class="codeblock__actions">
                <select class="theme-selector js-theme-selector" title="Change theme">
                    ${themeOptions}
                </select>
                ${canPreview ? `<button class="btn-action btn-preview js-preview" title="Preview HTML">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <span>Preview</span>
                </button>` : ''}
                ${canFormat ? `<button class="btn-action btn-format js-format" title="Format code">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01" />
                    </svg>
                    <span>Format</span>
                </button>` : ''}
                <button class="btn-action btn-download js-download" title="Download code">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                    </svg>
                    <span>Download</span>
                </button>
                <button class="btn-action btn-copy js-copy" title="Copy code">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                    </svg>
                    <span>Copy</span>
                </button>
                <button class="btn-action btn-save-snippet js-save-snippet" title="Save to Snippets">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
                    </svg>
                    <span>Save</span>
                </button>
                <button class="btn-action btn-preview-snippet js-preview-snippet" title="Preview with runtime preset">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <span>Preview</span>
                </button>
                <button class="btn-action btn-make-task js-make-task" title="Create task draft from code">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
                    </svg>
                    <span>Make Task</span>
                </button>
                ${isLong ? `<button class="btn-action btn-collapse js-collapse" title="Collapse/Expand">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                    </svg>
                    <span class="collapse-text">Collapse</span>
                </button>` : ''}
            </div>
        </div>
        <pre class="line-numbers language-${prismLang} ${isLong ? 'collapsed' : ''}"><code class="language-${prismLang}">${escapeHtmlUtil(code)}</code></pre>
    </div>`;
}

/**
 * Render markdown block with action buttons
 *
 * @param {string} markdownText - Original markdown text
 * @param {string} htmlContent - Rendered HTML content
 * @returns {string} HTML string with markdown block and actions
 */
function renderMarkdownBlock(markdownText, htmlContent) {
    // Get current markdown theme from localStorage
    const currentMdTheme = typeof localStorage !== 'undefined'
        ? (localStorage.getItem('markdown-theme') || 'light')
        : 'light';

    // Generate markdown theme options with current selection
    const mdThemeOptions = [
        { value: 'light', label: 'Light' },
        { value: 'dark', label: 'Dark' },
        { value: 'github', label: 'GitHub' },
        { value: 'notion', label: 'Notion' }
    ].map(opt =>
        `<option value="${opt.value}" ${opt.value === currentMdTheme ? 'selected' : ''}>${opt.label}</option>`
    ).join('');

    return `
    <div class="mdblock" data-md-content="${escapeHtmlUtil(markdownText)}" data-theme="${currentMdTheme}">
        <div class="mdblock__content msg-markdown">${htmlContent}</div>
        <div class="mdblock__footer">
            <div class="mdblock__info">
                <span class="mdblock__label">MARKDOWN</span>
            </div>
            <div class="mdblock__actions">
                <select class="theme-selector js-md-theme-selector" title="Change theme">
                    ${mdThemeOptions}
                </select>
                <button class="btn-action btn-md-copy js-md-copy" title="Copy markdown">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                    </svg>
                    <span>Copy</span>
                </button>
                <button class="btn-action btn-md-download js-md-download" title="Download as .md">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                    </svg>
                    <span>Download</span>
                </button>
                <button class="btn-action btn-md-export js-md-export" title="Export as PDF">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    <span>Export PDF</span>
                </button>
                <button class="btn-action btn-md-print js-md-print" title="Print">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z" />
                    </svg>
                    <span>Print</span>
                </button>
            </div>
        </div>
    </div>`;
}

/**
 * Render assistant message with code block parsing and markdown support
 *
 * @param {string} text - Full message text
 * @returns {string} HTML string with parsed code blocks and rendered markdown
 */
function renderAssistantMessage(text) {
    const parts = parseFencedCodeBlocks(text);

    return parts.map(p => {
        if (p.type === 'text') {
            // Render markdown for text parts
            const trimmedContent = p.content.trim();
            if (!trimmedContent) {
                return '';
            }

            // Use marked.js to render markdown if available
            if (typeof marked !== 'undefined') {
                try {
                    // Configure marked to be safe
                    marked.setOptions({
                        breaks: true,  // Convert \n to <br>
                        gfm: true,     // GitHub Flavored Markdown
                        headerIds: false,
                        mangle: false,
                        sanitize: false  // We'll use DOMPurify if needed
                    });

                    const htmlContent = marked.parse(trimmedContent);

                    // Wrap markdown content in a block with actions
                    return renderMarkdownBlock(p.content, htmlContent);
                } catch (e) {
                    console.error('Markdown rendering error:', e);
                    // Fallback to plain text
                    const escaped = escapeHtmlUtil(p.content);
                    return `<div class="msg-text">${escaped.replace(/\n/g, '<br>')}</div>`;
                }
            } else {
                // Fallback if marked.js is not loaded
                const escaped = escapeHtmlUtil(p.content);
                return `<div class="msg-text">${escaped.replace(/\n/g, '<br>')}</div>`;
            }
        }
        return renderCodeBlock(p);
    }).join('');
}

// Make functions available globally (for non-module scripts)
window.CodeBlockUtils = {
    parseFencedCodeBlocks,
    isHtmlBlock,
    escapeHtml: escapeHtmlUtil,
    normalizeLang,
    renderCodeBlock,
    renderMarkdownBlock,
    renderAssistantMessage
};
