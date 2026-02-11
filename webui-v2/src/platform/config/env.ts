/// <reference types="vite/client" />

/**
 * Platform Configuration - Environment Variables
 *
 * Centralized environment variable access for the platform layer.
 * All config values should be read from here, not directly from import.meta.env.
 */

import { getRuntimePublicOrigin } from './runtimeConfig'

interface PlatformConfig {
  /** Public origin used by the WebUI runtime */
  publicOrigin: string;

  /** Request timeout in milliseconds (default: 30000) */
  apiTimeout: number;

  /** Enable mock mode for development (default: false) */
  enableMock: boolean;

  /** Enable demo mode (default: true) */
  enableDemoMode: boolean;

}

/**
 * Parse and validate environment variables
 */
function parseEnv(): PlatformConfig {
  const publicOrigin = (import.meta.env.VITE_PUBLIC_ORIGIN || getRuntimePublicOrigin()).trim();
  const apiTimeout = parseInt(import.meta.env.VITE_API_TIMEOUT || '30000', 10);
  const enableMock = import.meta.env.VITE_ENABLE_MOCK === 'true';
  const enableDemoMode = import.meta.env.VITE_ENABLE_DEMO_MODE === 'true';

  // Validate critical values
  if (isNaN(apiTimeout) || apiTimeout <= 0) {
    console.warn('Invalid VITE_API_TIMEOUT, using default 30000ms');
  }

  return {
    publicOrigin,
    apiTimeout: isNaN(apiTimeout) ? 30000 : apiTimeout,
    enableMock,
    enableDemoMode,
  };
}

/**
 * Platform configuration singleton
 */
export const config: PlatformConfig = parseEnv();

/**
 * Check if running in development mode
 */
export const isDev = import.meta.env.DEV;

/**
 * Check if running in production mode
 */
export const isProd = import.meta.env.PROD;

/**
 * Log configuration on initialization (dev only)
 */
if (isDev) {
  console.log('[Platform] Configuration loaded:', {
    publicOrigin: config.publicOrigin,
    apiTimeout: config.apiTimeout,
    enableMock: config.enableMock,
    enableDemoMode: config.enableDemoMode,
  });
}
