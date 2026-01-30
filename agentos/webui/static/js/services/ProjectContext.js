/**
 * ProjectContext Service - Global project context management
 *
 * Task #18: UI displays current Project context (Step 1 - User mental model closure)
 *
 * Features:
 * - Manages current project selection
 * - Syncs with URL params and localStorage
 * - Provides project filtering utilities
 * - Notifies listeners of context changes
 */

class ProjectContextService {
    constructor() {
        this.currentProjectId = null;
        this.currentProject = null;
        this.projects = [];
        this.listeners = new Set();

        // Initialize from URL or localStorage
        this.loadFromUrl();
        if (!this.currentProjectId) {
            this.loadFromStorage();
        }
    }

    /**
     * Initialize the service - fetch projects and set current project
     */
    async init() {
        await this.loadProjects();

        if (this.currentProjectId) {
            await this.fetchCurrentProject();
        }

        this.notifyListeners();
    }

    /**
     * Load all projects from API
     */
    async loadProjects() {
        try {
            const result = await apiClient.get('/api/projects', {
                requestId: `project-context-load-${Date.now()}`
            });

            if (result.ok) {
                // API returns {projects: [...], total: N, limit: M, offset: O}
                this.projects = result.data?.projects || [];
            } else {
                console.error('Failed to load projects:', result.message);
                this.projects = [];
            }
        } catch (error) {
            console.error('Error loading projects:', error);
            this.projects = [];
        }
    }

    /**
     * Fetch details for current project
     */
    async fetchCurrentProject() {
        if (!this.currentProjectId) {
            this.currentProject = null;
            return;
        }

        try {
            const result = await apiClient.get(`/api/projects/${this.currentProjectId}`, {
                requestId: `project-context-fetch-${Date.now()}`
            });

            if (result.ok) {
                this.currentProject = result.data;
            } else {
                console.error('Failed to fetch current project:', result.message);
                this.currentProject = null;
            }
        } catch (error) {
            console.error('Error fetching current project:', error);
            this.currentProject = null;
        }
    }

    /**
     * Set current project
     */
    async setCurrentProject(projectId) {
        if (projectId === this.currentProjectId) return;

        this.currentProjectId = projectId;

        // Update storage and URL
        if (projectId) {
            localStorage.setItem('agentos_current_project', projectId);
            this.updateUrl();
            await this.fetchCurrentProject();
        } else {
            localStorage.removeItem('agentos_current_project');
            this.clearUrl();
            this.currentProject = null;
        }

        // Notify listeners
        this.notifyListeners();
    }

    /**
     * Get current project ID
     */
    getCurrentProjectId() {
        return this.currentProjectId;
    }

    /**
     * Get current project object
     */
    getCurrentProject() {
        return this.currentProject;
    }

    /**
     * Get all projects
     */
    getProjects() {
        return this.projects;
    }

    /**
     * Clear current project selection
     */
    clearCurrentProject() {
        this.setCurrentProject(null);
    }

    /**
     * Load project ID from URL parameter
     */
    loadFromUrl() {
        const urlParams = new URLSearchParams(window.location.search);
        const projectId = urlParams.get('project');
        if (projectId) {
            this.currentProjectId = projectId;
        }
    }

    /**
     * Load project ID from localStorage
     */
    loadFromStorage() {
        const storedProjectId = localStorage.getItem('agentos_current_project');
        if (storedProjectId) {
            this.currentProjectId = storedProjectId;
        }
    }

    /**
     * Update URL with current project
     */
    updateUrl() {
        if (!this.currentProjectId) return;

        const url = new URL(window.location);
        url.searchParams.set('project', this.currentProjectId);
        window.history.replaceState({}, '', url);
    }

    /**
     * Clear project from URL
     */
    clearUrl() {
        const url = new URL(window.location);
        url.searchParams.delete('project');
        window.history.replaceState({}, '', url);
    }

    /**
     * Build API URL with project filter
     */
    buildApiUrl(baseUrl, additionalParams = {}) {
        const url = new URL(baseUrl, window.location.origin);

        if (this.currentProjectId) {
            url.searchParams.set('project_id', this.currentProjectId);
        }

        Object.keys(additionalParams).forEach(key => {
            url.searchParams.set(key, additionalParams[key]);
        });

        return url.pathname + url.search;
    }

    /**
     * Register listener for context changes
     */
    addListener(callback) {
        this.listeners.add(callback);
        return () => this.listeners.delete(callback);
    }

    /**
     * Notify all listeners of context change
     */
    notifyListeners() {
        this.listeners.forEach(callback => {
            try {
                callback({
                    projectId: this.currentProjectId,
                    project: this.currentProject,
                    projects: this.projects
                });
            } catch (error) {
                console.error('Error in project context listener:', error);
            }
        });
    }

    /**
     * Get project name by ID
     */
    getProjectName(projectId) {
        const project = this.projects.find(p => p.project_id === projectId);
        return project ? project.name : projectId;
    }

    /**
     * Check if filtering by project
     */
    isFiltering() {
        return !!this.currentProjectId;
    }
}

// Create global singleton
window.projectContext = new ProjectContextService();

// Auto-initialize on DOM ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.projectContext.init();
    });
} else {
    window.projectContext.init();
}
