/**
 * OctopusOS Service
 *
 * API functions for OctopusOS core entities:
 * - Projects (v2)
 * - Tasks (v2)
 * - Repos (v2)
 * - Sessions
 * - Task Templates
 * - Task Dependencies
 * - Task Events
 * - Task Audit
 */

import { get, post, put, patch, del } from '@platform/http';

// ============================================================================
// Temporary Types (Will be replaced by @modules imports in A8)
// ============================================================================

// Project Types
export interface Project {
  id: string;
  name: string;
  description?: string;
  status: string;
  created_at: string;
  updated_at?: string;
}

export interface ListProjectsRequest {
  page?: number;
  limit?: number;
  status?: string;
  search?: string;
}

export interface ListProjectsResponse {
  projects: Project[];
  total: number;
  page: number;
  limit: number;
}

export interface GetProjectResponse {
  project: Project;
}

export interface CreateProjectRequest {
  name: string;
  description?: string;
  status?: string;
  tags?: string[];
  default_workdir?: string;
  settings?: Record<string, any>;
}

export interface CreateProjectResponse {
  project: Project;
}

export interface UpdateProjectRequest {
  name?: string;
  description?: string;
  status?: string;
}

export interface UpdateProjectResponse {
  project: Project;
}

// Task Types
export interface Task {
  id: string;
  project_id?: string;
  session_id?: string;
  title: string;
  description?: string;
  status: string;
  priority?: string;
  created_at: string;
  updated_at?: string;
}

export interface ListTasksRequest {
  project_id?: string;
  session_id?: string;
  status?: string;
  page?: number;
  limit?: number;
}

export interface ListTasksResponse {
  tasks: Task[];
  total: number;
  page: number;
  limit: number;
}

export interface GetTaskResponse {
  task: Task;
}

export interface CreateTaskRequest {
  project_id?: string;
  session_id?: string;
  title: string;
  description?: string;
  status?: string;
  priority?: string;
}

export interface CreateTaskResponse {
  task: Task;
}

export interface CreateAndStartTaskRequest {
  project_id?: string;
  session_id?: string;
  title: string;
  description?: string;
  priority?: string;
}

export interface CreateAndStartTaskResponse {
  task: Task;
}

// Repo Types
export interface Repo {
  id: string;
  project_id: string;
  name: string;
  path: string;
  url?: string;
  created_at: string;
  updated_at?: string;
}

export interface ListReposRequest {
  project_id?: string;
  page?: number;
  limit?: number;
  role?: string;
}

export interface ListReposResponse {
  repos: Repo[];
  total: number;
  page: number;
  limit: number;
}

export interface GetRepoResponse {
  repo: Repo;
}

export interface CreateRepoRequest {
  project_id: string;
  name: string;
  path: string;
  url?: string;
}

export interface CreateRepoResponse {
  repo: Repo;
}

// Session Types
export interface Session {
  id: string;
  title: string;  // Backend uses 'title', not 'name'
  created_at: string;
  updated_at: string;
  message_count?: number;
  last_message?: string;
  unread_count?: number;
  tags?: string[];
  metadata?: Record<string, any>;
  conversation_mode?: string;
  execution_phase?: string;
}

export interface ListSessionsRequest {
  limit?: number;
  offset?: number;
}

// Backend returns array directly, not wrapped in { sessions: [...] }
export type ListSessionsResponse = Session[];

export interface GetSessionResponse {
  session: Session;
}

export interface CreateSessionRequest {
  title?: string;  // Backend uses 'title'
  tags?: string[];
  user_id?: string;
  metadata?: Record<string, unknown>;
}

// Backend returns Session directly, not wrapped in { session: ... }
// But we handle both formats for backward compatibility
export type CreateSessionResponse = Session | { session: Session }

// Session Message Types
export interface SessionMessage {
  id: string;
  session_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  metadata?: Record<string, any>;
}

export interface ListSessionMessagesRequest {
  limit?: number;
  offset?: number;
}

export interface ListSessionMessagesPayload {
  messages: SessionMessage[];
  total: number;
}

// Backend /api/sessions/{id}/messages currently returns array directly.
// Keep union for backward compatibility.
export type ListSessionMessagesResponse = SessionMessage[] | ListSessionMessagesPayload

// Task Template Types
export interface TaskTemplate {
  id: string;
  name: string;
  description?: string;
  template_data: Record<string, unknown>;
  created_at: string;
  updated_at?: string;
}

export interface ListTaskTemplatesRequest {
  page?: number;
  limit?: number;
}

export interface ListTaskTemplatesResponse {
  templates: TaskTemplate[];
  total: number;
}

export interface GetTaskTemplateResponse {
  template: TaskTemplate;
}

export interface CreateTaskTemplateRequest {
  name: string;
  description?: string;
  template_data: Record<string, unknown>;
}

export interface CreateTaskTemplateResponse {
  template: TaskTemplate;
}

export interface UpdateTaskTemplateRequest {
  name?: string;
  description?: string;
  template_data?: Record<string, unknown>;
}

export interface UpdateTaskTemplateResponse {
  template: TaskTemplate;
}

export interface CreateTaskFromTemplateRequest {
  project_id?: string;
  session_id?: string;
  variables?: Record<string, unknown>;
}

export interface CreateTaskFromTemplateResponse {
  task: Task;
}

// Task Dependency Types
export interface TaskDependency {
  task_id: string;
  depends_on_task_id: string;
  dependency_type?: string;
}

export interface GetTaskDependenciesResponse {
  dependencies: TaskDependency[];
}

export interface GetTaskDependencyGraphResponse {
  nodes: Array<{ id: string; label: string }>;
  edges: Array<{ from: string; to: string }>;
}

// Task Event Types
export interface TaskEvent {
  id: string;
  task_id: string;
  event_type: string;
  event_data: Record<string, unknown>;
  created_at: string;
}

export interface ListTaskEventsRequest {
  phase?: string;
  page?: number;
  limit?: number;
}

export interface ListTaskEventsResponse {
  events: TaskEvent[];
  total: number;
}

export interface GetTaskEventsHealthResponse {
  status: string;
  metrics: Record<string, unknown>;
}

// Task Audit Types
export interface TaskAudit {
  id: string;
  task_id: string;
  action: string;
  details: Record<string, unknown>;
  created_at: string;
}

export interface ListTaskAuditsResponse {
  audits: TaskAudit[];
  total: number;
}

export interface TaskArtifact {
  id: string;
  task_id: string;
  name: string;
  path: string;
  created_at: string;
}

export interface ListTaskArtifactsResponse {
  artifacts: TaskArtifact[];
  total: number;
}

// ============================================================================
// Phase 6.1 Index Jobs, Leads, Messages, Plugins, Tools, Triggers, Users
// ============================================================================

export interface IndexJob {
  job_id: string;
  type: string;
  status: string;
  progress: number;
  message: string;
  files_processed: number;
  chunks_processed: number;
  errors: number;
  created_at: string;
  updated_at: string;
  duration_ms?: number;
}

export interface GetIndexJobsResponse {
  ok: boolean;
  data: IndexJob[];
  error?: string;
}

export interface LeadScan {
  id: number;
  target: string;
  type: string;
  status: string;
  startedAt: string | null;
  completedAt: string | null;
}

export interface GetLeadScansResponse {
  data: LeadScan[];
  total: number;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  conversationId: string;
  timestamp: string;
  tokenCount: number;
}

export interface GetMessagesResponse {
  data: Message[];
  total: number;
}

export interface Plugin {
  id: number;
  name: string;
  version: string;
  category: string;
  status: string;
  author: string;
  description: string;
  installedAt: string;
}

export interface GetPluginsResponse {
  data: Plugin[];
  total: number;
}

export interface Tool {
  id: string;
  name: string;
  type: 'builtin' | 'mcp' | 'custom';
  status: 'active' | 'inactive' | 'error';
  provider: string;
  description: string;
  lastUsed: string;
}

export interface GetToolsResponse {
  data: Tool[];
  total: number;
}

export interface Trigger {
  id: string;
  title: string;
  description: string;
  type: string;
  status: string;
}

export interface GetTriggersResponse {
  data: Trigger[];
  total: number;
}

export interface User {
  id: number;
  username: string;
  email: string;
  role: string;
  status: string;
  lastLogin: string;
  createdAt: string;
}

export interface GetUsersResponse {
  data: User[];
  total: number;
}

// Answer Packs Types
export interface AnswerItem {
  question: string;
  answer: string;
  type?: string;
}

export interface AnswerPack {
  id: string;
  name: string;
  status: string;
  items_count: number;
  metadata: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface GetAnswerPacksResponse {
  ok: boolean;
  data: AnswerPack[];
  total: number;
  limit: number;
  offset: number;
}

export interface GetAnswerPackResponse {
  ok: boolean;
  data: {
    id: string;
    name: string;
    status: string;
    items: AnswerItem[];
    metadata: Record<string, any>;
    created_at: string;
    updated_at: string;
  };
}

export interface CreateAnswerPackRequest {
  name: string;
  description?: string;
  answers: AnswerItem[];
}

export interface CreateAnswerPackResponse {
  ok: boolean;
  data: {
    id: string;
    name: string;
    status: string;
    created_at: string;
  };
  message: string;
}

export interface ValidateAnswerPackResponse {
  ok: boolean;
  data: {
    valid: boolean;
    errors: string[];
    warnings: string[];
  };
}

export interface CreateApplyProposalRequest {
  target_intent_id: string;
  target_type?: string;
}

export interface CreateApplyProposalResponse {
  ok: boolean;
  data: {
    proposal_id: string;
    target_intent_id: string;
    preview: Record<string, any>;
    status: string;
  };
  message: string;
}

export interface RelatedItem {
  id: string;
  type: string;
  name: string;
  status: string;
}

export interface GetRelatedItemsResponse {
  ok: boolean;
  data: RelatedItem[];
}

// ============================================================================
// Service Functions
// ============================================================================

const normalizeProject = (project: any): Project => ({
  id: project?.id ?? project?.project_id ?? '',
  name: project?.name ?? '',
  description: project?.description ?? '',
  status: project?.status ?? 'active',
  created_at: project?.created_at ?? '',
  updated_at: project?.updated_at,
})

const normalizeRepo = (repo: any): Repo => ({
  id: repo?.id ?? repo?.repo_id ?? '',
  project_id: repo?.project_id ?? '',
  name: repo?.name ?? '',
  path: repo?.path ?? repo?.workspace_relpath ?? '',
  url: repo?.url ?? repo?.remote_url,
  created_at: repo?.created_at ?? '',
  updated_at: repo?.updated_at,
})

const normalizeTask = (task: any): Task => ({
  id: task?.id ?? task?.task_id ?? '',
  project_id: task?.project_id ?? undefined,
  session_id: task?.session_id ?? undefined,
  title: task?.title ?? '',
  description: task?.description ?? '',
  status: task?.status ?? 'created',
  priority: task?.priority ?? undefined,
  created_at: task?.created_at ?? '',
  updated_at: task?.updated_at,
})

export const octopusosService = {
  // CSRF Token Initialization
  async ensureCSRFToken(): Promise<void> {
    // Call the CSRF token endpoint to ensure cookie is set
    // This is a GET request, so it doesn't need CSRF protection
    await get<{ csrf_token: string }>('/api/csrf-token');
    // Wait a bit for browser to process Set-Cookie header
    await new Promise(resolve => setTimeout(resolve, 150));
  },

  // Projects API (v2)
  async listProjects(params?: ListProjectsRequest): Promise<ListProjectsResponse> {
    const limit = params?.limit ?? 20
    const page = params?.page ?? 1
    const offset = Math.max(0, (page - 1) * limit)
    const response = await get<{
      projects: any[]
      total: number
      limit: number
      offset: number
    }>('/api/projects', {
      params: {
        status: params?.status,
        search: params?.search,
        limit,
        offset,
      },
    })

    return {
      projects: (response.projects ?? []).map(normalizeProject),
      total: response.total ?? 0,
      page,
      limit: response.limit ?? limit,
    }
  },

  async getProject(id: string): Promise<GetProjectResponse> {
    const response = await get<any>(`/api/projects/${id}`)
    return { project: normalizeProject(response) }
  },

  async createProject(data: CreateProjectRequest): Promise<CreateProjectResponse> {
    const response = await post<any>('/api/projects', data)
    return { project: normalizeProject(response) }
  },

  async updateProject(id: string, data: UpdateProjectRequest): Promise<UpdateProjectResponse> {
    const response = await patch<any>(`/api/projects/${id}`, data)
    return { project: normalizeProject(response) }
  },

  async deleteProject(id: string): Promise<void> {
    await del(`/api/projects/${id}`);
  },

  async getProjectRepos(projectId: string, params?: ListReposRequest): Promise<ListReposResponse> {
    const response = await get<any[]>(`/api/projects/${projectId}/repos`, {
      params: {
        role: params?.role,
      },
    })
    const repos = (response ?? []).map(normalizeRepo)
    return {
      repos,
      total: repos.length,
      page: params?.page ?? 1,
      limit: params?.limit ?? repos.length,
    }
  },

  async createProjectRepo(projectId: string, data: CreateRepoRequest): Promise<CreateRepoResponse> {
    const response = await post<any>(`/api/projects/${projectId}/repos`, {
      name: data.name,
      remote_url: data.url ?? null,
      workspace_relpath: data.path,
      default_branch: 'main',
      role: 'code',
      is_writable: true,
    })
    return { repo: normalizeRepo(response) }
  },

  // Tasks API (v2)
  async listTasks(params?: ListTasksRequest): Promise<ListTasksResponse> {
    const response = await get<{
      tasks: any[]
      total: number
      page: number
      limit: number
    }>('/api/tasks', { params })
    return {
      tasks: (response.tasks ?? []).map(normalizeTask),
      total: response.total ?? 0,
      page: response.page ?? (params?.page ?? 1),
      limit: response.limit ?? (params?.limit ?? 25),
    }
  },

  async getTask(id: string): Promise<GetTaskResponse> {
    const response = await get<{ task: any }>(`/api/tasks/${id}`)
    return { task: normalizeTask(response.task) }
  },

  async createTask(data: CreateTaskRequest): Promise<CreateTaskResponse> {
    const response = await post<{ task: any }>('/api/tasks', data)
    return { task: normalizeTask(response.task) }
  },

  async createAndStartTask(data: CreateAndStartTaskRequest): Promise<CreateAndStartTaskResponse> {
    const response = await post<{ task: any }>('/api/tasks/create_and_start', data)
    return { task: normalizeTask(response.task) }
  },

  async deleteTask(id: string): Promise<void> {
    await del(`/api/tasks/${id}`);
  },

  async getTaskRoute(id: string): Promise<{ route: string }> {
    return get(`/api/tasks/${id}/route`);
  },

  async updateTaskRoute(id: string, data: { route: string }): Promise<void> {
    await post(`/api/tasks/${id}/route`, data);
  },

  async batchCreateTasks(data: { tasks: CreateTaskRequest[] }): Promise<{ tasks: Task[] }> {
    const response = await post<{ tasks: any[] }>('/api/tasks/batch', data)
    return { tasks: (response.tasks ?? []).map(normalizeTask) }
  },

  // Repos API (v2)
  async listRepos(params?: ListReposRequest): Promise<ListReposResponse> {
    const response = await get<{
      repos: any[]
      total: number
      page: number
      limit: number
    }>('/api/repos', { params })
    return {
      repos: (response.repos ?? []).map(normalizeRepo),
      total: response.total ?? 0,
      page: response.page ?? (params?.page ?? 1),
      limit: response.limit ?? (params?.limit ?? 25),
    }
  },

  async getRepo(id: string): Promise<GetRepoResponse> {
    const response = await get<{ repo: any }>(`/api/repos/${id}`)
    return { repo: normalizeRepo(response.repo) }
  },

  async createRepo(data: CreateRepoRequest): Promise<CreateRepoResponse> {
    const response = await post<{ repo: any }>('/api/repos', data)
    return { repo: normalizeRepo(response.repo) }
  },

  async updateRepo(id: string, data: Partial<CreateRepoRequest>): Promise<{ repo: Repo }> {
    const response = await patch<{ repo: any }>(`/api/repos/${id}`, data)
    return { repo: normalizeRepo(response.repo) }
  },

  async deleteRepo(id: string): Promise<void> {
    await del(`/api/repos/${id}`);
  },

  // Sessions API
  async listSessions(params?: ListSessionsRequest): Promise<ListSessionsResponse> {
    return get('/api/sessions', { params });
  },

  async getSession(id: string): Promise<GetSessionResponse> {
    return get(`/api/sessions/${id}`);
  },

  async createSession(data: CreateSessionRequest): Promise<CreateSessionResponse> {
    return post('/api/sessions', data);
  },

  async deleteSession(id: string): Promise<void> {
    return del(`/api/sessions/${id}`);
  },

  async deleteAllSessions(): Promise<{ status: string; deleted_count: number; message: string }> {
    return del('/api/sessions');
  },

  async getSessionMessages(sessionId: string, params?: ListSessionMessagesRequest): Promise<ListSessionMessagesResponse> {
    return get(`/api/sessions/${sessionId}/messages`, { params });
  },

  // P0: Chat Health Check API
  async checkChatHealth(): Promise<{
    is_healthy: boolean
    issues: string[]
    hints?: string[]
  }> {
    return get('/api/selfcheck/chat-health');
  },

  // P0: Providers & Models API
  async getProviders(): Promise<{
    local: Array<{
      id: string
      label: string
      type: string
      supports_models: boolean
      supports_start: boolean
      supports_auth: string[]
    }>
    cloud: Array<{
      id: string
      label: string
      type: string
      supports_models: boolean
      supports_start: boolean
      supports_auth: string[]
    }>
  }> {
    return get('/api/providers');
  },

  async getAllProvidersStatus(): Promise<{
    ts: string
    providers: Array<{
      id: string
      type: string
      state: string
      endpoint: string | null
      latency_ms: number | null
      last_ok_at?: string | null
      last_error?: string | null
      pid?: number | null
      pid_exists?: boolean | null
      port_listening?: boolean | null
      api_responding?: boolean | null
    }>
    cache_ttl_ms: number
  }> {
    return get('/api/providers/status');
  },

  async getProviderModels(provider: string): Promise<{
    provider_id: string
    models: Array<{
      id: string
      label: string
      context_window: number | null
    }>
  }> {
    return get(`/api/providers/${provider}/models`);
  },

  async getInstalledModels(): Promise<{
    models: Array<{
      name: string
      provider: string
      size: string
      modified: string
      digest: string
      family: string
      parameters: string
    }>
  }> {
    return get('/api/models/list');
  },

  // Task Templates API
  async listTaskTemplates(params?: ListTaskTemplatesRequest): Promise<ListTaskTemplatesResponse> {
    return get('/api/task-templates', { params });
  },

  async getTaskTemplate(id: string): Promise<GetTaskTemplateResponse> {
    return get(`/api/task-templates/${id}`);
  },

  async createTaskTemplate(data: CreateTaskTemplateRequest): Promise<CreateTaskTemplateResponse> {
    return post('/api/task-templates', data);
  },

  async updateTaskTemplate(id: string, data: UpdateTaskTemplateRequest): Promise<UpdateTaskTemplateResponse> {
    return put(`/api/task-templates/${id}`, data);
  },

  async deleteTaskTemplate(id: string): Promise<void> {
    return del(`/api/task-templates/${id}`);
  },

  async createTaskFromTemplate(
    templateId: string,
    data: CreateTaskFromTemplateRequest
  ): Promise<CreateTaskFromTemplateResponse> {
    return post(`/api/task-templates/${templateId}/tasks`, data);
  },

  // Task Dependencies API
  async getTaskDependencies(taskId: string): Promise<GetTaskDependenciesResponse> {
    return get(`/api/tasks/${taskId}/dependencies`);
  },

  async getTaskDependencyGraph(taskId: string): Promise<GetTaskDependencyGraphResponse> {
    return get(`/api/tasks/${taskId}/dependencies/graph`);
  },

  async getTaskRepos(taskId: string): Promise<ListReposResponse> {
    return get(`/api/tasks/${taskId}/repos`);
  },

  // Task Events API
  async listTaskEvents(taskId: string, params?: ListTaskEventsRequest): Promise<ListTaskEventsResponse> {
    return get(`/api/tasks/${taskId}/events`, { params });
  },

  async getTaskEventsLatest(taskId: string): Promise<{ event: TaskEvent | null }> {
    return get(`/api/tasks/${taskId}/events/latest`);
  },

  async getTaskEventsSnapshot(taskId: string): Promise<{ events: TaskEvent[] }> {
    return get(`/api/tasks/${taskId}/events/snapshot`);
  },

  async getTaskGraph(taskId: string): Promise<{ graph: Record<string, unknown> }> {
    return get(`/api/tasks/${taskId}/graph`);
  },

  async getTaskCheckpoints(taskId: string): Promise<{ checkpoints: Record<string, unknown>[] }> {
    return get(`/api/tasks/${taskId}/checkpoints`);
  },

  async getTaskEventsByPhase(taskId: string, phase: string, params?: ListTaskEventsRequest): Promise<ListTaskEventsResponse> {
    return get(`/api/tasks/${taskId}/events/phase/${phase}`, { params });
  },

  async getTaskEventsHealth(): Promise<GetTaskEventsHealthResponse> {
    return get('/api/events/health');
  },

  // Task Audit API
  async getTaskAudits(taskId: string): Promise<ListTaskAuditsResponse> {
    return get(`/api/tasks/${taskId}/audits`);
  },

  async getRepoAudits(repoId: string): Promise<ListTaskAuditsResponse> {
    return get(`/api/repos/${repoId}/audits`);
  },

  async getTaskArtifacts(taskId: string): Promise<ListTaskArtifactsResponse> {
    return get(`/api/tasks/${taskId}/artifacts`);
  },

  async getRepoArtifacts(repoId: string): Promise<ListTaskArtifactsResponse> {
    return get(`/api/repos/${repoId}/artifacts`);
  },

  // Governance Audit API
  async getGovernanceAudit(params?: {
    agent_id?: string;
    capability_id?: string;
    allowed?: boolean;
    limit?: number;
    offset?: number;
  }): Promise<{
    invocations: Array<{
      invocation_id: string;
      agent_id: string;
      capability_id: string;
      operation: string;
      allowed: boolean;
      reason: string;
      context: Record<string, unknown>;
      timestamp: string;
    }>;
    stats: {
      total: number;
      allowed: number;
      denied: number;
      success_rate: number;
    };
    pagination: {
      limit: number;
      offset: number;
      has_more: boolean;
    };
  }> {
    const queryParams = new URLSearchParams();
    if (params?.agent_id) queryParams.append('agent_id', params.agent_id);
    if (params?.capability_id) queryParams.append('capability_id', params.capability_id);
    if (params?.allowed !== undefined) queryParams.append('allowed', String(params.allowed));
    queryParams.append('limit', String(params?.limit ?? 100));
    queryParams.append('offset', String(params?.offset ?? 0));

    const response = await get(`/api/capability/governance/audit?${queryParams}`) as any;
    return response.data;
  },

  // Phase 6.1 Index Jobs API
  async getIndexJobs(): Promise<GetIndexJobsResponse> {
    return get('/api/knowledge/jobs');
  },

  // Phase 6.1 Lead Scans API
  async getLeadScans(): Promise<GetLeadScansResponse> {
    // Backend endpoint is /api/lead/scans
    const response = await get<{ scans: any[]; total: number }>('/api/lead/scans');
    // Transform to expected format
    return {
      data: response.scans || [],
      total: response.total || 0,
    };
  },

  // Phase 6.1 Messages API
  async getMessages(): Promise<GetMessagesResponse> {
    return get('/api/messages');
  },

  // Phase 6.1 Plugins API
  async getPlugins(): Promise<GetPluginsResponse> {
    return get('/api/plugins');
  },

  // Phase 6.1 Tools API
  async getTools(): Promise<GetToolsResponse> {
    return get('/api/tools');
  },

  // Phase 6.1 Triggers API
  async getTriggers(): Promise<GetTriggersResponse> {
    return get('/api/triggers');
  },

  // Phase 6.1 Users API
  async getUsers(): Promise<GetUsersResponse> {
    return get('/api/users');
  },

  // Answer Packs API
  async getAnswerPacks(params?: {
    search?: string;
    status?: string;
    limit?: number;
    offset?: number;
  }): Promise<GetAnswerPacksResponse> {
    const queryParams = new URLSearchParams();
    if (params?.search) queryParams.set('search', params.search);
    if (params?.status) queryParams.set('status', params.status);
    if (params?.limit !== undefined) queryParams.set('limit', params.limit.toString());
    if (params?.offset !== undefined) queryParams.set('offset', params.offset.toString());
    const query = queryParams.toString();
    return get(`/api/answers/packs${query ? `?${query}` : ''}`);
  },

  async getAnswerPack(packId: string): Promise<GetAnswerPackResponse> {
    return get(`/api/answers/packs/${packId}`);
  },

  async createAnswerPack(request: CreateAnswerPackRequest): Promise<CreateAnswerPackResponse> {
    return post('/api/answers/packs', request);
  },

  async validateAnswerPack(packId: string): Promise<ValidateAnswerPackResponse> {
    return post(`/api/answers/packs/${packId}/validate`, {});
  },

  async createApplyProposal(packId: string, request: CreateApplyProposalRequest): Promise<CreateApplyProposalResponse> {
    return post(`/api/answers/packs/${packId}/apply-proposal`, request);
  },

  async getRelatedItems(packId: string): Promise<GetRelatedItemsResponse> {
    return get(`/api/answers/packs/${packId}/related`);
  },

  // ============================================================================
  // Capability Dashboard
  // ============================================================================

  async getCapabilityDashboardStats(): Promise<import('../types/capability').CapabilityDashboardResponse> {
    return get('/api/capability/dashboard/stats');
  },
};
