/**
 * Global type declarations for AgentOS WebUI
 *
 * This file declares types for global objects and functions attached to the window object.
 * It prevents TypeScript warnings and provides type safety for WebUI components.
 */

declare global {
  interface Window {
    // API Client
    apiClient: any;

    // Navigation
    navigateToView: (viewName: string, filters?: Record<string, any>) => void;

    // Toast notifications
    showToast: (message: string, type: string, duration?: number) => void;
    toastManager: any;
    Toast: any;

    // Dialog functions
    closeSaveSnippetDialog: () => void;
    submitSaveSnippet: () => Promise<void>;

    // Instance management
    startInstance: (providerId: string, instanceId: string) => Promise<void>;
    stopInstance: (providerId: string, instanceId: string) => Promise<void>;
    testInstance: (instanceKey: string) => Promise<void>;

    // View classes
    LeadScanHistoryView: any;
    GovernanceFindingsView: any;
    TasksView: any;
    KnowledgeHealthView: any;
    KnowledgePlaygroundView: any;
    SnippetsView: any;
    KnowledgeSourcesView: any;
    ProvidersView: any;
    EventsView: any;
    SessionsView: any;
    LogsView: any;
    ProjectsView: any;
    currentSourcesView: any;

    // Component classes
    FilterBar: any;
    DataTable: any;
    JsonViewer: any;
    RouteDecisionCard: any;
    LiveIndicator: any;
    MultiLiveIndicator: any;
    AdminTokenGate: any;

    // Utility APIs
    SnippetsAPI: {
      saveSnippet: (data: any) => Promise<any>;
      getSnippets: (filters?: any) => Promise<any>;
      deleteSnippet: (id: string) => Promise<void>;
      updateSnippet: (id: string, data: any) => Promise<any>;
    };

    CodeBlockUtils: {
      enhanceCodeBlock: (block: HTMLElement) => void;
      copyCode: (button: HTMLElement) => void;
      downloadCode: (button: HTMLElement) => void;
    };

    // Security
    adminTokenGate: any;

    // Internal state (for debugging/testing)
    _selfCheckResults?: any;

    // External libraries
    Prism?: {
      highlightElement: (element: Element) => void;
      highlightAll: () => void;
    };
    marked?: any;
  }
}

// This export is required to make this a module
export {};
