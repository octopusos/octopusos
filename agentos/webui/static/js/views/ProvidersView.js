/**
 * Providers Management View
 *
 * Local Setup page with instance management, fingerprint detection,
 * and process lifecycle control.
 *
 * Sprint B+ WebUI Integration
 */

class ProvidersView {
    constructor(apiClient) {
        this.apiClient = apiClient;
        this.instances = [];
        this.selectedInstance = null;
    }

    async render() {
        return `
            <div class="providers-view">
                <div class="view-header">
                    <h1>Local Model Providers</h1>
                    <div class="header-actions">
                        <button id="refresh-all" class="btn btn-primary">
                            <span class="icon"><span class="material-icons md-18">refresh</span></span> Refresh All
                        </button>
                    </div>
                </div>

                <div class="providers-content">
                    <!-- Ollama Section -->
                    <div class="provider-section" data-provider="ollama">
                        <div class="section-header">
                            <h2>Ollama</h2>
                            <button class="btn btn-sm" data-action="add-instance" data-provider="ollama">
                                + Add Instance
                            </button>
                        </div>
                        <div class="instances-container" data-provider="ollama"></div>
                    </div>

                    <!-- LM Studio Section -->
                    <div class="provider-section" data-provider="lmstudio">
                        <div class="section-header">
                            <h2>LM Studio</h2>
                            <div class="section-actions">
                                <button class="btn btn-sm" data-action="open-lmstudio">
                                    📱 Open App
                                </button>
                                <button class="btn btn-sm" data-action="verify-lmstudio">
                                    <span class="material-icons" style="font-size: 14px; vertical-align: middle;">check</span> Verify
                                </button>
                            </div>
                        </div>
                        <div class="instances-container" data-provider="lmstudio"></div>
                    </div>

                    <!-- llamacpp Section -->
                    <div class="provider-section" data-provider="llamacpp">
                        <div class="section-header">
                            <h2>llama.cpp</h2>
                            <button class="btn btn-sm" data-action="add-instance" data-provider="llamacpp">
                                + Add Instance
                            </button>
                        </div>
                        <div class="instances-container" data-provider="llamacpp"></div>
                    </div>

                    <!-- Install Section -->
                    <div class="install-section">
                        <h2>Installation</h2>
                        <div class="install-grid">
                            <div class="install-card" data-provider="ollama">
                                <h3>Ollama</h3>
                                <div class="cli-status" data-provider="ollama">
                                    <span class="status-icon"><span class="material-icons md-18">hourglass_empty</span></span>
                                    <span class="status-text">Checking...</span>
                                </div>
                                <button class="btn btn-install" data-provider="ollama" style="display:none">
                                    Install (brew)
                                </button>
                            </div>

                            <div class="install-card" data-provider="llamacpp">
                                <h3>llama.cpp</h3>
                                <div class="cli-status" data-provider="llamacpp">
                                    <span class="status-icon"><span class="material-icons md-18">hourglass_empty</span></span>
                                    <span class="status-text">Checking...</span>
                                </div>
                                <button class="btn btn-install" data-provider="llamacpp" style="display:none">
                                    Install (brew)
                                </button>
                            </div>

                            <div class="install-card" data-provider="lmstudio">
                                <h3>LM Studio</h3>
                                <div class="cli-status" data-provider="lmstudio">
                                    <span class="status-icon"><span class="material-icons md-18">hourglass_empty</span></span>
                                    <span class="status-text">Checking...</span>
                                </div>
                                <p class="install-note">Install from <a href="https://lmstudio.ai" target="_blank">lmstudio.ai</a></p>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Modals -->
                <div id="instance-modal" class="modal" style="display:none"></div>
                <div id="output-modal" class="modal" style="display:none"></div>
            </div>
        `;
    }

    async mount() {
        await this.loadInstances();
        await this.checkCLI();
        this.attachEventListeners();
        this.startAutoRefresh();
    }

    attachEventListeners() {
        // Refresh all
        document.getElementById('refresh-all')?.addEventListener('click', () => {
            this.loadInstances();
        });

        // Add instance buttons
        document.querySelectorAll('[data-action="add-instance"]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const provider = e.target.dataset.provider;
                this.showInstanceModal(provider);
            });
        });

        // LM Studio actions
        document.querySelector('[data-action="open-lmstudio"]')?.addEventListener('click', () => {
            this.openLMStudio();
        });

        document.querySelector('[data-action="verify-lmstudio"]')?.addEventListener('click', () => {
            this.verifyLMStudio();
        });

        // Install buttons
        document.querySelectorAll('.btn-install').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const provider = e.target.dataset.provider;
                this.installProvider(provider);
            });
        });

        // Instance actions (delegated)
        document.addEventListener('click', (e) => {
            // Find the button element (in case user clicks on icon inside button)
            const button = e.target.closest('[data-instance-action]');
            if (!button) return;

            const action = button.dataset.instanceAction;
            const instanceKey = button.dataset.instanceKey;
            const providerId = button.dataset.providerId;
            const instanceId = button.dataset.instanceId;

            switch (action) {
                case 'refresh':
                    this.refreshInstance(instanceKey);
                    break;
                case 'start':
                    this.startInstance(providerId, instanceId);
                    break;
                case 'stop':
                    this.stopInstance(providerId, instanceId);
                    break;
                case 'restart':
                    this.restartInstance(providerId, instanceId);
                    break;
                case 'output':
                    this.showOutputModal(providerId, instanceId);
                    break;
                case 'edit':
                    this.editInstance(providerId, instanceId);
                    break;
                case 'edit-routing':
                    this.editRoutingMetadata(providerId, instanceId);
                    break;
                case 'delete':
                    this.deleteInstance(providerId, instanceId);
                    break;
                case 'change-port':
                    this.changePort(providerId, instanceId);
                    break;
            }
        });
    }

    async loadInstances() {
        try {
            const response = await this.apiClient.get('/api/providers/instances');
            this.instances = response.instances;
            this.renderInstances();
        } catch (error) {
            console.error('Failed to load instances:', error);
        }
    }

    renderInstances() {
        // Group by provider
        const byProvider = {
            ollama: [],
            lmstudio: [],
            llamacpp: []
        };

        this.instances.forEach(inst => {
            if (byProvider[inst.provider_id]) {
                byProvider[inst.provider_id].push(inst);
            }
        });

        // Render each provider's instances
        Object.keys(byProvider).forEach(provider => {
            const container = document.querySelector(`.instances-container[data-provider="${provider}"]`);
            if (!container) return;

            const instances = byProvider[provider];
            if (instances.length === 0) {
                container.innerHTML = '<p class="no-instances">No instances configured</p>';
                return;
            }

            container.innerHTML = `
                <table class="instances-table">
                    <thead>
                        <tr>
                            <th>Instance ID</th>
                            <th>Endpoint</th>
                            <th>State</th>
                            <th>Fingerprint</th>
                            <th>Process</th>
                            <th>Routing Metadata</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${instances.map(inst => this.renderInstanceRow(inst)).join('')}
                    </tbody>
                </table>
            `;
        });
    }

    renderInstanceRow(inst) {
        const stateClass = {
            'READY': 'state-ready',
            'ERROR': 'state-error',
            'DISCONNECTED': 'state-disconnected'
        }[inst.state] || 'state-unknown';

        const processStatus = inst.process_running ?
            `<span class="process-running">Running (PID ${inst.process_pid})</span>` :
            `<span class="process-stopped">Stopped</span>`;

        // PR-4: Extract routing metadata
        const metadata = inst.metadata || {};
        const tags = metadata.tags || [];
        const ctx = metadata.ctx || null;
        const role = metadata.role || null;

        // Actions based on state
        let actions = `
            <button class="btn btn-xs" data-instance-action="refresh"
                    data-instance-key="${inst.instance_key}"><span class="material-icons md-18">refresh</span></button>
            <button class="btn btn-xs" data-instance-action="edit"
                    data-provider-id="${inst.provider_id}" data-instance-id="${inst.instance_id}"><span class="material-icons md-18">edit</span></button>
            <button class="btn btn-xs" data-instance-action="edit-routing"
                    data-provider-id="${inst.provider_id}" data-instance-id="${inst.instance_id}"
                    title="Edit routing metadata"><span class="material-icons md-18">track_changes</span></button>
        `;

        // Start/Stop buttons (only for instances with launch config)
        if (inst.has_launch_config) {
            if (inst.process_running) {
                actions += `
                    <button class="btn btn-xs" data-instance-action="stop"
                            data-provider-id="${inst.provider_id}" data-instance-id="${inst.instance_id}"
                            title="Stop instance"><span class="material-icons md-18" style="color: #dc3545;">stop</span></button>
                `;
            } else {
                actions += `
                    <button class="btn btn-xs" data-instance-action="start"
                            data-provider-id="${inst.provider_id}" data-instance-id="${inst.instance_id}"
                            title="Start instance"><span class="material-icons md-18" style="color: #28a745;">play_arrow</span></button>
                `;
            }
        }

        // Output log button for all instances
        actions += `
            <button class="btn btn-xs" data-instance-action="output"
                    data-provider-id="${inst.provider_id}" data-instance-id="${inst.instance_id}"
                    title="View logs"><span class="material-icons md-18">description</span></button>
        `;

        // Port conflict quick fix
        let errorInfo = '';
        if (inst.reason_code === 'PORT_OCCUPIED_BY_OTHER_PROVIDER') {
            errorInfo = `
                <div class="instance-error">
                    <span><span class="material-icons md-18">warning</span> ${inst.last_error}</span>
                    <button class="btn btn-xs btn-warning" data-instance-action="change-port"
                            data-provider-id="${inst.provider_id}" data-instance-id="${inst.instance_id}">
                        Change Port
                    </button>
                </div>
            `;
        } else if (inst.last_error) {
            errorInfo = `<div class="instance-error"><span><span class="material-icons md-18">warning</span> ${inst.last_error}</span></div>`;
        }

        // PR-4: Display routing metadata
        const tagsDisplay = tags.length > 0
            ? tags.map(t => `<span class="tag-badge">${t}</span>`).join(' ')
            : '<span class="text-muted">no tags</span>';

        const ctxDisplay = ctx
            ? `<span class="ctx-badge">${ctx}</span>`
            : '<span class="text-muted">—</span>';

        return `
            <tr class="instance-row ${stateClass}" data-instance-key="${inst.instance_key}">
                <td>${inst.instance_id}</td>
                <td>
                    <code>${inst.base_url}</code>
                    ${errorInfo}
                </td>
                <td>
                    <span class="state-badge ${stateClass}">${inst.state}</span>
                    ${inst.latency_ms ? `<span class="latency">${inst.latency_ms}ms</span>` : ''}
                </td>
                <td>
                    <span class="fingerprint-badge">${inst.detected_fingerprint || 'unknown'}</span>
                </td>
                <td>${processStatus}</td>
                <td class="routing-metadata">
                    <div class="metadata-row">
                        <label>Tags:</label>
                        <div class="metadata-value">${tagsDisplay}</div>
                    </div>
                    <div class="metadata-row">
                        <label>Ctx:</label>
                        <div class="metadata-value">${ctxDisplay}</div>
                    </div>
                    ${role ? `<div class="metadata-row"><label>Role:</label><div class="metadata-value"><span class="role-badge">${role}</span></div></div>` : ''}
                </td>
                <td class="actions">${actions}</td>
            </tr>
        `;
    }

    async checkCLI() {
        const providers = ['ollama', 'llamacpp', 'lmstudio'];

        for (const provider of providers) {
            try {
                const response = await this.apiClient.get(`/api/providers/${provider}/cli-check`);
                const statusEl = document.querySelector(`.cli-status[data-provider="${provider}"]`);
                const installBtn = document.querySelector(`.btn-install[data-provider="${provider}"]`);

                // Check if statusEl exists before accessing it
                if (!statusEl) {
                    console.warn(`CLI status element not found for provider: ${provider}`);
                    continue;
                }

                if (response.cli_found) {
                    statusEl.innerHTML = `
                        <span class="status-icon"><span class="material-icons md-18">done</span></span>
                        <span class="status-text">CLI Found</span>
                        <code class="cli-path">${response.bin_path}</code>
                    `;
                    if (installBtn) installBtn.style.display = 'none';
                } else {
                    statusEl.innerHTML = `
                        <span class="status-icon"><span class="material-icons md-18">cancel</span></span>
                        <span class="status-text">CLI Not Found</span>
                    `;
                    if (installBtn && provider !== 'lmstudio') {
                        installBtn.style.display = 'block';
                    }
                }
            } catch (error) {
                console.error(`Failed to check CLI for ${provider}:`, error);
            }
        }
    }

    showInstanceModal(provider, instance = null) {
        const modal = document.getElementById('instance-modal');
        const isEdit = instance !== null;

        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h2>${isEdit ? 'Edit' : 'Add'} ${provider} Instance</h2>
                    <button class="modal-close">&times;</button>
                </div>
                <div class="modal-body">
                    <form id="instance-form">
                        <div class="form-group">
                            <label>Instance ID</label>
                            <input type="text" name="instance_id" required
                                   value="${instance?.instance_id || ''}"
                                   ${isEdit ? 'readonly' : ''}>
                        </div>
                        <div class="form-group">
                            <label>Endpoint</label>
                            <input type="url" name="base_url" required
                                   placeholder="http://127.0.0.1:8080"
                                   value="${instance?.base_url || ''}">
                        </div>
                        ${provider === 'llamacpp' ? this.renderLaunchConfig(instance) : ''}
                        <div class="form-actions">
                            <button type="submit" class="btn btn-primary">Save</button>
                            <button type="button" class="btn btn-info" id="modal-test-btn" style="margin-right: auto;">Test Connection</button>
                            <button type="button" class="btn btn-secondary" id="modal-cancel-btn">Cancel</button>
                        </div>
                    </form>
                </div>
            </div>
        `;

        modal.style.display = 'flex';

        // Event listeners
        modal.querySelectorAll('.modal-close').forEach(btn => {
            btn.addEventListener('click', () => modal.style.display = 'none');
        });

        // Cancel button
        const cancelBtn = modal.querySelector('#modal-cancel-btn');
        if (cancelBtn) {
            cancelBtn.addEventListener('click', () => modal.style.display = 'none');
        }

        // Test button
        const testBtn = modal.querySelector('#modal-test-btn');
        if (testBtn) {
            testBtn.addEventListener('click', async () => {
                await this.testInstance(provider, document.getElementById('instance-form'));
            });
        }

        document.getElementById('instance-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            await this.saveInstance(provider, e.target, isEdit);
        });
    }

    renderLaunchConfig(instance) {
        const launch = instance?.launch_config || {};
        const args = launch.args || {};

        return `
            <fieldset class="launch-config">
                <legend>Launch Configuration (Optional - for Start/Stop control)</legend>
                <div class="form-row">
                    <div class="form-group">
                        <label>Model Path</label>
                        <input type="text" name="launch_model"
                               value="${args.model || ''}"
                               placeholder="/path/to/model.gguf (required to start)">
                    </div>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label>Host</label>
                        <input type="text" name="launch_host"
                               value="${args.host || '127.0.0.1'}">
                    </div>
                    <div class="form-group">
                        <label>Port</label>
                        <input type="number" name="launch_port"
                               value="${args.port || 8080}">
                    </div>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label>GPU Layers (ngl)</label>
                        <input type="number" name="launch_ngl"
                               value="${args.ngl || 99}">
                    </div>
                    <div class="form-group">
                        <label>Threads</label>
                        <input type="number" name="launch_threads"
                               value="${args.threads || 8}">
                    </div>
                    <div class="form-group">
                        <label>Context Size</label>
                        <input type="number" name="launch_ctx"
                               value="${args.ctx || 8192}">
                    </div>
                </div>
                <div class="form-group">
                    <label>Extra Args</label>
                    <input type="text" name="launch_extra"
                           placeholder="--option value"
                           value="${args.extra_args || ''}">
                </div>
            </fieldset>
        `;
    }

    async testInstance(provider, form) {
        const formData = new FormData(form);
        const baseUrl = formData.get('base_url');

        if (!baseUrl) {
            Toast.error('Please enter an endpoint URL first');
            return;
        }

        const testBtn = document.getElementById('modal-test-btn');
        const originalText = testBtn.textContent;

        try {
            // Disable button and show loading state
            testBtn.disabled = true;
            testBtn.textContent = 'Testing...';

            // Record start time for latency measurement
            const startTime = Date.now();

            // Test the endpoint
            const response = await fetch(`${baseUrl}/health`, {
                method: 'GET',
                headers: {
                    'Accept': 'application/json'
                },
                signal: AbortSignal.timeout(5000) // 5 second timeout
            });

            const latency = Date.now() - startTime;

            if (response.ok) {
                const data = await response.json();
                Toast.success(`Connection successful (${latency}ms)`);

                // Show additional info if available
                if (data.model) {
                    console.log('Model info:', data.model);
                }
            } else {
                Toast.error(`Connection failed: ${response.status} ${response.statusText}`);
            }
        } catch (error) {
            if (error.name === 'TimeoutError') {
                Toast.error('Connection timeout (>5s)');
            } else if (error.message.includes('Failed to fetch')) {
                Toast.error('Cannot reach endpoint. Check URL and network.');
            } else {
                Toast.error(`Test failed: ${error.message}`);
            }
        } finally {
            // Restore button state
            testBtn.disabled = false;
            testBtn.textContent = originalText;
        }
    }

    async saveInstance(provider, form, isEdit) {
        const formData = new FormData(form);
        const data = {
            instance_id: formData.get('instance_id'),
            base_url: formData.get('base_url'),
            enabled: true,
            metadata: {}
        };

        // Add launch config for llamacpp (always include to enable Start/Stop buttons)
        if (provider === 'llamacpp') {
            const modelPath = formData.get('launch_model') || '';
            const host = formData.get('launch_host') || '127.0.0.1';
            const port = parseInt(formData.get('launch_port')) || 8080;
            const ngl = parseInt(formData.get('launch_ngl')) || 99;
            const threads = parseInt(formData.get('launch_threads')) || 8;
            const ctx = parseInt(formData.get('launch_ctx')) || 8192;

            data.launch = {
                bin: 'llama-server',
                args: {
                    model: modelPath,
                    host: host,
                    port: port,
                    ngl: ngl,
                    threads: threads,
                    ctx: ctx
                }
            };

            const extraArgs = formData.get('launch_extra');
            if (extraArgs) {
                data.launch.args.extra_args = extraArgs;
            }
        }

        try {
            if (isEdit) {
                await this.apiClient.put(`/api/providers/instances/${provider}/${data.instance_id}`, data);
            } else {
                await this.apiClient.post(`/api/providers/instances/${provider}`, data);
            }

            Toast.success(`Instance ${provider}:${data.instance_id} saved successfully`);
            document.getElementById('instance-modal').style.display = 'none';
            await this.loadInstances();
        } catch (error) {
            console.error('Failed to save instance:', error);
            Toast.error(`Failed to save instance: ${error.message}`);
        }
    }

    showOutputModal(providerId, instanceId) {
        const modal = document.getElementById('output-modal');
        modal.innerHTML = `
            <div class="modal-content output-modal">
                <div class="modal-header">
                    <h2>Process Output: ${providerId}:${instanceId}</h2>
                    <button class="modal-close">&times;</button>
                </div>
                <div class="modal-body">
                    <div class="output-controls">
                        <select id="output-lines">
                            <option value="50">Last 50 lines</option>
                            <option value="200" selected>Last 200 lines</option>
                            <option value="1000">Last 1000 lines</option>
                        </select>
                        <input type="text" id="output-search" placeholder="Search...">
                        <button id="output-copy" class="btn btn-sm"><span class="material-icons md-18">content_copy</span> Copy</button>
                    </div>
                    <div class="output-tabs">
                        <button class="tab-btn active" data-stream="stdout">stdout</button>
                        <button class="tab-btn" data-stream="stderr">stderr</button>
                    </div>
                    <pre id="output-content" class="output-content">Loading...</pre>
                </div>
            </div>
        `;

        modal.style.display = 'flex';

        modal.querySelector('.modal-close').addEventListener('click', () => {
            modal.style.display = 'none';
        });

        this.loadOutput(providerId, instanceId, 'stdout', 200);

        // Tab switching
        modal.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                modal.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
                e.target.classList.add('active');
                const stream = e.target.dataset.stream;
                const lines = document.getElementById('output-lines').value;
                this.loadOutput(providerId, instanceId, stream, parseInt(lines));
            });
        });

        // Lines change
        document.getElementById('output-lines').addEventListener('change', (e) => {
            const stream = modal.querySelector('.tab-btn.active').dataset.stream;
            this.loadOutput(providerId, instanceId, stream, parseInt(e.target.value));
        });

        // Search
        document.getElementById('output-search').addEventListener('input', (e) => {
            this.filterOutput(e.target.value);
        });

        // Copy
        document.getElementById('output-copy').addEventListener('click', () => {
            const content = document.getElementById('output-content').textContent;
            navigator.clipboard.writeText(content);
        });
    }

    async loadOutput(providerId, instanceId, stream, lines) {
        try {
            const response = await this.apiClient.get(
                `/api/providers/${providerId}/instances/${instanceId}/output?lines=${lines}`
            );

            const content = stream === 'stdout' ? response.stdout : response.stderr;
            document.getElementById('output-content').textContent = content.join('\n') || '(empty)';
        } catch (error) {
            document.getElementById('output-content').textContent = `Error: ${error.message}`;
        }
    }

    filterOutput(query) {
        const content = document.getElementById('output-content');
        const lines = content.textContent.split('\n');

        if (!query) {
            content.textContent = lines.join('\n');
            return;
        }

        const filtered = lines.filter(line => line.toLowerCase().includes(query.toLowerCase()));
        content.textContent = filtered.join('\n');
    }

    async startInstance(providerId, instanceId) {
        try {
            await this.apiClient.post(`/api/providers/${providerId}/instances/start`, {
                instance_id: instanceId
            });
            Toast.success(`Starting ${providerId}:${instanceId}...`);
            await this.loadInstances();
        } catch (error) {
            console.error('Failed to start instance:', error);
            Toast.error(`Failed to start instance: ${error.message}`);
        }
    }

    async stopInstance(providerId, instanceId) {
        try {
            await this.apiClient.post(`/api/providers/${providerId}/instances/stop`, {
                instance_id: instanceId
            });
            Toast.success(`Stopping ${providerId}:${instanceId}...`);
            await this.loadInstances();
        } catch (error) {
            console.error('Failed to stop instance:', error);
            Toast.error(`Failed to stop instance: ${error.message}`);
        }
    }

    async restartInstance(providerId, instanceId) {
        await this.stopInstance(providerId, instanceId);
        setTimeout(() => this.startInstance(providerId, instanceId), 1000);
    }

    async openLMStudio() {
        try {
            await this.apiClient.post('/api/providers/lmstudio/open-app');
        } catch (error) {
            Dialog.alert('Failed to open LM Studio: ' + error.message, { title: 'Error' });
        }
    }

    async verifyLMStudio() {
        await this.refreshInstance('lmstudio');
    }

    async installProvider(provider) {
        try {
            const btn = document.querySelector(`.btn-install[data-provider="${provider}"]`);
            btn.disabled = true;
            btn.textContent = 'Installing...';

            await this.apiClient.post(`/api/providers/${provider}/install`);

            btn.innerHTML = 'Installed <span class="material-icons" style="font-size: 16px; vertical-align: middle;">check</span>';
            await this.checkCLI();
        } catch (error) {
            Dialog.alert('Installation failed: ' + error.message, { title: 'Installation Error' });
        }
    }

    async refreshInstance(instanceKey) {
        await this.loadInstances();
    }

    async editInstance(providerId, instanceId) {
        try {
            const response = await this.apiClient.get(`/api/providers/instances/${providerId}/${instanceId}`);
            // Convert config to instance format
            const instance = {
                provider_id: providerId,
                instance_id: response.config.instance_id,
                base_url: response.config.base_url,
                launch_config: response.config.launch
            };
            this.showInstanceModal(providerId, instance);
        } catch (error) {
            Dialog.alert('Failed to load instance: ' + error.message, { title: 'Load Error' });
        }
    }

    async deleteInstance(providerId, instanceId) {
        const confirmed = await Dialog.confirm(`Delete instance ${providerId}:${instanceId}?`, {
            title: 'Delete Instance',
            confirmText: 'Delete',
            danger: true
        });
        if (!confirmed) return;

        try {
            await this.apiClient.delete(`/api/providers/instances/${providerId}/${instanceId}`);
            await this.loadInstances();
        } catch (error) {
            Dialog.alert('Failed to delete: ' + error.message, { title: 'Delete Error' });
        }
    }

    changePort(providerId, instanceId) {
        // Open edit modal with port field focused
        this.editInstance(providerId, instanceId);
        setTimeout(() => {
            const portInput = document.querySelector('input[name="launch_port"]');
            if (portInput) portInput.focus();
        }, 100);
    }

    async editRoutingMetadata(providerId, instanceId) {
        try {
            const response = await this.apiClient.get(`/api/providers/instances/${providerId}/${instanceId}`);
            const instance = {
                provider_id: providerId,
                instance_id: response.config.instance_id,
                base_url: response.config.base_url,
                metadata: response.config.metadata || {}
            };
            this.showRoutingMetadataModal(instance);
        } catch (error) {
            Dialog.alert('Failed to load instance: ' + error.message, { title: 'Load Error' });
        }
    }

    showRoutingMetadataModal(instance) {
        const modal = document.getElementById('instance-modal');
        const metadata = instance.metadata || {};
        const tags = (metadata.tags || []).join(', ');
        const ctx = metadata.ctx || '';
        const role = metadata.role || '';

        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h2>Edit Routing Metadata: ${instance.instance_id}</h2>
                    <button class="modal-close">&times;</button>
                </div>
                <div class="modal-body">
                    <form id="routing-metadata-form">
                        <div class="form-group">
                            <label>Tags (comma-separated)</label>
                            <input type="text" name="tags"
                                   placeholder="e.g., coding, big_ctx, local"
                                   value="${tags}">
                            <small class="form-hint">Examples: coding, fast, big_ctx, local, vision</small>
                        </div>
                        <div class="form-group">
                            <label>Context Length (ctx)</label>
                            <input type="number" name="ctx"
                                   placeholder="e.g., 8192"
                                   value="${ctx}">
                            <small class="form-hint">Maximum context window size</small>
                        </div>
                        <div class="form-group">
                            <label>Role</label>
                            <input type="text" name="role"
                                   placeholder="e.g., coding, general, fast"
                                   value="${role}">
                            <small class="form-hint">Primary use case for this instance</small>
                        </div>
                        <div class="form-actions">
                            <button type="submit" class="btn btn-primary">Save Routing Metadata</button>
                            <button type="button" class="btn btn-secondary" id="modal-cancel-routing-btn">Cancel</button>
                        </div>
                    </form>
                </div>
            </div>
        `;

        modal.style.display = 'flex';

        modal.querySelectorAll('.modal-close').forEach(btn => {
            btn.addEventListener('click', () => modal.style.display = 'none');
        });

        // Cancel button
        const cancelBtn = modal.querySelector('#modal-cancel-routing-btn');
        if (cancelBtn) {
            cancelBtn.addEventListener('click', () => modal.style.display = 'none');
        }

        document.getElementById('routing-metadata-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            await this.saveRoutingMetadata(instance.provider_id, instance.instance_id, e.target);
        });
    }

    async saveRoutingMetadata(providerId, instanceId, form) {
        const formData = new FormData(form);

        // Parse tags (comma-separated)
        const tagsStr = formData.get('tags').trim();
        const tags = tagsStr ? tagsStr.split(',').map(t => t.trim()).filter(t => t) : [];

        // Parse ctx (optional)
        const ctxStr = formData.get('ctx').trim();
        const ctx = ctxStr ? parseInt(ctxStr) : null;

        // Parse role (optional)
        const role = formData.get('role').trim() || null;

        try {
            // Fetch current config first
            const current = await this.apiClient.get(`/api/providers/instances/${providerId}/${instanceId}`);

            // Update only metadata
            const updatedConfig = {
                ...current.config,
                metadata: {
                    ...(current.config.metadata || {}),
                    tags: tags,
                    ctx: ctx,
                    role: role
                }
            };

            await this.apiClient.put(`/api/providers/instances/${providerId}/${instanceId}`, updatedConfig);

            document.getElementById('instance-modal').style.display = 'none';
            await this.loadInstances();

            // Show success toast if available
            if (window.showToast) {
                window.showToast('Routing metadata updated', 'success');
            }
        } catch (error) {
            Dialog.alert('Failed to save routing metadata: ' + error.message, { title: 'Save Error' });
        }
    }

    startAutoRefresh() {
        setInterval(() => this.loadInstances(), 10000);
    }

    unmount() {
        // Cleanup
    }
}

// Export
window.ProvidersView = ProvidersView;
