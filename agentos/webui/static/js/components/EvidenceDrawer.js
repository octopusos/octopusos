/**
 * EvidenceDrawer - Trusted Progress Evidence Viewer
 *
 * PR-V6: Evidence Drawer
 *
 * Displays checkpoint evidence in a user-friendly drawer UI
 * - Shows 4 evidence types: artifact, command, db_row, timestamp
 * - Provides 3-tier information hierarchy (conclusion → summary → details)
 * - Uses visual badges for verification status
 * - Non-technical friendly with collapsible advanced info
 *
 * Usage:
 * ```javascript
 * const drawer = new EvidenceDrawer('evidence-drawer-container');
 * await drawer.open('ckpt_abc123');
 * drawer.close();
 * ```
 */

class EvidenceDrawer {
    /**
     * Create evidence drawer
     *
     * @param {string} containerId - Container element ID
     */
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        if (!this.container) {
            throw new Error(`Container not found: ${containerId}`);
        }

        this.isOpen = false;
        this.currentCheckpoint = null;
        this.evidenceData = null;

        this.init();
    }

    /**
     * Initialize drawer
     */
    init() {
        this.render();
        this.setupEventListeners();
    }

    /**
     * Render drawer structure
     */
    render() {
        this.container.innerHTML = `
            <!-- Overlay -->
            <div class="evidence-drawer-overlay" id="evidence-drawer-overlay"></div>

            <!-- Drawer -->
            <div class="evidence-drawer" id="evidence-drawer">
                <div class="drawer-header">
                    <h2 class="drawer-title">证据查看器</h2>
                    <button class="drawer-close-btn" id="evidence-drawer-close" title="关闭">
                        <span class="material-icons md-24">close</span>
                    </button>
                </div>

                <div class="drawer-body" id="evidence-drawer-body">
                    <div class="drawer-loading">
                        <div class="spinner"></div>
                        <p>加载证据中...</p>
                    </div>
                </div>

                <div class="drawer-footer">
                    <button class="btn-text" id="evidence-toggle-advanced">
                        <span class="material-icons md-18">visibility</span>
                        显示高级信息
                    </button>
                </div>
            </div>
        `;

        this.overlayEl = this.container.querySelector('#evidence-drawer-overlay');
        this.drawerEl = this.container.querySelector('#evidence-drawer');
        this.bodyEl = this.container.querySelector('#evidence-drawer-body');
        this.closeBtn = this.container.querySelector('#evidence-drawer-close');
        this.toggleAdvancedBtn = this.container.querySelector('#evidence-toggle-advanced');
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Close on overlay click
        this.overlayEl.addEventListener('click', () => this.close());

        // Close button
        this.closeBtn.addEventListener('click', () => this.close());

        // Toggle advanced info
        this.toggleAdvancedBtn.addEventListener('click', () => this.toggleAdvancedInfo());

        // ESC key to close
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isOpen) {
                this.close();
            }
        });
    }

    /**
     * Open drawer with checkpoint evidence
     *
     * @param {string} checkpointId - Checkpoint ID
     */
    async open(checkpointId) {
        console.log(`[EvidenceDrawer] Opening for checkpoint: ${checkpointId}`);

        this.currentCheckpoint = checkpointId;
        this.isOpen = true;

        // Show drawer with loading state
        this.overlayEl.classList.add('visible');
        this.drawerEl.classList.add('open');

        // Fetch evidence
        try {
            this.evidenceData = await this.fetchEvidence(checkpointId);
            this.renderEvidence(this.evidenceData);
        } catch (error) {
            console.error('[EvidenceDrawer] Failed to fetch evidence:', error);
            this.renderError(error);
        }
    }

    /**
     * Close drawer
     */
    close() {
        console.log('[EvidenceDrawer] Closing');

        this.isOpen = false;
        this.overlayEl.classList.remove('visible');
        this.drawerEl.classList.remove('open');
        this.currentCheckpoint = null;
        this.evidenceData = null;

        // Reset advanced info state
        this.drawerEl.classList.remove('advanced-visible');
        this.toggleAdvancedBtn.innerHTML = `
            <span class="material-icons md-18">visibility</span>
            显示高级信息
        `;
    }

    /**
     * Fetch evidence from API
     *
     * @param {string} checkpointId - Checkpoint ID
     * @returns {Promise<Object>} Evidence data
     */
    async fetchEvidence(checkpointId) {
        const response = await fetch(`/api/checkpoints/${checkpointId}/evidence`);

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to fetch evidence');
        }

        return await response.json();
    }

    /**
     * Render evidence content
     *
     * @param {Object} data - Evidence data from API
     */
    renderEvidence(data) {
        const statusBadge = this.renderStatusBadge(data.status);
        const evidenceList = this.renderEvidenceList(data.items);
        const metadata = this.renderMetadata(data);

        this.bodyEl.innerHTML = `
            <div class="evidence-content">
                <!-- Status Badge -->
                ${statusBadge}

                <!-- Checkpoint Info -->
                <div class="checkpoint-info">
                    <div class="info-row">
                        <span class="info-label">Checkpoint ID:</span>
                        <code class="info-value">${data.checkpoint_id}</code>
                        <button class="btn-icon btn-copy" data-copy="${data.checkpoint_id}" title="复制">
                            <span class="material-icons md-16">content_copy</span>
                        </button>
                    </div>
                    <div class="info-row">
                        <span class="info-label">类型:</span>
                        <span class="info-value">${this.formatCheckpointType(data.checkpoint_type)}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">序号:</span>
                        <span class="info-value">#${data.sequence_number}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">创建时间:</span>
                        <span class="info-value">${this.formatTimestamp(data.created_at)}</span>
                    </div>
                </div>

                <!-- Evidence List -->
                <div class="evidence-section">
                    <h3>证据列表 (${data.items.length} 项)</h3>
                    ${evidenceList}
                </div>

                <!-- Metadata (Advanced) -->
                <div class="evidence-advanced">
                    ${metadata}
                </div>
            </div>
        `;

        // Setup copy buttons
        this.setupCopyButtons();

        // Setup evidence item toggles
        this.setupEvidenceToggles();
    }

    /**
     * Render status badge
     *
     * @param {string} status - Status: verified, invalid, pending
     * @returns {string} HTML
     */
    renderStatusBadge(status) {
        const config = {
            verified: {
                icon: 'check_circle',
                text: '已验证',
                description: '所有证据已通过验证，此检查点可安全恢复'
            },
            invalid: {
                icon: 'error',
                text: '失效（需回滚）',
                description: '部分证据验证失败，此检查点无法恢复'
            },
            pending: {
                icon: 'schedule',
                text: '待验证',
                description: '证据尚未验证'
            }
        };

        const { icon, text, description } = config[status] || config.pending;

        return `
            <div class="status-badge status-${status}">
                <div class="badge-content">
                    <span class="material-icons md-24">${icon}</span>
                    <div class="badge-text">
                        <h3>${text}</h3>
                        <p>${description}</p>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Render evidence list
     *
     * @param {Array} items - Evidence items
     * @returns {string} HTML
     */
    renderEvidenceList(items) {
        if (!items || items.length === 0) {
            return '<p class="empty-message">无证据</p>';
        }

        return items.map((item, index) => this.renderEvidenceItem(item, index)).join('');
    }

    /**
     * Render single evidence item
     *
     * @param {Object} item - Evidence item
     * @param {number} index - Item index
     * @returns {string} HTML
     */
    renderEvidenceItem(item, index) {
        const statusIcon = item.verified ? 'check_circle' : 'cancel';
        const statusClass = item.verified ? 'verified' : 'failed';
        const typeLabel = this.getEvidenceTypeLabel(item.type);
        const details = this.renderEvidenceDetails(item);

        return `
            <div class="evidence-item" data-index="${index}">
                <div class="evidence-header" data-toggle="evidence-${index}">
                    <div class="evidence-header-left">
                        <span class="material-icons md-20 evidence-status-icon ${statusClass}">${statusIcon}</span>
                        <span class="evidence-type">${typeLabel}</span>
                    </div>
                    <div class="evidence-header-right">
                        <span class="evidence-description">${item.description}</span>
                        <span class="material-icons md-18 toggle-icon">expand_more</span>
                    </div>
                </div>
                <div class="evidence-details" id="evidence-${index}" style="display: none;">
                    ${details}
                    ${item.verification_error ? `
                        <div class="verification-error">
                            <span class="material-icons md-16">error_outline</span>
                            <span>${item.verification_error}</span>
                        </div>
                    ` : ''}
                </div>
            </div>
        `;
    }

    /**
     * Render evidence details based on type
     *
     * @param {Object} item - Evidence item
     * @returns {string} HTML
     */
    renderEvidenceDetails(item) {
        const { type, details } = item;

        switch (type) {
            case 'artifact':
                return this.renderArtifactDetails(details);
            case 'command':
                return this.renderCommandDetails(details);
            case 'db_row':
                return this.renderDbRowDetails(details);
            case 'file_sha256':
                return this.renderFileSha256Details(details);
            default:
                return this.renderGenericDetails(details);
        }
    }

    /**
     * Render artifact evidence details
     */
    renderArtifactDetails(details) {
        return `
            <div class="detail-row">
                <span class="detail-label">文件路径:</span>
                <code class="detail-value">${details.path}</code>
                <button class="btn-icon btn-copy" data-copy="${details.path}">
                    <span class="material-icons md-14">content_copy</span>
                </button>
            </div>
            <div class="detail-row">
                <span class="detail-label">类型:</span>
                <span class="detail-value">${details.type}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">存在:</span>
                <span class="detail-value">${details.exists ? '✓ 是' : '✗ 否'}</span>
            </div>
        `;
    }

    /**
     * Render command evidence details
     */
    renderCommandDetails(details) {
        return `
            <div class="detail-row">
                <span class="detail-label">命令:</span>
                <code class="detail-value">${details.command}</code>
                <button class="btn-icon btn-copy" data-copy="${details.command}">
                    <span class="material-icons md-14">content_copy</span>
                </button>
            </div>
            <div class="detail-row">
                <span class="detail-label">退出码:</span>
                <code class="detail-value ${details.exit_code === 0 ? 'success' : 'error'}">${details.exit_code}</code>
            </div>
            ${details.stdout_preview ? `
                <div class="detail-row">
                    <span class="detail-label">输出摘要:</span>
                    <pre class="detail-value">${details.stdout_preview}</pre>
                </div>
            ` : ''}
            ${details.stderr_preview ? `
                <div class="detail-row">
                    <span class="detail-label">错误输出:</span>
                    <pre class="detail-value error">${details.stderr_preview}</pre>
                </div>
            ` : ''}
        `;
    }

    /**
     * Render database row evidence details
     */
    renderDbRowDetails(details) {
        return `
            <div class="detail-row">
                <span class="detail-label">表:</span>
                <code class="detail-value">${details.table}</code>
            </div>
            <div class="detail-row">
                <span class="detail-label">WHERE:</span>
                <pre class="detail-value">${JSON.stringify(details.where, null, 2)}</pre>
            </div>
            <div class="detail-row">
                <span class="detail-label">期望值:</span>
                <pre class="detail-value">${JSON.stringify(details.values, null, 2)}</pre>
            </div>
        `;
    }

    /**
     * Render file SHA256 evidence details
     */
    renderFileSha256Details(details) {
        return `
            <div class="detail-row">
                <span class="detail-label">文件路径:</span>
                <code class="detail-value">${details.path}</code>
                <button class="btn-icon btn-copy" data-copy="${details.path}">
                    <span class="material-icons md-14">content_copy</span>
                </button>
            </div>
            <div class="detail-row">
                <span class="detail-label">SHA256:</span>
                <code class="detail-value sha256">${details.sha256_short}</code>
                <button class="btn-icon btn-copy" data-copy="${details.sha256}" title="复制完整哈希">
                    <span class="material-icons md-14">content_copy</span>
                </button>
            </div>
        `;
    }

    /**
     * Render generic evidence details
     */
    renderGenericDetails(details) {
        return `
            <div class="detail-row">
                <pre class="detail-value">${JSON.stringify(details, null, 2)}</pre>
            </div>
        `;
    }

    /**
     * Render metadata (advanced info)
     */
    renderMetadata(data) {
        return `
            <h3>高级信息</h3>
            <div class="metadata-grid">
                <div class="metadata-item">
                    <span class="metadata-label">Task ID:</span>
                    <code class="metadata-value">${data.task_id}</code>
                </div>
                <div class="metadata-item">
                    <span class="metadata-label">验证统计:</span>
                    <span class="metadata-value">
                        ${data.summary.verified}/${data.summary.total} 通过
                        ${data.summary.failed > 0 ? `, ${data.summary.failed} 失败` : ''}
                    </span>
                </div>
                ${data.last_verified_at ? `
                    <div class="metadata-item">
                        <span class="metadata-label">最后验证:</span>
                        <span class="metadata-value">${this.formatTimestamp(data.last_verified_at)}</span>
                    </div>
                ` : ''}
            </div>
        `;
    }

    /**
     * Render error message
     */
    renderError(error) {
        this.bodyEl.innerHTML = `
            <div class="evidence-error">
                <span class="material-icons md-48">error_outline</span>
                <h3>加载失败</h3>
                <p>${error.message || '未知错误'}</p>
                <button class="btn-primary" onclick="location.reload()">刷新页面</button>
            </div>
        `;
    }

    /**
     * Toggle advanced info visibility
     */
    toggleAdvancedInfo() {
        const isVisible = this.drawerEl.classList.toggle('advanced-visible');

        this.toggleAdvancedBtn.innerHTML = isVisible
            ? `<span class="material-icons md-18">visibility_off</span> 隐藏高级信息`
            : `<span class="material-icons md-18">visibility</span> 显示高级信息`;
    }

    /**
     * Setup copy buttons
     */
    setupCopyButtons() {
        const copyButtons = this.bodyEl.querySelectorAll('.btn-copy');

        copyButtons.forEach(btn => {
            btn.addEventListener('click', async (e) => {
                e.stopPropagation();
                const text = btn.getAttribute('data-copy');
                await this.copyToClipboard(text);

                // Visual feedback
                const icon = btn.querySelector('.material-icons');
                icon.textContent = 'check';
                setTimeout(() => {
                    icon.textContent = 'content_copy';
                }, 1000);
            });
        });
    }

    /**
     * Setup evidence item toggles
     */
    setupEvidenceToggles() {
        const headers = this.bodyEl.querySelectorAll('[data-toggle]');

        headers.forEach(header => {
            header.addEventListener('click', () => {
                const targetId = header.getAttribute('data-toggle');
                const details = document.getElementById(targetId);
                const icon = header.querySelector('.toggle-icon');

                if (details.style.display === 'none') {
                    details.style.display = 'block';
                    icon.textContent = 'expand_less';
                } else {
                    details.style.display = 'none';
                    icon.textContent = 'expand_more';
                }
            });
        });
    }

    /**
     * Copy text to clipboard
     */
    async copyToClipboard(text) {
        try {
            await navigator.clipboard.writeText(text);
            console.log('[EvidenceDrawer] Copied to clipboard:', text.substring(0, 50));
        } catch (error) {
            console.error('[EvidenceDrawer] Failed to copy:', error);
            // Fallback for older browsers
            const textarea = document.createElement('textarea');
            textarea.value = text;
            document.body.appendChild(textarea);
            textarea.select();
            document.execCommand('copy');
            document.body.removeChild(textarea);
        }
    }

    /**
     * Get evidence type label
     */
    getEvidenceTypeLabel(type) {
        const labels = {
            'artifact': '📦 文件证据',
            'command': '⚙️ 命令执行',
            'db_row': '💾 数据库记录',
            'file_sha256': '🔐 文件哈希',
            'timestamp': '🕐 时间戳'
        };
        return labels[type] || type;
    }

    /**
     * Format checkpoint type
     */
    formatCheckpointType(type) {
        const labels = {
            'iteration_start': '迭代开始',
            'iteration_end': '迭代结束',
            'tool_executed': '工具执行',
            'llm_response': 'LLM 响应',
            'approval_point': '审批点',
            'state_transition': '状态转换',
            'manual_checkpoint': '手动检查点',
            'error_boundary': '错误边界'
        };
        return labels[type] || type;
    }

    /**
     * Format timestamp
     */
    formatTimestamp(timestamp) {
        if (!timestamp) return 'N/A';

        const date = new Date(timestamp);
        const now = new Date();
        const diffMs = now - date;
        const diffSec = Math.floor(diffMs / 1000);
        const diffMin = Math.floor(diffSec / 60);
        const diffHour = Math.floor(diffMin / 60);

        if (diffSec < 60) return `${diffSec} 秒前`;
        if (diffMin < 60) return `${diffMin} 分钟前`;
        if (diffHour < 24) return `${diffHour} 小时前`;

        return date.toLocaleString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        });
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = EvidenceDrawer;
}
