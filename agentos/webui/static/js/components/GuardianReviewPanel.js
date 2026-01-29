/**
 * GuardianReviewPanel - Guardian 验收审查记录面板
 *
 * Task #3: WebUI Guardian Reviews Tab
 *
 * 职责：
 * - 展示 Guardian Reviews Timeline
 * - 展示 Overall Verdict 和 Confidence
 * - 提供 Evidence 展开/折叠功能
 * - 优雅的空态和错误处理
 *
 * Usage:
 *   const panel = new GuardianReviewPanel({
 *       container: document.getElementById('container'),
 *       verdictData: { overall_verdict: 'PASS', confidence: 0.95, total_reviews: 3 },
 *       reviews: [...]
 *   });
 *   panel.render();
 */

class GuardianReviewPanel {
    /**
     * 构造 GuardianReviewPanel
     *
     * @param {Object} options - 配置选项
     * @param {HTMLElement} options.container - 容器元素
     * @param {Object} options.verdictData - 验收摘要数据
     * @param {Array} options.reviews - 审查记录列表
     */
    constructor({ container, verdictData, reviews }) {
        this.container = container;
        this.verdictData = verdictData;
        this.reviews = reviews;
    }

    /**
     * 渲染面板
     */
    render() {
        if (this.reviews.length === 0) {
            this.renderEmptyState();
            return;
        }

        const html = `
            ${this.renderOverallStatus()}
            ${this.renderTimeline()}
        `;

        this.container.innerHTML = html;
        this.attachEventListeners();
    }

    /**
     * 渲染整体状态卡片
     */
    renderOverallStatus() {
        const { latest_verdict, total_reviews } = this.verdictData;

        // 计算整体置信度（基于最新的 review 或所有 reviews 平均）
        let avgConfidence = 0;
        if (this.reviews.length > 0) {
            const sum = this.reviews.reduce((acc, r) => acc + (r.confidence || 0), 0);
            avgConfidence = sum / this.reviews.length;
        }

        // 如果没有 overall_verdict，使用 latest_verdict
        const overallVerdict = latest_verdict || 'UNKNOWN';

        return `
            <div class="guardian-overall-status">
                <div class="status-header">
                    <h3>Overall Status</h3>
                    ${this.renderVerdictBadge(overallVerdict)}
                    <span class="review-count">${total_reviews} Guardian${total_reviews > 1 ? 's' : ''}</span>
                </div>
                <div class="confidence-bar">
                    <label>Confidence</label>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${avgConfidence * 100}%"></div>
                    </div>
                    <span class="confidence-value">${Math.round(avgConfidence * 100)}%</span>
                </div>
            </div>
        `;
    }

    /**
     * 渲染时间线
     */
    renderTimeline() {
        const sortedReviews = [...this.reviews].sort((a, b) =>
            new Date(b.created_at) - new Date(a.created_at)
        );

        const timelineItems = sortedReviews.map(review =>
            this.renderTimelineItem(review)
        ).join('');

        return `
            <div class="guardian-timeline">
                <h4>Review Timeline</h4>
                <div class="timeline-items">
                    ${timelineItems}
                </div>
            </div>
        `;
    }

    /**
     * 渲染单个时间线条目
     */
    renderTimelineItem(review) {
        const timestamp = this.formatTimestamp(review.created_at);
        const evidenceId = `evidence-${review.review_id}`;

        return `
            <div class="timeline-item" data-review-id="${review.review_id}">
                <div class="timeline-marker ${review.verdict.toLowerCase()}"></div>
                <div class="timeline-content">
                    <div class="timeline-header">
                        <span class="timestamp">${timestamp}</span>
                        <span class="review-type-badge ${review.review_type.toLowerCase()}">${review.review_type}</span>
                        ${this.renderVerdictBadge(review.verdict)}
                    </div>
                    <div class="timeline-body">
                        <div class="guardian-info">
                            <strong>Guardian:</strong> <code>${this.escapeHtml(review.guardian_id)}</code>
                        </div>
                        <div class="confidence-info">
                            <strong>Confidence:</strong> ${Math.round(review.confidence * 100)}%
                        </div>
                        ${review.rule_snapshot_id ? `
                            <div class="rule-snapshot">
                                <strong>Rule Snapshot:</strong> <code>${this.escapeHtml(review.rule_snapshot_id)}</code>
                            </div>
                        ` : ''}
                        <button class="btn-expand-evidence" data-evidence-id="${evidenceId}">
                            View Evidence <span class="material-icons" style="font-size: 16px;">expand_more</span>
                        </button>
                        <div class="evidence-detail" id="${evidenceId}" style="display: none;">
                            <pre>${this.escapeHtml(JSON.stringify(review.evidence, null, 2))}</pre>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * 渲染验收结论徽章
     */
    renderVerdictBadge(verdict) {
        const colorMap = {
            'PASS': 'success',
            'FAIL': 'danger',
            'NEEDS_REVIEW': 'warning',
            'UNKNOWN': 'secondary'
        };
        const color = colorMap[verdict] || 'secondary';

        return `<span class="badge badge-${color}">${verdict}</span>`;
    }

    /**
     * 渲染空状态
     */
    renderEmptyState() {
        this.container.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">🛡️</div>
                <h3>No Guardian Reviews Yet</h3>
                <p>This task hasn't been reviewed by any Guardian yet.</p>
                <p class="empty-hint">
                    Guardian reviews provide verification and acceptance records
                    for governance and audit purposes.
                </p>
            </div>
        `;
    }

    /**
     * 附加事件监听器
     */
    attachEventListeners() {
        // Toggle evidence display
        const evidenceButtons = this.container.querySelectorAll('.btn-expand-evidence');
        evidenceButtons.forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                const evidenceId = btn.dataset.evidenceId;
                const evidenceDiv = document.getElementById(evidenceId);
                const isVisible = evidenceDiv.style.display !== 'none';

                evidenceDiv.style.display = isVisible ? 'none' : 'block';
                const icon = isVisible ? 'expand_more' : 'expand_less';
                btn.innerHTML = `${isVisible ? 'View' : 'Hide'} Evidence <span class="material-icons" style="font-size: 16px;">${icon}</span>`;
            });
        });
    }

    /**
     * 格式化时间戳
     */
    formatTimestamp(timestamp) {
        if (!timestamp) return 'N/A';

        try {
            const date = new Date(timestamp);
            return date.toLocaleString('en-US', {
                year: 'numeric',
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
            });
        } catch (e) {
            return timestamp;
        }
    }

    /**
     * HTML 转义（防止 XSS）
     */
    escapeHtml(text) {
        if (typeof text !== 'string') {
            text = String(text);
        }

        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };

        return text.replace(/[&<>"']/g, m => map[m]);
    }
}

// Export to global scope
window.GuardianReviewPanel = GuardianReviewPanel;
