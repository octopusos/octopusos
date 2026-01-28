/**
 * TasksView - Task Management UI
 *
 * PR-2: Observability Module - Tasks View
 * Coverage: GET /api/tasks, GET /api/tasks/{task_id}
 */

class TasksView {
    constructor(container) {
        this.container = container;
        this.filterBar = null;
        this.dataTable = null;
        this.detailDrawer = null;
        this.currentFilters = {};
        this.tasks = [];
        this.selectedTask = null;
        this.decisionTraceLoaded = false;
        this.currentDecisionTrace = [];
        this.nextTraceCursor = null;
        this.planLoaded = false;
        this.reposLoaded = false;
        this.dependenciesLoaded = false;
        this.guardianReviewsLoaded = false;

        this.init();
    }

    init() {
        this.container.innerHTML = `
            <div class="tasks-view">
                <div class="view-header">
                    <h2>Task Management</h2>
                    <div class="header-actions">
                        <button class="btn-refresh" id="tasks-refresh">
                            <span class="icon"><span class="material-icons md-18">refresh</span></span> Refresh
                        </button>
                        <button class="btn-primary" id="tasks-create">
                            <span class="icon"><span class="material-icons md-18">add</span></span> Create Task
                        </button>
                    </div>
                </div>

                <div id="tasks-filter-bar" class="filter-section"></div>

                <div id="tasks-table" class="table-section"></div>

                <div id="tasks-detail-drawer" class="drawer hidden">
                    <div class="drawer-overlay" id="tasks-drawer-overlay"></div>
                    <div class="drawer-content">
                        <div class="drawer-header">
                            <h3>Task Details</h3>
                            <button class="btn-close" id="tasks-drawer-close">✕</button>
                        </div>
                        <div class="drawer-body" id="tasks-drawer-body">
                            <!-- Task details will be rendered here -->
                        </div>
                    </div>
                </div>
            </div>
        `;

        this.setupFilterBar();
        this.setupDataTable();
        this.setupEventListeners();
        this.loadTasks();
    }

    setupFilterBar() {
        const filterContainer = this.container.querySelector('#tasks-filter-bar');

        this.filterBar = new FilterBar(filterContainer, {
            filters: [
                {
                    type: 'text',
                    key: 'task_id',
                    label: 'Task ID',
                    placeholder: 'Filter by task ID...'
                },
                {
                    type: 'select',
                    key: 'status',
                    label: 'Status',
                    options: [
                        { value: '', label: 'All Status' },
                        { value: 'pending', label: 'Pending' },
                        { value: 'running', label: 'Running' },
                        { value: 'completed', label: 'Completed' },
                        { value: 'failed', label: 'Failed' },
                        { value: 'cancelled', label: 'Cancelled' }
                    ]
                },
                {
                    type: 'text',
                    key: 'session_id',
                    label: 'Session ID',
                    placeholder: 'Filter by session...'
                },
                {
                    type: 'time-range',
                    key: 'time_range',
                    label: 'Time Range',
                    placeholder: 'Select time range'
                },
                {
                    type: 'button',
                    key: 'reset',
                    label: 'Reset',
                    className: 'btn-secondary'
                }
            ],
            onChange: (filters) => this.handleFilterChange(filters),
            debounceMs: 300
        });
    }

    setupDataTable() {
        const tableContainer = this.container.querySelector('#tasks-table');

        this.dataTable = new DataTable(tableContainer, {
            columns: [
                {
                    key: 'task_id',
                    label: 'Task ID',
                    width: '200px',
                    render: (value) => `<code class="code-inline">${value}</code>`
                },
                {
                    key: 'status',
                    label: 'Status',
                    width: '120px',
                    render: (value) => this.renderStatus(value)
                },
                {
                    key: 'type',
                    label: 'Type',
                    width: '150px',
                    render: (value) => value || 'N/A'
                },
                {
                    key: 'session_id',
                    label: 'Session',
                    width: '200px',
                    render: (value) => value ? `<code class="code-inline">${value}</code>` : 'N/A'
                },
                {
                    key: 'created_at',
                    label: 'Created',
                    width: '180px',
                    render: (value) => this.formatTimestamp(value)
                },
                {
                    key: 'updated_at',
                    label: 'Updated',
                    width: '180px',
                    render: (value) => this.formatTimestamp(value)
                }
            ],
            data: [],
            emptyText: 'No tasks found',
            loadingText: 'Loading tasks...',
            onRowClick: (task) => this.showTaskDetail(task),
            pagination: true,
            pageSize: 10
        });
    }

    setupEventListeners() {
        // Refresh button
        this.container.querySelector('#tasks-refresh').addEventListener('click', () => {
            this.loadTasks(true);
        });

        // Create button
        this.container.querySelector('#tasks-create').addEventListener('click', () => {
            this.createTask();
        });

        // Drawer close
        this.container.querySelector('#tasks-drawer-close').addEventListener('click', () => {
            this.hideTaskDetail();
        });

        this.container.querySelector('#tasks-drawer-overlay').addEventListener('click', () => {
            this.hideTaskDetail();
        });

        // Keyboard shortcut: Escape to close drawer
        const handleKeydown = (e) => {
            if (e.key === 'Escape' && !this.container.querySelector('#tasks-detail-drawer').classList.contains('hidden')) {
                this.hideTaskDetail();
            }
        };
        document.addEventListener('keydown', handleKeydown);
    }

    handleFilterChange(filters) {
        this.currentFilters = filters;
        this.loadTasks();
    }

    async loadTasks(forceRefresh = false) {
        this.dataTable.setLoading(true);

        try {
            // Build query parameters
            const params = new URLSearchParams();

            if (this.currentFilters.task_id) {
                params.append('task_id', this.currentFilters.task_id);
            }
            if (this.currentFilters.status) {
                params.append('status', this.currentFilters.status);
            }
            if (this.currentFilters.session_id) {
                params.append('session_id', this.currentFilters.session_id);
            }
            if (this.currentFilters.time_range) {
                const { start, end } = this.currentFilters.time_range;
                if (start) params.append('start_time', start);
                if (end) params.append('end_time', end);
            }

            const url = `/api/tasks${params.toString() ? '?' + params.toString() : ''}`;
            const result = await apiClient.get(url, {
                requestId: `tasks-list-${Date.now()}`
            });

            if (result.ok) {
                this.tasks = result.data.tasks || result.data || [];
                this.dataTable.setData(this.tasks);

                if (forceRefresh) {
                    showToast('Tasks refreshed', 'success', 2000);
                }
            } else {
                showToast(`Failed to load tasks: ${result.message}`, 'error');
                this.dataTable.setData([]);
            }
        } catch (error) {
            console.error('Failed to load tasks:', error);
            showToast('Failed to load tasks', 'error');
            this.dataTable.setData([]);
        } finally {
            this.dataTable.setLoading(false);
        }
    }

    async showTaskDetail(task) {
        this.selectedTask = task;
        const drawer = this.container.querySelector('#tasks-detail-drawer');
        const drawerBody = this.container.querySelector('#tasks-drawer-body');

        // Show drawer with loading state
        drawer.classList.remove('hidden');
        drawerBody.innerHTML = '<div class="loading-spinner">Loading task details...</div>';

        try {
            // Fetch full task details
            const result = await apiClient.get(`/api/tasks/${task.task_id}`, {
                requestId: `task-detail-${task.task_id}`
            });

            if (result.ok) {
                const taskDetail = result.data;
                this.renderTaskDetail(taskDetail);
            } else {
                drawerBody.innerHTML = `
                    <div class="error-message">
                        <div class="error-icon"><span class="material-icons md-18">warning</span></div>
                        <div class="error-text">Failed to load task details: ${result.message}</div>
                    </div>
                `;
            }
        } catch (error) {
            console.error('Failed to load task detail:', error);
            drawerBody.innerHTML = `
                <div class="error-message">
                    <div class="error-icon"><span class="material-icons md-18">warning</span></div>
                    <div class="error-text">Failed to load task details</div>
                </div>
            `;
        }
    }

    renderTaskDetail(task) {
        const drawerBody = this.container.querySelector('#tasks-drawer-body');

        drawerBody.innerHTML = `
            <div class="task-detail">
                <!-- Tab Navigation -->
                <div class="task-detail-tabs">
                    <button class="tab-btn active" data-tab="overview">Overview</button>
                    <button class="tab-btn" data-tab="plan">Execution Plan</button>
                    <button class="tab-btn" data-tab="repos">Repos & Changes</button>
                    <button class="tab-btn" data-tab="dependencies">Dependencies</button>
                    <button class="tab-btn" data-tab="decision-trace">Decision Trace</button>
                    <button class="tab-btn" data-tab="guardian-reviews">Guardian Reviews</button>
                    <button class="tab-btn" data-tab="audit">Audit</button>
                    <button class="tab-btn" data-tab="history">History</button>
                </div>

                <!-- Tab Content -->
                <div class="task-detail-tab-content">
                    <!-- Overview Tab -->
                    <div class="tab-pane active" data-tab-pane="overview">
                        <div class="detail-section">
                            <h4>Basic Information</h4>
                            <div class="detail-grid">
                                <div class="detail-item">
                                    <label>Task ID</label>
                                    <div class="detail-value">
                                        <code>${task.task_id}</code>
                                        <button class="btn-copy" data-copy="${task.task_id}" title="Copy Task ID">
                                            <span class="material-icons md-18">content_copy</span>
                                        </button>
                                    </div>
                                </div>
                                <div class="detail-item">
                                    <label>Status</label>
                                    <div class="detail-value">${this.renderStatus(task.status)}</div>
                                </div>
                                <div class="detail-item">
                                    <label>Type</label>
                                    <div class="detail-value">${task.type || 'N/A'}</div>
                                </div>
                                <div class="detail-item">
                                    <label>Session ID</label>
                                    <div class="detail-value">
                                        ${task.session_id ? `
                                            <code>${task.session_id}</code>
                                            <button class="btn-link" data-session="${task.session_id}">View Session</button>
                                        ` : 'N/A'}
                                    </div>
                                </div>
                                <div class="detail-item">
                                    <label>Created</label>
                                    <div class="detail-value">${this.formatTimestamp(task.created_at)}</div>
                                </div>
                                <div class="detail-item">
                                    <label>Updated</label>
                                    <div class="detail-value">${this.formatTimestamp(task.updated_at)}</div>
                                </div>
                            </div>
                        </div>

                        ${task.description ? `
                            <div class="detail-section">
                                <h4>Description</h4>
                                <div class="detail-description">${task.description}</div>
                            </div>
                        ` : ''}

                        ${this.renderRouteTimeline(task)}

                        ${task.error ? `
                            <div class="detail-section">
                                <h4>Error</h4>
                                <div class="error-box">${task.error}</div>
                            </div>
                        ` : ''}

                        <div class="detail-section">
                            <h4>Full Task Data</h4>
                            <div id="task-json-viewer"></div>
                        </div>

                        <div class="detail-actions">
                            <button class="btn-secondary" id="task-view-events">View Related Events</button>
                            <button class="btn-secondary" id="task-view-logs">View Related Logs</button>
                            ${task.status === 'running' ? `
                                <button class="btn-danger" id="task-cancel">Cancel Task</button>
                            ` : ''}
                        </div>

                        <!-- Wave4-X1: Integration Links to New Views -->
                        <div class="detail-section">
                            <h4>Execution & Governance</h4>
                            <div class="execution-links">
                                <button class="btn-link" id="task-view-plan">
                                    <span class="material-icons md-18">list_alt</span> View Execution Plan
                                </button>
                                <button class="btn-link" id="task-view-intent">
                                    <span class="material-icons md-18">edit</span> View Intent Workbench
                                </button>
                                <button class="btn-link" id="task-view-content">
                                    <span class="material-icons md-18">inventory_2</span> View Content Assets
                                </button>
                                <button class="btn-link" id="task-view-answers">
                                    <span class="material-icons md-18">question_answer</span> View Answer Packs
                                </button>
                            </div>
                        </div>
                    </div>

                    <!-- Execution Plan Tab -->
                    <div class="tab-pane" data-tab-pane="plan">
                        <div id="task-plan-content" class="plan-loading">
                            <div class="loading-spinner">Loading execution plan...</div>
                        </div>
                    </div>

                    <!-- Repos & Changes Tab -->
                    <div class="tab-pane" data-tab-pane="repos">
                        <div id="task-repos-content" class="repos-loading">
                            <div class="loading-spinner">Loading repository information...</div>
                        </div>
                    </div>

                    <!-- Dependencies Tab -->
                    <div class="tab-pane" data-tab-pane="dependencies">
                        <div id="task-dependencies-content" class="dependencies-loading">
                            <div class="loading-spinner">Loading dependencies...</div>
                        </div>
                    </div>

                    <!-- Decision Trace Tab -->
                    <div class="tab-pane" data-tab-pane="decision-trace">
                        <div class="decision-trace-container">
                            <div class="trace-header">
                                <h4>Decision Trace Timeline</h4>
                                <div class="trace-filters">
                                    <input type="text" class="trace-search" placeholder="Search in trace..." id="trace-search">
                                    <select class="trace-filter" id="trace-filter-type">
                                        <option value="">All Decisions</option>
                                        <option value="ALLOWED">ALLOWED</option>
                                        <option value="BLOCKED">BLOCKED</option>
                                        <option value="PAUSED">PAUSED</option>
                                        <option value="RETRY">RETRY</option>
                                    </select>
                                </div>
                            </div>
                            <div id="decision-trace-content" class="trace-loading">
                                <div class="loading-spinner">Loading decision trace...</div>
                            </div>
                        </div>
                    </div>

                    <!-- Guardian Reviews Tab -->
                    <div class="tab-pane" data-tab-pane="guardian-reviews">
                        <div id="guardian-reviews-container" class="guardian-loading">
                            <div class="loading-spinner"></div>
                            <span>Loading Guardian reviews...</span>
                        </div>
                    </div>

                    <!-- Audit Tab (Placeholder) -->
                    <div class="tab-pane" data-tab-pane="audit">
                        <div class="detail-section">
                            <h4>Audit Log</h4>
                            <p class="text-muted">Audit log view coming soon...</p>
                        </div>
                    </div>

                    <!-- History Tab (Placeholder) -->
                    <div class="tab-pane" data-tab-pane="history">
                        <div class="detail-section">
                            <h4>Task History</h4>
                            <p class="text-muted">Task history view coming soon...</p>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Render JSON viewer
        const jsonContainer = drawerBody.querySelector('#task-json-viewer');
        new JsonViewer(jsonContainer, task, {
            collapsed: true,
            maxDepth: 2,
            showToolbar: true,
            fileName: `task-${task.task_id}.json`
        });

        // Setup tab switching
        this.setupTabSwitching(task);

        // Setup action buttons
        this.setupTaskDetailActions(task);
    }

    renderRouteTimeline(task) {
        // PR-4: Extract routing information from task data
        const routePlan = task.route_plan_json ? JSON.parse(task.route_plan_json) : task.route_plan;
        const requirements = task.requirements_json ? JSON.parse(task.requirements_json) : task.requirements;
        const selectedInstance = task.selected_instance_id || routePlan?.selected;

        // Check if there's any routing info
        if (!routePlan && !selectedInstance && !requirements) {
            return '';
        }

        // Build route timeline from events (if available)
        const routeEvents = (task.events || []).filter(e =>
            e.event_type === 'TASK_ROUTED' ||
            e.event_type === 'TASK_ROUTE_VERIFIED' ||
            e.event_type === 'TASK_REROUTED' ||
            e.event_type === 'TASK_ROUTE_OVERRIDDEN'
        );

        return `
            <div class="detail-section route-section">
                <h4>Routing Information</h4>

                ${selectedInstance ? `
                    <div class="route-selected">
                        <div class="route-label">Selected Instance</div>
                        <div class="route-instance">${selectedInstance}</div>
                    </div>
                ` : ''}

                ${requirements ? `
                    <div class="route-requirements">
                        <div class="route-label">Requirements</div>
                        <div class="requirements-list">
                            ${requirements.needs ? requirements.needs.map(n => `<span class="requirement-badge">${n}</span>`).join(' ') : ''}
                            ${requirements.min_ctx ? `<span class="requirement-badge">min_ctx: ${requirements.min_ctx}</span>` : ''}
                        </div>
                    </div>
                ` : ''}

                ${routePlan ? this.renderRoutePlan(routePlan) : ''}

                ${routeEvents.length > 0 ? this.renderRouteEventsTimeline(routeEvents) : ''}
            </div>
        `;
    }

    renderRoutePlan(routePlan) {
        const scores = routePlan.scores || {};
        const reasons = routePlan.reasons || [];
        const fallback = routePlan.fallback || [];

        return `
            <div class="route-plan">
                ${reasons.length > 0 ? `
                    <div class="route-reasons">
                        <div class="route-label">Routing Reasons</div>
                        <ul class="reasons-list">
                            ${reasons.map(r => `<li>${r}</li>`).join('')}
                        </ul>
                    </div>
                ` : ''}

                ${Object.keys(scores).length > 0 ? `
                    <div class="route-scores">
                        <div class="route-label">Instance Scores</div>
                        <div class="scores-chart">
                            ${Object.entries(scores).map(([instance, score]) => `
                                <div class="score-item">
                                    <div class="score-bar-container">
                                        <div class="score-bar" style="width: ${score * 100}%"></div>
                                    </div>
                                    <div class="score-label">
                                        <span class="score-instance">${instance}</span>
                                        <span class="score-value">${(score * 100).toFixed(1)}%</span>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                ` : ''}

                ${fallback.length > 0 ? `
                    <div class="route-fallback">
                        <div class="route-label">Fallback Chain</div>
                        <div class="fallback-chain">
                            ${fallback.map((inst, idx) => `
                                <span class="fallback-instance">
                                    ${idx + 1}. ${inst}
                                </span>
                            `).join(' <span class="material-icons" style="font-size: 14px; vertical-align: middle;">arrow_forward</span> ')}
                        </div>
                    </div>
                ` : ''}
            </div>
        `;
    }

    renderRouteEventsTimeline(events) {
        return `
            <div class="route-timeline">
                <div class="route-label">Route Timeline</div>
                <div class="timeline-container">
                    ${events.map(event => this.renderRouteEvent(event)).join('')}
                </div>
            </div>
        `;
    }

    renderRouteEvent(event) {
        const eventIcons = {
            'TASK_ROUTED': '<span class="material-icons md-18">track_changes</span>',
            'TASK_ROUTE_VERIFIED': '<span class="material-icons md-18">done</span>',
            'TASK_REROUTED': '<span class="material-icons md-18">refresh</span>',
            'TASK_ROUTE_OVERRIDDEN': '<span class="material-icons md-18">edit</span>'
        };

        const eventLabels = {
            'TASK_ROUTED': 'Initial Route',
            'TASK_ROUTE_VERIFIED': 'Route Verified',
            'TASK_REROUTED': 'Rerouted',
            'TASK_ROUTE_OVERRIDDEN': 'Manual Override'
        };

        const icon = eventIcons[event.event_type] || '📌';
        const label = eventLabels[event.event_type] || event.event_type;

        // Extract routing info from event data
        const eventData = event.data || {};
        const instance = eventData.selected || eventData.instance || 'unknown';
        const reason = eventData.reason || eventData.reason_code || '';
        const score = eventData.score;

        return `
            <div class="timeline-event">
                <div class="event-icon">${icon}</div>
                <div class="event-content">
                    <div class="event-header">
                        <span class="event-type">${label}</span>
                        <span class="event-time">${this.formatTimestamp(event.timestamp || event.created_at)}</span>
                    </div>
                    <div class="event-details">
                        <div class="event-instance">Instance: <code>${instance}</code></div>
                        ${reason ? `<div class="event-reason">Reason: ${reason}</div>` : ''}
                        ${score !== undefined ? `<div class="event-score">Score: ${(score * 100).toFixed(1)}%</div>` : ''}
                    </div>
                </div>
            </div>
        `;
    }

    setupTabSwitching(task) {
        const drawerBody = this.container.querySelector('#tasks-drawer-body');
        const tabBtns = drawerBody.querySelectorAll('.tab-btn');
        const tabPanes = drawerBody.querySelectorAll('.tab-pane');

        tabBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                const tabName = btn.getAttribute('data-tab');

                // Update active tab button
                tabBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');

                // Update active tab pane
                tabPanes.forEach(pane => {
                    if (pane.getAttribute('data-tab-pane') === tabName) {
                        pane.classList.add('active');
                    } else {
                        pane.classList.remove('active');
                    }
                });

                // Load execution plan when tab is activated
                if (tabName === 'plan' && !this.planLoaded) {
                    this.loadTaskPlan(task.task_id);
                    this.planLoaded = true;
                }

                // Load decision trace when tab is activated
                if (tabName === 'decision-trace' && !this.decisionTraceLoaded) {
                    this.loadDecisionTrace(task.task_id);
                    this.decisionTraceLoaded = true;
                }

                // Load repos when tab is activated
                if (tabName === 'repos' && !this.reposLoaded) {
                    this.loadTaskRepos(task.task_id);
                    this.reposLoaded = true;
                }

                // Load dependencies when tab is activated
                if (tabName === 'dependencies' && !this.dependenciesLoaded) {
                    this.loadTaskDependencies(task.task_id);
                    this.dependenciesLoaded = true;
                }

                // Load Guardian reviews when tab is activated
                if (tabName === 'guardian-reviews' && !this.guardianReviewsLoaded) {
                    this.loadGuardianReviews(task.task_id);
                    this.guardianReviewsLoaded = true;
                }
            });
        });

        // Setup decision trace filters
        const searchInput = drawerBody.querySelector('#trace-search');
        const filterSelect = drawerBody.querySelector('#trace-filter-type');

        if (searchInput) {
            searchInput.addEventListener('input', () => {
                this.filterDecisionTrace();
            });
        }

        if (filterSelect) {
            filterSelect.addEventListener('change', () => {
                this.filterDecisionTrace();
            });
        }
    }

    async loadDecisionTrace(taskId, cursor = null) {
        const traceContent = this.container.querySelector('#decision-trace-content');

        try {
            // Build URL with parameters
            const params = new URLSearchParams();
            params.append('limit', '50');
            if (cursor) {
                params.append('cursor', cursor);
            }

            const url = `/api/governance/tasks/${taskId}/decision-trace?${params.toString()}`;
            const result = await apiClient.get(url, {
                requestId: `decision-trace-${taskId}-${Date.now()}`
            });

            if (result.ok) {
                this.currentDecisionTrace = result.data.trace_items || [];
                this.nextTraceCursor = result.data.next_cursor;
                this.renderDecisionTrace(this.currentDecisionTrace, cursor === null);
            } else {
                traceContent.innerHTML = `
                    <div class="error-message">
                        <div class="error-icon"><span class="material-icons md-18">warning</span></div>
                        <div class="error-text">Failed to load decision trace: ${result.message}</div>
                    </div>
                `;
            }
        } catch (error) {
            console.error('Failed to load decision trace:', error);
            traceContent.innerHTML = `
                <div class="error-message">
                    <div class="error-icon"><span class="material-icons md-18">warning</span></div>
                    <div class="error-text">Failed to load decision trace</div>
                </div>
            `;
        }
    }

    renderDecisionTrace(traceItems, isInitial = true) {
        const traceContent = this.container.querySelector('#decision-trace-content');

        if (traceItems.length === 0) {
            traceContent.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon"><span class="material-icons md-36">timeline</span></div>
                    <div class="empty-text">No decision trace available</div>
                </div>
            `;
            return;
        }

        const timelineHtml = `
            <div class="decision-trace-timeline" id="decision-trace-timeline">
                ${traceItems.map(item => this.renderTraceItem(item)).join('')}
            </div>
            ${this.nextTraceCursor ? `
                <div class="trace-load-more">
                    <button class="btn-secondary" id="trace-load-more">Load More</button>
                </div>
            ` : ''}
        `;

        if (isInitial) {
            traceContent.innerHTML = timelineHtml;
        } else {
            // Append to existing timeline
            const timeline = traceContent.querySelector('#decision-trace-timeline');
            const loadMoreBtn = traceContent.querySelector('.trace-load-more');
            if (loadMoreBtn) loadMoreBtn.remove();

            timeline.insertAdjacentHTML('beforeend', traceItems.map(item => this.renderTraceItem(item)).join(''));

            if (this.nextTraceCursor) {
                timeline.insertAdjacentHTML('afterend', `
                    <div class="trace-load-more">
                        <button class="btn-secondary" id="trace-load-more">Load More</button>
                    </div>
                `);
            }
        }

        // Setup load more button
        const loadMoreBtn = traceContent.querySelector('#trace-load-more');
        if (loadMoreBtn) {
            loadMoreBtn.addEventListener('click', () => {
                this.loadDecisionTrace(this.selectedTask.task_id, this.nextTraceCursor);
            });
        }

        // Setup toggle buttons
        traceContent.querySelectorAll('.trace-toggle-json').forEach(btn => {
            btn.addEventListener('click', () => {
                const itemId = btn.getAttribute('data-item-id');
                const jsonContainer = traceContent.querySelector(`#trace-json-${itemId}`);
                if (jsonContainer) {
                    jsonContainer.classList.toggle('hidden');
                    btn.textContent = jsonContainer.classList.contains('hidden') ? 'Show JSON' : 'Hide JSON';
                }
            });
        });
    }

    renderTraceItem(item) {
        const timestamp = this.formatTimestamp(item.ts);
        const itemId = `${item.kind}-${item.audit_id || item.event_id || Math.random()}`;

        if (item.kind === 'audit') {
            return this.renderAuditTraceItem(item, timestamp, itemId);
        } else if (item.kind === 'event') {
            return this.renderEventTraceItem(item, timestamp, itemId);
        } else {
            return this.renderGenericTraceItem(item, timestamp, itemId);
        }
    }

    renderAuditTraceItem(item, timestamp, itemId) {
        const decisionSnapshot = item.decision_snapshot || {};
        const decisionType = this.extractDecisionType(item.event_type, decisionSnapshot);
        const decisionBadge = this.renderDecisionBadge(decisionType);
        const details = this.extractDecisionDetails(decisionSnapshot);

        return `
            <div class="trace-item" data-decision-type="${decisionType}">
                <div class="trace-timestamp">${timestamp}</div>
                <div class="trace-line"></div>
                <div class="trace-content">
                    <div class="trace-event">
                        <span class="event-type-badge event-audit">SUPERVISOR AUDIT</span>
                        <span class="event-source">${item.event_type}</span>
                    </div>
                    <div class="trace-decision">
                        ${decisionBadge}
                        ${details.reason ? `<div class="decision-reason">${details.reason}</div>` : ''}
                    </div>
                    ${details.rules.length > 0 ? `
                        <div class="trace-rules">
                            <div class="rules-label">Rules Applied:</div>
                            <div class="rules-list">
                                ${details.rules.map(rule => `<span class="rule-badge">${rule}</span>`).join('')}
                            </div>
                        </div>
                    ` : ''}
                    ${details.riskScore !== null ? `
                        <div class="trace-risk">
                            <span class="risk-label">Risk Score:</span>
                            <span class="risk-value ${this.getRiskClass(details.riskScore)}">${details.riskScore}/100</span>
                        </div>
                    ` : ''}
                    ${decisionSnapshot && Object.keys(decisionSnapshot).length > 0 ? `
                        <div class="trace-json-toggle">
                            <button class="btn-link trace-toggle-json" data-item-id="${itemId}">Show JSON</button>
                        </div>
                        <div class="trace-json hidden" id="trace-json-${itemId}">
                            <pre>${JSON.stringify(decisionSnapshot, null, 2)}</pre>
                        </div>
                    ` : ''}
                </div>
            </div>
        `;
    }

    renderEventTraceItem(item, timestamp, itemId) {
        const payload = item.payload || {};
        const eventSource = payload.source || 'unknown';

        return `
            <div class="trace-item" data-decision-type="">
                <div class="trace-timestamp">${timestamp}</div>
                <div class="trace-line"></div>
                <div class="trace-content">
                    <div class="trace-event">
                        <span class="event-type-badge event-task">TASK EVENT</span>
                        <span class="event-source">${item.event_type}</span>
                    </div>
                    ${eventSource !== 'unknown' ? `
                        <div class="event-metadata">
                            <span class="metadata-label">Source:</span>
                            <span class="metadata-value">${eventSource}</span>
                        </div>
                    ` : ''}
                    ${payload && Object.keys(payload).length > 0 ? `
                        <div class="trace-json-toggle">
                            <button class="btn-link trace-toggle-json" data-item-id="${itemId}">Show JSON</button>
                        </div>
                        <div class="trace-json hidden" id="trace-json-${itemId}">
                            <pre>${JSON.stringify(payload, null, 2)}</pre>
                        </div>
                    ` : ''}
                </div>
            </div>
        `;
    }

    renderGenericTraceItem(item, timestamp, itemId) {
        return `
            <div class="trace-item" data-decision-type="">
                <div class="trace-timestamp">${timestamp}</div>
                <div class="trace-line"></div>
                <div class="trace-content">
                    <div class="trace-event">
                        <span class="event-type-badge">${item.kind.toUpperCase()}</span>
                    </div>
                    <div class="trace-json-toggle">
                        <button class="btn-link trace-toggle-json" data-item-id="${itemId}">Show JSON</button>
                    </div>
                    <div class="trace-json hidden" id="trace-json-${itemId}">
                        <pre>${JSON.stringify(item.data, null, 2)}</pre>
                    </div>
                </div>
            </div>
        `;
    }

    extractDecisionType(eventType, decisionSnapshot) {
        // Try to extract from event_type first
        if (eventType.includes('ALLOWED')) return 'ALLOWED';
        if (eventType.includes('BLOCKED')) return 'BLOCKED';
        if (eventType.includes('PAUSED')) return 'PAUSED';
        if (eventType.includes('RETRY')) return 'RETRY';

        // Try from decision_snapshot
        if (decisionSnapshot.decision_type) {
            return decisionSnapshot.decision_type.toUpperCase();
        }

        return 'UNKNOWN';
    }

    extractDecisionDetails(decisionSnapshot) {
        const details = {
            reason: null,
            rules: [],
            riskScore: null,
        };

        if (!decisionSnapshot) return details;

        // Extract reason
        if (decisionSnapshot.blocked_reason_code) {
            details.reason = `Blocked: ${decisionSnapshot.blocked_reason_code}`;
        } else if (decisionSnapshot.reason) {
            details.reason = decisionSnapshot.reason;
        } else if (decisionSnapshot.metadata && decisionSnapshot.metadata.reason) {
            details.reason = decisionSnapshot.metadata.reason;
        }

        // Extract rules
        if (decisionSnapshot.rules_applied) {
            details.rules = Array.isArray(decisionSnapshot.rules_applied)
                ? decisionSnapshot.rules_applied
                : [decisionSnapshot.rules_applied];
        } else if (decisionSnapshot.policies_evaluated) {
            details.rules = Array.isArray(decisionSnapshot.policies_evaluated)
                ? decisionSnapshot.policies_evaluated
                : [decisionSnapshot.policies_evaluated];
        }

        // Extract risk score
        if (decisionSnapshot.metadata && typeof decisionSnapshot.metadata.risk_score === 'number') {
            details.riskScore = decisionSnapshot.metadata.risk_score;
        } else if (typeof decisionSnapshot.risk_score === 'number') {
            details.riskScore = decisionSnapshot.risk_score;
        }

        return details;
    }

    renderDecisionBadge(decisionType) {
        const badges = {
            'ALLOWED': '<span class="decision-badge decision-allowed"><span class="material-icons md-18">check_circle</span> ALLOWED</span>',
            'BLOCKED': '<span class="decision-badge decision-blocked"><span class="material-icons md-18">block</span> BLOCKED</span>',
            'PAUSED': '<span class="decision-badge decision-paused"><span class="material-icons md-18">pause_circle</span> PAUSED</span>',
            'RETRY': '<span class="decision-badge decision-retry"><span class="material-icons md-18">refresh</span> RETRY</span>',
            'UNKNOWN': '<span class="decision-badge decision-unknown"><span class="material-icons md-18">help</span> UNKNOWN</span>',
        };

        return badges[decisionType] || badges['UNKNOWN'];
    }

    getRiskClass(score) {
        if (score >= 80) return 'risk-high';
        if (score >= 50) return 'risk-medium';
        return 'risk-low';
    }

    filterDecisionTrace() {
        const drawerBody = this.container.querySelector('#tasks-drawer-body');
        const searchInput = drawerBody.querySelector('#trace-search');
        const filterSelect = drawerBody.querySelector('#trace-filter-type');
        const traceItems = drawerBody.querySelectorAll('.trace-item');

        if (!searchInput || !filterSelect) return;

        const searchTerm = searchInput.value.toLowerCase();
        const filterType = filterSelect.value;

        traceItems.forEach(item => {
            const text = item.textContent.toLowerCase();
            const decisionType = item.getAttribute('data-decision-type');

            const matchesSearch = !searchTerm || text.includes(searchTerm);
            const matchesFilter = !filterType || decisionType === filterType;

            if (matchesSearch && matchesFilter) {
                item.style.display = '';
            } else {
                item.style.display = 'none';
            }
        });
    }

    setupTaskDetailActions(task) {
        const drawerBody = this.container.querySelector('#tasks-drawer-body');

        // Copy buttons
        drawerBody.querySelectorAll('.btn-copy').forEach(btn => {
            btn.addEventListener('click', () => {
                const text = btn.getAttribute('data-copy');
                navigator.clipboard.writeText(text);
                showToast('Copied to clipboard', 'success', 1500);
            });
        });

        // View session button
        const sessionBtn = drawerBody.querySelector('.btn-link[data-session]');
        if (sessionBtn) {
            sessionBtn.addEventListener('click', () => {
                const sessionId = sessionBtn.getAttribute('data-session');
                window.navigateToView('chat', { session_id: sessionId });
                this.hideTaskDetail();
            });
        }

        // View events button
        const eventsBtn = drawerBody.querySelector('#task-view-events');
        if (eventsBtn) {
            eventsBtn.addEventListener('click', () => {
                window.navigateToView('events', { task_id: task.task_id });
                this.hideTaskDetail();
            });
        }

        // View logs button
        const logsBtn = drawerBody.querySelector('#task-view-logs');
        if (logsBtn) {
            logsBtn.addEventListener('click', () => {
                window.navigateToView('logs', { task_id: task.task_id });
                this.hideTaskDetail();
            });
        }

        // Cancel button
        const cancelBtn = drawerBody.querySelector('#task-cancel');
        if (cancelBtn) {
            cancelBtn.addEventListener('click', async () => {
                const confirmed = await Dialog.confirm(`Are you sure you want to cancel task ${task.task_id}?`, {
                    title: 'Cancel Task',
                    confirmText: 'Cancel Task',
                    danger: true
                });
                if (confirmed) {
                    await this.cancelTask(task.task_id);
                }
            });
        }

        // Wave4-X1: Navigation to new execution views
        const planBtn = drawerBody.querySelector('#task-view-plan');
        if (planBtn) {
            planBtn.addEventListener('click', () => {
                // Switch to plan tab instead of navigating away
                const tabBtn = drawerBody.querySelector('.tab-btn[data-tab="plan"]');
                if (tabBtn) {
                    tabBtn.click();
                }
            });
        }

        const intentBtn = drawerBody.querySelector('#task-view-intent');
        if (intentBtn) {
            intentBtn.addEventListener('click', () => {
                this.hideTaskDetail();
                loadView('intent-workbench');
                // TODO: Pass task's intent_id context when IntentWorkbenchView is implemented
            });
        }

        const contentBtn = drawerBody.querySelector('#task-view-content');
        if (contentBtn) {
            contentBtn.addEventListener('click', () => {
                this.hideTaskDetail();
                loadView('content-registry');
                // TODO: Filter by task's content assets when ContentRegistryView is implemented
            });
        }

        const answersBtn = drawerBody.querySelector('#task-view-answers');
        if (answersBtn) {
            answersBtn.addEventListener('click', () => {
                this.hideTaskDetail();
                loadView('answer-packs');
                // TODO: Filter by task's answer packs when AnswerPacksView is implemented
            });
        }
    }

    hideTaskDetail() {
        const drawer = this.container.querySelector('#tasks-detail-drawer');
        drawer.classList.add('hidden');
        this.selectedTask = null;
        this.decisionTraceLoaded = false;
        this.currentDecisionTrace = [];
        this.nextTraceCursor = null;
        this.planLoaded = false;
        this.reposLoaded = false;
        this.dependenciesLoaded = false;
        this.guardianReviewsLoaded = false;
    }

    async createTask() {
        showToast('Task creation UI coming soon', 'info');
        // TODO: Implement task creation modal
    }

    async cancelTask(taskId) {
        try {
            const result = await apiClient.post(`/api/tasks/${taskId}/cancel`, {}, {
                requestId: `task-cancel-${taskId}`
            });

            if (result.ok) {
                showToast('Task cancelled successfully', 'success');
                this.hideTaskDetail();
                this.loadTasks(true);
            } else {
                showToast(`Failed to cancel task: ${result.message}`, 'error');
            }
        } catch (error) {
            console.error('Failed to cancel task:', error);
            showToast('Failed to cancel task', 'error');
        }
    }

    async loadTaskPlan(taskId) {
        const planContent = this.container.querySelector('#task-plan-content');

        try {
            const result = await apiClient.get(`/api/exec/tasks/${taskId}/plan`, {
                requestId: `task-plan-${taskId}-${Date.now()}`
            });

            if (result.ok) {
                const plan = result.data;
                this.renderTaskPlan(plan);
            } else {
                planContent.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-icon"><span class="material-icons md-36">description</span></div>
                        <div class="empty-text">No execution plan available for this task</div>
                        <p class="text-muted">Generate a plan first or check if the API is available.</p>
                    </div>
                `;
            }
        } catch (error) {
            console.error('Failed to load task plan:', error);
            planContent.innerHTML = `
                <div class="error-message">
                    <div class="error-icon"><span class="material-icons md-18">warning</span></div>
                    <div class="error-text">Failed to load execution plan</div>
                    <p class="text-muted">The execution plan API may not be available yet.</p>
                </div>
            `;
        }
    }

    renderTaskPlan(plan) {
        const planContent = this.container.querySelector('#task-plan-content');

        // Create a mini embedded version of the plan
        planContent.innerHTML = `
            <div class="task-plan-embedded">
                <div class="plan-header">
                    <div class="plan-info">
                        <h4>Execution Plan</h4>
                        ${plan.plan_id ? `<code class="code-inline">${plan.plan_id}</code>` : ''}
                    </div>
                    <span class="plan-status status-${plan.status || 'draft'}">${this.formatPlanStatus(plan.status || 'draft')}</span>
                </div>

                ${plan.description ? `
                    <div class="plan-description">
                        <p>${plan.description}</p>
                    </div>
                ` : ''}

                ${plan.validation ? this.renderPlanValidationSummary(plan.validation) : ''}

                ${plan.steps && plan.steps.length > 0 ? `
                    <div class="plan-steps-summary">
                        <h5>Steps (${plan.steps.length})</h5>
                        <div class="steps-list">
                            ${plan.steps.slice(0, 5).map((step, idx) => `
                                <div class="step-item">
                                    <span class="step-number">${idx + 1}</span>
                                    <span class="step-name">${step.name || `Step ${idx + 1}`}</span>
                                    ${step.risk_level && step.risk_level !== 'low' ? `
                                        <span class="risk-badge risk-${step.risk_level}">${step.risk_level.toUpperCase()}</span>
                                    ` : ''}
                                </div>
                            `).join('')}
                            ${plan.steps.length > 5 ? `
                                <div class="text-muted">... and ${plan.steps.length - 5} more steps</div>
                            ` : ''}
                        </div>
                    </div>
                ` : ''}

                <div class="plan-actions">
                    <button class="btn-secondary" onclick="window.open('#execution-plans?task_id=${plan.task_id}', '_blank')">
                        <span class="material-icons md-18">open_in_new</span>
                        View Full Plan
                    </button>
                </div>
            </div>
        `;
    }

    renderPlanValidationSummary(validation) {
        const hasFailed = validation.rules_failed && validation.rules_failed.length > 0;
        const passedCount = validation.rules_passed ? validation.rules_passed.length : 0;
        const failedCount = validation.rules_failed ? validation.rules_failed.length : 0;

        return `
            <div class="plan-validation-summary ${hasFailed ? 'has-failures' : 'all-passed'}">
                <h5>
                    <span class="material-icons md-18">${hasFailed ? 'error' : 'check_circle'}</span>
                    Validation
                </h5>
                <div class="validation-stats">
                    ${passedCount > 0 ? `<span class="stat-passed">${passedCount} passed</span>` : ''}
                    ${failedCount > 0 ? `<span class="stat-failed">${failedCount} failed</span>` : ''}
                </div>
            </div>
        `;
    }

    formatPlanStatus(status) {
        const statusMap = {
            'draft': 'Draft',
            'pending': 'Pending',
            'validated': 'Validated',
            'approved': 'Approved',
            'rejected': 'Rejected',
            'executing': 'Executing',
            'completed': 'Completed',
            'failed': 'Failed'
        };
        return statusMap[status] || status;
    }

    renderStatus(status) {
        const statusMap = {
            'pending': { label: 'Pending', class: 'status-pending', icon: '<span class="material-icons md-18">hourglass_empty</span>' },
            'running': { label: 'Running', class: 'status-running', icon: '<span class="material-icons md-18">play_arrow</span>' },
            'completed': { label: 'Completed', class: 'status-success', icon: '<span class="material-icons md-18">done</span>' },
            'failed': { label: 'Failed', class: 'status-error', icon: '<span class="material-icons md-18">cancel</span>' },
            'cancelled': { label: 'Cancelled', class: 'status-cancelled', icon: '<span class="material-icons md-18">block</span>' }
        };

        const config = statusMap[status] || { label: status, class: 'status-unknown', icon: '<span class="material-icons md-18">help</span>' };
        return `<span class="status-badge ${config.class}">${config.icon} ${config.label}</span>`;
    }

    formatTimestamp(timestamp) {
        if (!timestamp) return 'N/A';

        try {
            const date = new Date(timestamp);
            const now = new Date();
            const diff = now - date;

            // Less than 1 minute
            if (diff < 60000) {
                return 'Just now';
            }

            // Less than 1 hour
            if (diff < 3600000) {
                const minutes = Math.floor(diff / 60000);
                return `${minutes}m ago`;
            }

            // Less than 24 hours
            if (diff < 86400000) {
                const hours = Math.floor(diff / 3600000);
                return `${hours}h ago`;
            }

            // Format as date
            return date.toLocaleString();
        } catch (e) {
            return timestamp;
        }
    }

    async loadTaskRepos(taskId) {
        const reposContent = this.container.querySelector('#task-repos-content');

        try {
            const result = await apiClient.get(`/api/tasks/${taskId}/repos?detailed=true`, {
                requestId: `task-repos-${taskId}-${Date.now()}`
            });

            if (result.ok) {
                const repos = result.data || [];
                this.renderTaskRepos(repos);
            } else {
                reposContent.innerHTML = `
                    <div class="error-message">
                        <div class="error-icon"><span class="material-icons md-18">warning</span></div>
                        <div class="error-text">Failed to load repositories: ${result.message}</div>
                    </div>
                `;
            }
        } catch (error) {
            console.error('Failed to load task repos:', error);
            reposContent.innerHTML = `
                <div class="error-message">
                    <div class="error-icon"><span class="material-icons md-18">warning</span></div>
                    <div class="error-text">Failed to load repositories</div>
                </div>
            `;
        }
    }

    renderTaskRepos(repos) {
        const reposContent = this.container.querySelector('#task-repos-content');

        if (repos.length === 0) {
            reposContent.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon"><span class="material-icons md-36">source</span></div>
                    <div class="empty-text">No repositories associated with this task</div>
                </div>
            `;
            return;
        }

        reposContent.innerHTML = `
            <div class="repos-section">
                <h4>Repositories (${repos.length})</h4>
                ${repos.map(repo => this.renderRepoCard(repo)).join('')}
            </div>
        `;

        // Setup expand/collapse handlers
        reposContent.querySelectorAll('.repo-card-header').forEach(header => {
            header.addEventListener('click', () => {
                const card = header.parentElement;
                card.classList.toggle('expanded');
            });
        });
    }

    renderRepoCard(repo) {
        const accessBadge = repo.writable
            ? '<span class="badge-success">FULL access</span>'
            : '<span class="badge-muted">READ_ONLY</span>';

        const hasChanges = repo.files && repo.files.length > 0;
        const changesSummary = hasChanges
            ? `<span class="text-success">+${repo.total_lines_added}</span>, <span class="text-danger">-${repo.total_lines_deleted}</span>`
            : 'No changes';

        return `
            <div class="repo-card ${hasChanges ? '' : 'no-changes'}">
                <div class="repo-card-header">
                    <div class="repo-info">
                        <span class="material-icons md-18">folder</span>
                        <strong>${repo.name}</strong>
                        ${accessBadge}
                        <span class="role-badge role-${repo.role}">${repo.role}</span>
                    </div>
                    <div class="repo-stats">
                        ${hasChanges ? `
                            <span class="material-icons md-18">check</span>
                            <span>${repo.files.length} files changed (${changesSummary})</span>
                        ` : '<span class="text-muted">No changes</span>'}
                    </div>
                </div>
                ${hasChanges ? `
                    <div class="repo-card-body">
                        <div class="files-list">
                            ${repo.files.slice(0, 10).map(file => `
                                <div class="file-item">
                                    <span class="material-icons md-16">description</span>
                                    <code class="file-path">${file.path}</code>
                                    <span class="file-stats">
                                        <span class="text-success">+${file.lines_added || 0}</span>
                                        <span class="text-danger">-${file.lines_deleted || 0}</span>
                                    </span>
                                </div>
                            `).join('')}
                            ${repo.files.length > 10 ? `
                                <div class="text-muted">... and ${repo.files.length - 10} more files</div>
                            ` : ''}
                        </div>
                        ${repo.commit_hash ? `
                            <div class="repo-commit">
                                <span class="material-icons md-16">commit</span>
                                <span>Commit:</span>
                                <code class="code-inline">${repo.commit_hash}</code>
                            </div>
                        ` : ''}
                    </div>
                ` : ''}
            </div>
        `;
    }

    async loadTaskDependencies(taskId) {
        const depsContent = this.container.querySelector('#task-dependencies-content');

        try {
            const result = await apiClient.get(`/api/tasks/${taskId}/dependencies?include_reverse=true`, {
                requestId: `task-deps-${taskId}-${Date.now()}`
            });

            if (result.ok) {
                const data = result.data || {};
                this.renderTaskDependencies(data.depends_on || [], data.depended_by || []);
            } else {
                depsContent.innerHTML = `
                    <div class="error-message">
                        <div class="error-icon"><span class="material-icons md-18">warning</span></div>
                        <div class="error-text">Failed to load dependencies: ${result.message}</div>
                    </div>
                `;
            }
        } catch (error) {
            console.error('Failed to load task dependencies:', error);
            depsContent.innerHTML = `
                <div class="error-message">
                    <div class="error-icon"><span class="material-icons md-18">warning</span></div>
                    <div class="error-text">Failed to load dependencies</div>
                </div>
            `;
        }
    }

    renderTaskDependencies(dependsOn, dependedBy) {
        const depsContent = this.container.querySelector('#task-dependencies-content');

        if (dependsOn.length === 0 && dependedBy.length === 0) {
            depsContent.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon"><span class="material-icons md-36">link</span></div>
                    <div class="empty-text">No dependencies found</div>
                </div>
            `;
            return;
        }

        depsContent.innerHTML = `
            <div class="dependencies-section">
                ${dependsOn.length > 0 ? `
                    <div class="deps-group">
                        <h4>
                            <span class="material-icons md-18">arrow_downward</span>
                            Depends on (${dependsOn.length})
                        </h4>
                        <div class="deps-list">
                            ${dependsOn.map(dep => this.renderDependencyItem(dep, 'depends-on')).join('')}
                        </div>
                    </div>
                ` : ''}

                ${dependedBy.length > 0 ? `
                    <div class="deps-group">
                        <h4>
                            <span class="material-icons md-18">arrow_upward</span>
                            Depended by (${dependedBy.length})
                        </h4>
                        <div class="deps-list">
                            ${dependedBy.map(dep => this.renderDependencyItem(dep, 'depended-by')).join('')}
                        </div>
                    </div>
                ` : ''}
            </div>
        `;

        // Setup click handlers for viewing tasks
        depsContent.querySelectorAll('.btn-view-task').forEach(btn => {
            btn.addEventListener('click', async () => {
                const targetTaskId = btn.getAttribute('data-task-id');
                // Close current drawer and show the dependency task
                this.hideTaskDetail();
                // Fetch and show the dependency task
                const task = this.tasks.find(t => t.task_id === targetTaskId);
                if (task) {
                    await this.showTaskDetail(task);
                } else {
                    // Fetch task details if not in current list
                    try {
                        const result = await apiClient.get(`/api/tasks/${targetTaskId}`);
                        if (result.ok) {
                            await this.showTaskDetail(result.data);
                        }
                    } catch (error) {
                        showToast('Failed to load dependency task', 'error');
                    }
                }
            });
        });
    }

    renderDependencyItem(dep, direction) {
        const typeColors = {
            'requires': 'dep-requires',
            'suggests': 'dep-suggests',
            'blocks': 'dep-blocks'
        };

        const typeIcons = {
            'requires': 'link',
            'suggests': 'info',
            'blocks': 'block'
        };

        const typeClass = typeColors[dep.dependency_type] || 'dep-default';
        const typeIcon = typeIcons[dep.dependency_type] || 'link';
        const targetTaskId = direction === 'depends-on' ? dep.depends_on_task_id : dep.task_id;

        return `
            <div class="dependency-item ${typeClass}">
                <div class="dep-icon">
                    <span class="material-icons md-18">${typeIcon}</span>
                </div>
                <div class="dep-content">
                    <div class="dep-header">
                        <code class="code-inline">${targetTaskId}</code>
                        <span class="dep-type-badge dep-type-${dep.dependency_type}">${dep.dependency_type}</span>
                    </div>
                    ${dep.reason ? `
                        <div class="dep-reason">${dep.reason}</div>
                    ` : ''}
                    <div class="dep-meta">
                        <span>${this.formatTimestamp(dep.created_at)}</span>
                    </div>
                </div>
                <div class="dep-actions">
                    <button class="btn-link btn-view-task" data-task-id="${targetTaskId}">
                        View Task
                    </button>
                </div>
            </div>
        `;
    }

    async loadGuardianReviews(taskId) {
        const container = this.container.querySelector('#guardian-reviews-container');

        // Show loading state
        container.innerHTML = `
            <div class="guardian-loading">
                <div class="loading-spinner"></div>
                <span>Loading Guardian reviews...</span>
            </div>
        `;

        try {
            // Fetch verdict summary
            const verdictResp = await apiClient.get(`/api/guardian/targets/task/${taskId}/verdict`, {
                requestId: `guardian-verdict-${taskId}-${Date.now()}`
            });

            // Fetch full reviews
            const reviewsResp = await apiClient.get(`/api/guardian/reviews?target_type=task&target_id=${taskId}`, {
                requestId: `guardian-reviews-${taskId}-${Date.now()}`
            });

            if (verdictResp.ok && reviewsResp.ok) {
                const verdictData = verdictResp.data;
                const reviewsData = reviewsResp.data;

                // Render Guardian Reviews Panel
                this.renderGuardianReviewsPanel(container, verdictData, reviewsData.reviews || []);
            } else {
                const errorMsg = verdictResp.message || reviewsResp.message || 'Unknown error';
                container.innerHTML = `
                    <div class="error-message">
                        <div class="error-icon"><span class="material-icons md-18">warning</span></div>
                        <div class="error-text">Failed to load Guardian reviews: ${errorMsg}</div>
                    </div>
                `;
            }
        } catch (error) {
            console.error('Failed to load Guardian reviews:', error);
            container.innerHTML = `
                <div class="error-message">
                    <div class="error-icon"><span class="material-icons md-18">warning</span></div>
                    <div class="error-text">Failed to load Guardian reviews: ${error.message}</div>
                </div>
            `;
        }
    }

    renderGuardianReviewsPanel(container, verdictData, reviews) {
        const panel = new GuardianReviewPanel({
            container,
            verdictData,
            reviews
        });
        panel.render();
    }

    destroy() {
        // Cleanup
        this.container.innerHTML = '';
    }
}

// Export
window.TasksView = TasksView;
