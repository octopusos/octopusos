/**
 * ConfigView - Configuration Management UI
 *
 * PR-4: Skills/Memory/Config Module (Refactored for Control Surface Consistency)
 * Coverage: GET /api/config
 *
 * 改造要点：
 * - 移除 Tab 系统，Raw JSON 改为 Modal
 * - Application Settings 改为 Property Grid
 * - Environment Variables 添加 Filter + Show all
 * - 视觉风格和 RuntimeView 对齐
 */

class ConfigView {
    constructor(container) {
        this.container = container;
        this.config = null;
        this.migrationsStatus = null;
        this.envLimit = 20; // 默认显示前 20 条环境变量
        this.envFilter = ''; // 搜索过滤器

        this.init();
    }

    init() {
        this.container.innerHTML = `
            <div class="config-view">
                <!-- 增强的 PageHeader -->
                <div class="view-header">
                    <div>
                        <h2>Configuration</h2>
                        <p class="text-sm text-gray-600 mt-1">
                            Runtime configuration snapshot (read-only)
                        </p>
                    </div>
                    <div class="header-actions">
                        <button class="btn-refresh" id="config-refresh">
                            <span class="icon"><span class="material-icons md-18">refresh</span></span> Refresh
                        </button>
                        <button class="btn-secondary" id="config-view-raw">
                            <span class="icon"><span class="material-icons md-18">code</span></span> View Raw JSON
                        </button>
                        <button class="btn-secondary" id="config-download">
                            <span class="icon"><span class="material-icons md-18">download</span></span> Download
                        </button>
                    </div>
                </div>

                <!-- Content Container (只有 Structured View，移除 Tab) -->
                <div id="config-content" class="config-content">
                    <div class="text-center py-8 text-gray-500">
                        Loading configuration...
                    </div>
                </div>

                <!-- Raw JSON Modal -->
                <div id="raw-json-modal" class="modal" style="display:none">
                    <div class="modal-overlay" id="raw-json-modal-overlay"></div>
                    <div class="modal-content modal-lg">
                        <div class="modal-header">
                            <h3>Full Configuration (JSON)</h3>
                            <button class="modal-close" id="raw-json-modal-close">×</button>
                        </div>
                        <div class="modal-body">
                            <div class="flex justify-end mb-3">
                                <button class="btn-sm btn-secondary" id="copy-raw-json">
                                    <span class="material-icons md-18">content_copy</span> Copy to Clipboard
                                </button>
                            </div>
                            <div class="json-viewer-container" id="raw-json-content"></div>
                            <p class="text-xs text-gray-500 mt-3">
                                ⓘ This is a read-only view of the current configuration.
                            </p>
                        </div>
                    </div>
                </div>
            </div>
        `;

        this.setupEventListeners();
        this.loadConfig();
    }

    setupEventListeners() {
        // Refresh button
        const refreshBtn = this.container.querySelector('#config-refresh');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.loadConfig(true));
        }

        // View Raw JSON button (打开 Modal)
        const viewRawBtn = this.container.querySelector('#config-view-raw');
        if (viewRawBtn) {
            viewRawBtn.addEventListener('click', () => this.showRawJsonModal());
        }

        // Download button
        const downloadBtn = this.container.querySelector('#config-download');
        if (downloadBtn) {
            downloadBtn.addEventListener('click', () => this.downloadConfig());
        }

        // Modal close handlers
        const modalOverlay = this.container.querySelector('#raw-json-modal-overlay');
        const modalClose = this.container.querySelector('#raw-json-modal-close');
        if (modalOverlay) {
            modalOverlay.addEventListener('click', () => this.hideRawJsonModal());
        }
        if (modalClose) {
            modalClose.addEventListener('click', () => this.hideRawJsonModal());
        }
    }

    async loadConfig(forceRefresh = false) {
        try {
            const contentDiv = this.container.querySelector('#config-content');
            if (!contentDiv) return;

            // Show loading state
            contentDiv.innerHTML = '<div class="text-center py-8 text-gray-500">Loading configuration...</div>';

            // Call APIs in parallel
            const [configResponse, migrationsResponse] = await Promise.all([
                apiClient.get('/api/config'),
                apiClient.get('/api/config/migrations')
            ]);

            if (!configResponse.ok) {
                throw new Error(configResponse.error || 'Failed to load configuration');
            }

            this.config = configResponse.data || {};
            this.migrationsStatus = migrationsResponse.ok ? migrationsResponse.data : null;

            // 渲染 Structured View（唯一视图）
            this.renderStructuredView(contentDiv);

            // Show success toast (only on manual refresh)
            if (forceRefresh && window.showToast) {
                window.showToast('Configuration reloaded', 'success', 1500);
            }

        } catch (error) {
            console.error('Failed to load configuration:', error);

            const contentDiv = this.container.querySelector('#config-content');
            if (contentDiv) {
                contentDiv.innerHTML = `
                    <div class="text-center py-8 text-red-600">
                        <p>Failed to load configuration</p>
                        <p class="text-sm mt-2">${error.message}</p>
                    </div>
                `;
            }

            if (window.showToast) {
                window.showToast(`Error: ${error.message}`, 'error');
            }
        }
    }

    renderStructuredView(container) {
        if (!this.config) return;

        const html = `
            <div class="config-structured">
                <!-- System Overview -->
                <div class="config-section">
                    <h3 class="config-section-title">System Overview</h3>
                    <div class="config-card">
                        <div class="detail-grid">
                            <div class="detail-item">
                                <span class="detail-label">AgentOS Version</span>
                                <span class="detail-value font-semibold">${this.config.version || 'Unknown'}</span>
                            </div>
                            <div class="detail-item">
                                <span class="detail-label">Python Version</span>
                                <span class="detail-value">${this.config.python_version ? this.config.python_version.split(' ')[0] : 'Unknown'}</span>
                            </div>
                            <div class="detail-item">
                                <span class="detail-label">Runtime Mode</span>
                                <span class="detail-value">Local (Open)</span>
                            </div>
                            <div class="detail-item">
                                <span class="detail-label">Last Loaded</span>
                                <span class="detail-value">${new Date().toLocaleString()}</span>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Application Settings (Property Grid，不再用 JsonViewer) -->
                ${this.config.settings ? `
                    <div class="config-section">
                        <h3 class="config-section-title">Application Settings</h3>
                        <div class="config-card">
                            <div class="detail-grid">
                                ${Object.entries(this.config.settings).map(([key, value]) => `
                                    <div class="detail-item">
                                        <span class="detail-label">${this.formatLabel(key)}</span>
                                        <span class="detail-value">${this.escapeHtml(String(value))}</span>
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                        <p class="text-xs text-gray-500 mt-2">
                            🔒 Settings are read-only. Edit the config file to make changes.
                        </p>
                    </div>
                ` : ''}

                <!-- Environment Variables (添加 Filter + Show all) -->
                ${this.config.environment && Object.keys(this.config.environment).length > 0 ?
                    this.renderEnvironmentVariables() : ''}

                <!-- Database Migrations -->
                ${this.migrationsStatus ? this.renderDatabaseMigrations() : ''}

                <!-- Quick Actions -->
                <div class="config-section">
                    <h3 class="config-section-title">Quick Actions</h3>
                    <div class="config-card">
                        <div class="flex gap-3 flex-wrap">
                            <button class="btn-secondary" id="view-providers">
                                <span class="material-icons md-18">power</span> View Providers
                            </button>
                            <button class="btn-secondary" id="view-selfcheck">
                                <span class="material-icons md-18">done</span> Run Self-check
                            </button>
                            <button class="btn-secondary" id="download-config-footer">
                                <span class="material-icons md-18">download</span> Download Config
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        container.innerHTML = html;

        // Setup Quick Actions
        this.setupQuickActions(container);

        // Setup Environment Filter
        if (this.config.environment && Object.keys(this.config.environment).length > 0) {
            this.setupEnvironmentFilter(container);
        }
    }

    renderDatabaseMigrations() {
        if (!this.migrationsStatus) return '';

        const status = this.migrationsStatus;
        const statusBadge = status.needs_migration
            ? '<span class="badge badge-warning">Pending Migration</span>'
            : '<span class="badge badge-success">Up to Date</span>';

        return `
            <div class="config-section">
                <div class="flex items-center justify-between mb-3">
                    <h3 class="config-section-title">
                        Database Migrations
                        ${statusBadge}
                    </h3>
                </div>
                <div class="config-card">
                    <div class="detail-grid mb-4">
                        <div class="detail-item">
                            <span class="detail-label">Database Path</span>
                            <span class="detail-value font-mono text-xs">${this.escapeHtml(status.db_path)}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Current Version</span>
                            <span class="detail-value font-semibold">${status.current_version ? 'v' + status.current_version : 'Unknown'}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Latest Version</span>
                            <span class="detail-value font-semibold">${status.latest_version ? 'v' + status.latest_version : 'Unknown'}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Pending Migrations</span>
                            <span class="detail-value ${status.pending_count > 0 ? 'text-orange-600 font-semibold' : ''}">${status.pending_count}</span>
                        </div>
                    </div>

                    ${status.needs_migration ? `
                        <div class="bg-orange-50 border border-orange-200 rounded p-3 mb-4">
                            <div class="flex items-start gap-2">
                                <span class="material-icons md-18 text-orange-600">warning</span>
                                <div class="flex-1">
                                    <p class="text-sm text-orange-800 font-medium">Database migration required</p>
                                    <p class="text-xs text-orange-700 mt-1">
                                        Your database is on v${status.current_version}, but v${status.latest_version} is available.
                                        ${status.pending_count} migration(s) need to be applied.
                                    </p>
                                </div>
                            </div>
                        </div>
                    ` : ''}

                    <!-- Available Migrations List -->
                    <div class="mb-4">
                        <h4 class="text-sm font-semibold text-gray-700 mb-2">Available Migrations</h4>
                        <div class="max-h-64 overflow-y-auto">
                            <table class="config-table">
                                <thead>
                                    <tr>
                                        <th>Version</th>
                                        <th>Description</th>
                                        <th>Status</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${status.migrations.map(migration => {
                                        const currentParts = status.current_version ?
                                            status.current_version.split('.').map(Number) : [0, 0, 0];
                                        const migrationParts = migration.version.split('.').map(Number);

                                        const isApplied = migrationParts[0] < currentParts[0] ||
                                                         (migrationParts[0] === currentParts[0] && migrationParts[1] < currentParts[1]) ||
                                                         (migrationParts[0] === currentParts[0] && migrationParts[1] === currentParts[1] && migrationParts[2] <= currentParts[2]);

                                        return `
                                            <tr class="${isApplied ? 'opacity-60' : ''}">
                                                <td class="font-mono text-xs">v${migration.version}</td>
                                                <td class="text-xs">${this.escapeHtml(migration.description)}</td>
                                                <td>
                                                    ${isApplied
                                                        ? '<span class="badge badge-success badge-sm">Applied</span>'
                                                        : '<span class="badge badge-warning badge-sm">Pending</span>'}
                                                </td>
                                            </tr>
                                        `;
                                    }).join('')}
                                </tbody>
                            </table>
                        </div>
                    </div>

                    <!-- Migration Actions -->
                    <div class="flex gap-2">
                        ${status.needs_migration ? `
                            <button class="btn-primary" id="run-migrations">
                                <span class="material-icons md-18">upgrade</span> Run Migrations
                            </button>
                        ` : ''}
                        <button class="btn-secondary" id="refresh-migrations">
                            <span class="material-icons md-18">refresh</span> Refresh Status
                        </button>
                    </div>
                </div>
                <p class="text-xs text-gray-500 mt-2">
                    ⓘ Database migrations are applied automatically. Manual migration is only needed in special cases.
                </p>
            </div>
        `;
    }

    renderEnvironmentVariables() {
        if (!this.config.environment) return '';

        const allEnvs = Object.entries(this.config.environment).sort(([a], [b]) => a.localeCompare(b));
        const totalCount = allEnvs.length;
        const displayedEnvs = allEnvs.slice(0, this.envLimit);
        const hasMore = totalCount > this.envLimit;

        return `
            <div class="config-section">
                <div class="flex items-center justify-between mb-3">
                    <h3 class="config-section-title">
                        Environment Variables
                        <span class="badge badge-info ml-2" id="env-count">${totalCount} variables</span>
                    </h3>
                    <input
                        type="text"
                        id="env-filter"
                        placeholder="🔍 Filter variables..."
                        class="input-sm"
                        style="width: 240px;"
                        value="${this.envFilter}"
                    />
                </div>
                <div class="config-card">
                    <div class="max-h-96 overflow-y-auto">
                        <table class="config-table" id="env-table">
                            <thead>
                                <tr>
                                    <th>Variable</th>
                                    <th>Value</th>
                                    <th style="width: 60px;"></th>
                                </tr>
                            </thead>
                            <tbody>
                                ${displayedEnvs.map(([key, value]) => `
                                    <tr data-env-key="${this.escapeHtml(key.toLowerCase())}">
                                        <td class="font-mono text-xs">${this.escapeHtml(key)}</td>
                                        <td class="font-mono text-xs text-gray-700">${this.escapeHtml(String(value))}</td>
                                        <td>
                                            <button class="btn-icon" title="Copy value" data-copy-value="${this.escapeHtml(String(value))}">
                                                <span class="material-icons md-14">content_copy</span>
                                            </button>
                                        </td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                </div>
                ${hasMore ? `
                    <button class="btn-sm btn-secondary mt-2" id="env-show-all">
                        Show all (${totalCount})
                    </button>
                ` : ''}
                <p class="text-xs text-gray-500 mt-2">
                    ⓘ Sensitive values (API keys, secrets, passwords) are automatically filtered.
                </p>
            </div>
        `;
    }

    setupEnvironmentFilter(container) {
        const filterInput = container.querySelector('#env-filter');
        const showAllBtn = container.querySelector('#env-show-all');

        // Filter input
        if (filterInput) {
            filterInput.addEventListener('input', (e) => {
                this.envFilter = e.target.value.toLowerCase();
                this.filterEnvironmentTable();
            });
        }

        // Show all button
        if (showAllBtn) {
            showAllBtn.addEventListener('click', () => {
                this.envLimit = Object.keys(this.config.environment).length;
                const contentDiv = this.container.querySelector('#config-content');
                if (contentDiv) {
                    this.renderStructuredView(contentDiv);
                }
            });
        }

        // Copy value buttons
        const copyButtons = container.querySelectorAll('.btn-icon[data-copy-value]');
        copyButtons.forEach(btn => {
            btn.addEventListener('click', (e) => {
                const value = e.currentTarget.dataset.copyValue;
                navigator.clipboard.writeText(value).then(() => {
                    if (window.showToast) {
                        window.showToast('Value copied to clipboard', 'success', 1000);
                    }
                });
            });
        });
    }

    filterEnvironmentTable() {
        const table = this.container.querySelector('#env-table tbody');
        if (!table) return;

        const rows = table.querySelectorAll('tr');
        let visibleCount = 0;

        rows.forEach(row => {
            const key = row.dataset.envKey || '';
            if (key.includes(this.envFilter)) {
                row.style.display = '';
                visibleCount++;
            } else {
                row.style.display = 'none';
            }
        });

        // Update count badge
        const countBadge = this.container.querySelector('#env-count');
        if (countBadge) {
            const totalCount = rows.length;
            countBadge.textContent = this.envFilter
                ? `${visibleCount} of ${totalCount} variables`
                : `${totalCount} variables`;
        }
    }

    showRawJsonModal() {
        if (!this.config) {
            if (window.showToast) {
                window.showToast('No configuration loaded', 'error');
            }
            return;
        }

        const modal = this.container.querySelector('#raw-json-modal');
        const content = this.container.querySelector('#raw-json-content');

        if (modal && content) {
            // Render JSON viewer
            content.innerHTML = '';
            new JsonViewer(content, this.config);

            // Show modal
            modal.style.display = 'flex';

            // Setup copy button
            const copyBtn = this.container.querySelector('#copy-raw-json');
            if (copyBtn) {
                // Remove existing listeners
                const newCopyBtn = copyBtn.cloneNode(true);
                copyBtn.parentNode.replaceChild(newCopyBtn, copyBtn);

                newCopyBtn.addEventListener('click', () => {
                    const jsonString = JSON.stringify(this.config, null, 2);
                    navigator.clipboard.writeText(jsonString).then(() => {
                        if (window.showToast) {
                            window.showToast('Configuration copied to clipboard', 'success', 1500);
                        }
                    });
                });
            }
        }
    }

    hideRawJsonModal() {
        const modal = this.container.querySelector('#raw-json-modal');
        if (modal) {
            modal.style.display = 'none';
        }
    }

    setupQuickActions(container) {
        const viewProvidersBtn = container.querySelector('#view-providers');
        if (viewProvidersBtn) {
            viewProvidersBtn.addEventListener('click', () => {
                if (window.navigateToView) {
                    window.navigateToView('providers');
                }
            });
        }

        const viewSelfcheckBtn = container.querySelector('#view-selfcheck');
        if (viewSelfcheckBtn) {
            viewSelfcheckBtn.addEventListener('click', () => {
                if (window.navigateToView) {
                    window.navigateToView('support');
                }
            });
        }

        const downloadConfigBtn = container.querySelector('#download-config-footer');
        if (downloadConfigBtn) {
            downloadConfigBtn.addEventListener('click', () => this.downloadConfig());
        }

        // Database Migration actions
        const runMigrationsBtn = container.querySelector('#run-migrations');
        if (runMigrationsBtn) {
            runMigrationsBtn.addEventListener('click', () => this.runMigrations());
        }

        const refreshMigrationsBtn = container.querySelector('#refresh-migrations');
        if (refreshMigrationsBtn) {
            refreshMigrationsBtn.addEventListener('click', () => this.loadConfig(true));
        }
    }

    async runMigrations() {
        if (!this.migrationsStatus || !this.migrationsStatus.needs_migration) {
            if (window.showToast) {
                window.showToast('No migrations needed', 'info');
            }
            return;
        }

        const fromVersion = this.migrationsStatus.current_version;
        const toVersion = this.migrationsStatus.latest_version;

        const confirmed = await Dialog.confirm(
            `Run database migration from v${fromVersion} to v${toVersion}?\n\n${this.migrationsStatus.pending_count} migration(s) will be applied.\n\nThis operation cannot be undone.`,
            {
                title: 'Run Database Migration',
                confirmText: 'Run Migration',
                danger: true
            }
        );
        if (!confirmed) {
            return;
        }

        try {
            // Show loading state
            const runBtn = this.container.querySelector('#run-migrations');
            if (runBtn) {
                runBtn.disabled = true;
                runBtn.innerHTML = '<span class="material-icons md-18">hourglass_empty</span> Running...';
            }

            if (window.showToast) {
                window.showToast('Running database migrations...', 'info', 2000);
            }

            // Call migration API
            const response = await apiClient.post('/api/config/migrations/migrate', {
                target_version: null // null = latest
            });

            if (!response.ok) {
                throw new Error(response.error || 'Migration failed');
            }

            const result = response.data;

            if (window.showToast) {
                window.showToast(
                    `<span class="material-icons" style="font-size: 16px; vertical-align: middle;">check</span> Migration successful: v${result.from_version} <span class="material-icons" style="font-size: 14px; vertical-align: middle;">arrow_forward</span> v${result.to_version} (${result.migrations_executed} migration(s))`,
                    'success',
                    3000
                );
            }

            // Reload configuration to show updated status
            await this.loadConfig(false);

        } catch (error) {
            console.error('Failed to run migrations:', error);

            if (window.showToast) {
                window.showToast(`Migration failed: ${error.message}`, 'error', 5000);
            }

            // Re-enable button
            const runBtn = this.container.querySelector('#run-migrations');
            if (runBtn) {
                runBtn.disabled = false;
                runBtn.innerHTML = '<span class="material-icons md-18">upgrade</span> Run Migrations';
            }
        }
    }

    downloadConfig() {
        if (!this.config) {
            if (window.showToast) {
                window.showToast('No configuration loaded', 'error');
            }
            return;
        }

        try {
            const jsonString = JSON.stringify(this.config, null, 2);
            const blob = new Blob([jsonString], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `agentos-config-${new Date().toISOString().split('T')[0]}.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);

            if (window.showToast) {
                window.showToast('Configuration downloaded', 'success', 1500);
            }
        } catch (error) {
            console.error('Failed to download config:', error);
            if (window.showToast) {
                window.showToast('Download failed', 'error');
            }
        }
    }

    formatLabel(key) {
        // 将 snake_case 转为 Title Case
        return key
            .split('_')
            .map(word => word.charAt(0).toUpperCase() + word.slice(1))
            .join(' ');
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    destroy() {
        // Cleanup
        this.container.innerHTML = '';
    }
}
