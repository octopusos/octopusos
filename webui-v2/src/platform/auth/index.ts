/**
 * Platform Auth Layer - Public API
 *
 * Export all public auth utilities.
 */

export { getToken, setToken, clearToken, hasToken, getAuthHeader } from './adminToken';
export {
  evaluateWriteAccess,
  resolveWriteAccess,
  getCachedRuntimeMode,
  setCachedRuntimeMode,
  normalizeMode,
} from './writeAccess';
