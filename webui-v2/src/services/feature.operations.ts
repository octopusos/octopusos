export type FeatureKey =
  | 'FEATURE_CONFIG_WRITE'
  | 'FEATURE_EXTENSIONS_INSTALL'
  | 'FEATURE_MEMORY_PROPOSALS_REVIEW'
  | 'FEATURE_MODE_TOGGLE'
  | 'FEATURE_PROVIDERS_CONTROL'

export type FeatureOperation = {
  method: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
  path: string
}

export const FEATURE_OPERATIONS: Record<FeatureKey, FeatureOperation[]> = {
  FEATURE_CONFIG_WRITE: [
    { method: 'POST', path: '/api/config/entries' },
    { method: 'PUT', path: '/api/config/entries/{id}' },
    { method: 'DELETE', path: '/api/config/entries/{id}' },
  ],
  FEATURE_EXTENSIONS_INSTALL: [
    { method: 'POST', path: '/api/extensions/install-url' },
  ],
  FEATURE_MEMORY_PROPOSALS_REVIEW: [
    { method: 'POST', path: '/api/memory/proposals/{id}/approve' },
    { method: 'POST', path: '/api/memory/proposals/{id}/reject' },
    { method: 'POST', path: '/api/memory/propose' },
  ],
  FEATURE_MODE_TOGGLE: [
    { method: 'POST', path: '/api/demo-mode/enable' },
    { method: 'POST', path: '/api/demo-mode/disable' },
  ],
  FEATURE_PROVIDERS_CONTROL: [
    { method: 'POST', path: '/api/providers/{provider_id}/instances/{instance_id}/start' },
    { method: 'POST', path: '/api/providers/{provider_id}/instances/{instance_id}/stop' },
    { method: 'POST', path: '/api/providers/{provider_id}/instances/{instance_id}/restart' },
  ],
}

