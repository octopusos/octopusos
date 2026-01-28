/**
 * ProjectsView - Multi-repository project management UI
 *
 * Phase 6.2: WebUI Multi-repository view enhancement
 */

class ProjectsView {
    constructor(container) {
        this.container = container;
        this.projects = [];
        this.selectedProject = null;
        this.selectedRepo = null;

        this.init();
    }

    init() {
        this.container.innerHTML = `
            <div class="projects-view">
                <div class="view-header">
                    <h2>Projects & Repositories</h2>
                    <div class="header-actions">
                        <button class="btn-refresh" id="projects-refresh">
                            <span class="icon"><span class="material-icons md-18">refresh</span></span> Refresh
                        </button>
                    </div>
                </div>

                <div class="projects-content">
                    <!-- Projects List -->
                    <div id="projects-list" class="projects-section">
                        <div class="loading-spinner">Loading projects...</div>
                    </div>

                    <!-- Project Detail Drawer -->
                    <div id="project-detail-drawer" class="drawer hidden">
                        <div class="drawer-overlay" id="project-drawer-overlay"></div>
                        <div class="drawer-content">
                            <div class="drawer-header">
                                <h3>Project Details</h3>
                                <button class="btn-close" id="project-drawer-close">✕</button>
                            </div>
                            <div class="drawer-body" id="project-drawer-body">
                                <!-- Project details will be rendered here -->
                            </div>
                        </div>
                    </div>

                    <!-- Repo Detail Drawer -->
                    <div id="repo-detail-drawer" class="drawer hidden">
                        <div class="drawer-overlay" id="repo-drawer-overlay"></div>
                        <div class="drawer-content">
                            <div class="drawer-header">
                                <h3>Repository Details</h3>
                                <button class="btn-close" id="repo-drawer-close">✕</button>
                            </div>
                            <div class="drawer-body" id="repo-drawer-body">
                                <!-- Repo details will be rendered here -->
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;

        this.setupEventListeners();
        this.loadProjects();
    }

    setupEventListeners() {
        // Refresh button
        this.container.querySelector('#projects-refresh').addEventListener('click', () => {
            this.loadProjects(true);
        });

        // Project drawer close
        this.container.querySelector('#project-drawer-close').addEventListener('click', () => {
            this.hideProjectDetail();
        });

        this.container.querySelector('#project-drawer-overlay').addEventListener('click', () => {
            this.hideProjectDetail();
        });

        // Repo drawer close
        this.container.querySelector('#repo-drawer-close').addEventListener('click', () => {
            this.hideRepoDetail();
        });

        this.container.querySelector('#repo-drawer-overlay').addEventListener('click', () => {
            this.hideRepoDetail();
        });
    }

    async loadProjects(forceRefresh = false) {
        const projectsList = this.container.querySelector('#projects-list');
        projectsList.innerHTML = '<div class="loading-spinner">Loading projects...</div>';

        try {
            const result = await apiClient.get('/api/projects', {
                requestId: `projects-list-${Date.now()}`
            });

            if (result.ok) {
                this.projects = result.data || [];
                this.renderProjects();

                if (forceRefresh) {
                    showToast('Projects refreshed', 'success', 2000);
                }
            } else {
                projectsList.innerHTML = `
                    <div class="error-message">
                        <div class="error-icon"><span class="material-icons md-18">warning</span></div>
                        <div class="error-text">Failed to load projects: ${result.message}</div>
                    </div>
                `;
            }
        } catch (error) {
            console.error('Failed to load projects:', error);
            projectsList.innerHTML = `
                <div class="error-message">
                    <div class="error-icon"><span class="material-icons md-18">warning</span></div>
                    <div class="error-text">Failed to load projects</div>
                </div>
            `;
        }
    }

    renderProjects() {
        const projectsList = this.container.querySelector('#projects-list');

        if (this.projects.length === 0) {
            projectsList.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon"><span class="material-icons md-36">folder_open</span></div>
                    <div class="empty-text">No projects found</div>
                </div>
            `;
            return;
        }

        projectsList.innerHTML = `
            <div class="projects-grid">
                ${this.projects.map(project => this.renderProjectCard(project)).join('')}
            </div>
        `;

        // Setup click handlers
        projectsList.querySelectorAll('.project-card').forEach(card => {
            card.addEventListener('click', () => {
                const projectId = card.getAttribute('data-project-id');
                this.showProjectDetail(projectId);
            });
        });
    }

    renderProjectCard(project) {
        return `
            <div class="project-card" data-project-id="${project.project_id}">
                <div class="project-card-header">
                    <span class="material-icons md-24">folder</span>
                    <h4>${project.name}</h4>
                </div>
                <div class="project-card-body">
                    <div class="project-stat">
                        <span class="stat-label">Repositories</span>
                        <span class="stat-value">${project.repo_count}</span>
                    </div>
                    <div class="project-meta">
                        <span class="material-icons md-16">schedule</span>
                        <span>${this.formatTimestamp(project.created_at)}</span>
                    </div>
                </div>
            </div>
        `;
    }

    async showProjectDetail(projectId) {
        this.selectedProject = projectId;
        const drawer = this.container.querySelector('#project-detail-drawer');
        const drawerBody = this.container.querySelector('#project-drawer-body');

        // Show drawer with loading state
        drawer.classList.remove('hidden');
        drawerBody.innerHTML = '<div class="loading-spinner">Loading project details...</div>';

        try {
            const result = await apiClient.get(`/api/projects/${projectId}`, {
                requestId: `project-detail-${projectId}`
            });

            if (result.ok) {
                const project = result.data;
                this.renderProjectDetail(project);
            } else {
                drawerBody.innerHTML = `
                    <div class="error-message">
                        <div class="error-icon"><span class="material-icons md-18">warning</span></div>
                        <div class="error-text">Failed to load project details: ${result.message}</div>
                    </div>
                `;
            }
        } catch (error) {
            console.error('Failed to load project detail:', error);
            drawerBody.innerHTML = `
                <div class="error-message">
                    <div class="error-icon"><span class="material-icons md-18">warning</span></div>
                    <div class="error-text">Failed to load project details</div>
                </div>
            `;
        }
    }

    renderProjectDetail(project) {
        const drawerBody = this.container.querySelector('#project-drawer-body');

        drawerBody.innerHTML = `
            <div class="project-detail">
                <!-- Project Info -->
                <div class="detail-section">
                    <h4>Project Information</h4>
                    <div class="detail-grid">
                        <div class="detail-item">
                            <label>Project ID</label>
                            <div class="detail-value"><code>${project.project_id}</code></div>
                        </div>
                        <div class="detail-item">
                            <label>Name</label>
                            <div class="detail-value">${project.name}</div>
                        </div>
                        <div class="detail-item">
                            <label>Repositories</label>
                            <div class="detail-value">${project.repo_count}</div>
                        </div>
                        <div class="detail-item">
                            <label>Workspace Root</label>
                            <div class="detail-value"><code>${project.workspace_root || 'N/A'}</code></div>
                        </div>
                    </div>
                </div>

                <!-- Repositories Tab -->
                <div class="detail-section">
                    <h4>Repositories (${project.repos.length})</h4>
                    ${project.repos.length > 0 ? `
                        <div class="repos-table">
                            <table>
                                <thead>
                                    <tr>
                                        <th>Name</th>
                                        <th>URL</th>
                                        <th>Role</th>
                                        <th>Writable</th>
                                        <th>Actions</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${project.repos.map(repo => `
                                        <tr>
                                            <td><strong>${repo.name}</strong></td>
                                            <td><code class="code-inline">${repo.remote_url || 'Local'}</code></td>
                                            <td><span class="role-badge role-${repo.role}">${repo.role}</span></td>
                                            <td>${repo.is_writable ? '<span class="badge-success"><span class="material-icons" style="font-size: 14px; vertical-align: middle;">check</span></span>' : '<span class="badge-muted">Read-only</span>'}</td>
                                            <td>
                                                <button class="btn-link btn-view-repo" data-repo-id="${repo.repo_id}" data-project-id="${project.project_id}">
                                                    View
                                                </button>
                                            </td>
                                        </tr>
                                    `).join('')}
                                </tbody>
                            </table>
                        </div>
                    ` : '<p class="text-muted">No repositories in this project</p>'}
                </div>
            </div>
        `;

        // Setup repo view buttons
        drawerBody.querySelectorAll('.btn-view-repo').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const repoId = btn.getAttribute('data-repo-id');
                const projectId = btn.getAttribute('data-project-id');
                this.showRepoDetail(projectId, repoId);
            });
        });
    }

    async showRepoDetail(projectId, repoId) {
        this.selectedRepo = repoId;
        const drawer = this.container.querySelector('#repo-detail-drawer');
        const drawerBody = this.container.querySelector('#repo-drawer-body');

        // Show drawer with loading state
        drawer.classList.remove('hidden');
        drawerBody.innerHTML = '<div class="loading-spinner">Loading repository details...</div>';

        try {
            // Fetch repo details and tasks in parallel
            const [repoResult, tasksResult] = await Promise.all([
                apiClient.get(`/api/projects/${projectId}/repos/${repoId}`, {
                    requestId: `repo-detail-${repoId}`
                }),
                apiClient.get(`/api/projects/${projectId}/repos/${repoId}/tasks`, {
                    requestId: `repo-tasks-${repoId}`
                })
            ]);

            if (repoResult.ok) {
                const repo = repoResult.data;
                const tasks = tasksResult.ok ? tasksResult.data : [];
                this.renderRepoDetail(repo, tasks);
            } else {
                drawerBody.innerHTML = `
                    <div class="error-message">
                        <div class="error-icon"><span class="material-icons md-18">warning</span></div>
                        <div class="error-text">Failed to load repository details: ${repoResult.message}</div>
                    </div>
                `;
            }
        } catch (error) {
            console.error('Failed to load repo detail:', error);
            drawerBody.innerHTML = `
                <div class="error-message">
                    <div class="error-icon"><span class="material-icons md-18">warning</span></div>
                    <div class="error-text">Failed to load repository details</div>
                </div>
            `;
        }
    }

    renderRepoDetail(repo, tasks) {
        const drawerBody = this.container.querySelector('#repo-drawer-body');

        // Calculate total stats from tasks
        const totalFiles = tasks.reduce((sum, task) => sum + task.files_changed, 0);
        const totalLinesAdded = tasks.reduce((sum, task) => sum + task.lines_added, 0);
        const totalLinesDeleted = tasks.reduce((sum, task) => sum + task.lines_deleted, 0);

        drawerBody.innerHTML = `
            <div class="repo-detail">
                <!-- Repo Info -->
                <div class="detail-section">
                    <h4>Repository Information</h4>
                    <div class="detail-grid">
                        <div class="detail-item">
                            <label>Name</label>
                            <div class="detail-value">${repo.name}</div>
                        </div>
                        <div class="detail-item">
                            <label>Repository ID</label>
                            <div class="detail-value"><code>${repo.repo_id}</code></div>
                        </div>
                        <div class="detail-item">
                            <label>Remote URL</label>
                            <div class="detail-value"><code class="code-inline">${repo.remote_url || 'Local'}</code></div>
                        </div>
                        <div class="detail-item">
                            <label>Role</label>
                            <div class="detail-value"><span class="role-badge role-${repo.role}">${repo.role}</span></div>
                        </div>
                        <div class="detail-item">
                            <label>Access</label>
                            <div class="detail-value">${repo.is_writable ? '<span class="badge-success">Writable</span>' : '<span class="badge-muted">Read-only</span>'}</div>
                        </div>
                        <div class="detail-item">
                            <label>Default Branch</label>
                            <div class="detail-value"><code>${repo.default_branch}</code></div>
                        </div>
                        <div class="detail-item">
                            <label>Workspace Path</label>
                            <div class="detail-value"><code>${repo.workspace_relpath}</code></div>
                        </div>
                        <div class="detail-item">
                            <label>Tasks</label>
                            <div class="detail-value">${repo.task_count || tasks.length}</div>
                        </div>
                    </div>
                </div>

                <!-- Statistics -->
                ${tasks.length > 0 ? `
                    <div class="detail-section">
                        <h4>Statistics</h4>
                        <div class="stats-grid">
                            <div class="stat-card">
                                <div class="stat-value">${totalFiles}</div>
                                <div class="stat-label">Files Changed</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-value text-success">+${totalLinesAdded}</div>
                                <div class="stat-label">Lines Added</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-value text-danger">-${totalLinesDeleted}</div>
                                <div class="stat-label">Lines Deleted</div>
                            </div>
                        </div>
                    </div>
                ` : ''}

                <!-- Tasks Timeline -->
                <div class="detail-section">
                    <h4>Tasks (${tasks.length})</h4>
                    ${tasks.length > 0 ? `
                        <div class="tasks-timeline">
                            ${tasks.map(task => `
                                <div class="timeline-item">
                                    <div class="timeline-marker"></div>
                                    <div class="timeline-content">
                                        <div class="timeline-header">
                                            <code class="code-inline">${task.task_id}</code>
                                            <span class="timeline-time">${this.formatTimestamp(task.created_at)}</span>
                                        </div>
                                        <div class="timeline-stats">
                                            <span>${task.files_changed} files</span>
                                            <span class="text-success">+${task.lines_added}</span>
                                            <span class="text-danger">-${task.lines_deleted}</span>
                                            ${task.commit_hash ? `<code class="code-inline">${task.commit_hash.substring(0, 7)}</code>` : ''}
                                        </div>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    ` : '<p class="text-muted">No tasks have modified this repository</p>'}
                </div>
            </div>
        `;
    }

    hideProjectDetail() {
        const drawer = this.container.querySelector('#project-detail-drawer');
        drawer.classList.add('hidden');
        this.selectedProject = null;
    }

    hideRepoDetail() {
        const drawer = this.container.querySelector('#repo-detail-drawer');
        drawer.classList.add('hidden');
        this.selectedRepo = null;
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

    destroy() {
        // Cleanup
        this.container.innerHTML = '';
    }
}

// Export
window.ProjectsView = ProjectsView;
