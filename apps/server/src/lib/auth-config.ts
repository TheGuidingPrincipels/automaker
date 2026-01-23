/**
 * Auth Config Utility - Anthropic-specific authentication mode management
 *
 * This module provides Anthropic-specific authentication functions that delegate
 * to the unified provider-auth-config module. It maintains backward compatibility
 * with existing code while leveraging the centralized provider authentication system.
 *
 * For new code, prefer using provider-auth-config.ts directly with provider='anthropic'.
 *
 * Provides functions to manage authentication mode for Anthropic API:
 * - 'auth_token': CLI OAuth authentication (subscription mode)
 * - 'api_key': API key authentication (pay-per-use mode)
 *
 * CRITICAL: In auth_token mode, API keys are completely ignored at 4 levels:
 * 1. Startup: process.env.ANTHROPIC_API_KEY is cleared
 * 2. Provider: buildEnv() explicitly sets ANTHROPIC_API_KEY = ''
 * 3. Subprocess: env vars are filtered based on mode
 * 4. UI: Mode indicator shows active mode
 *
 * Configuration priority:
 * 1. Environment variable AUTOMAKER_ANTHROPIC_AUTH_MODE takes precedence
 * 2. Legacy AUTOMAKER_DISABLE_API_KEY_AUTH (mapped to auth mode)
 * 3. Global settings anthropicAuthMode field
 * 4. Legacy settings disableApiKeyAuth field
 * 5. Default: 'auth_token'
 */

import { createLogger } from '@automaker/utils';
import type { AnthropicAuthMode } from '@automaker/types';
import {
  initializeProviderAuthMode,
  getProviderAuthModeSync,
  getProviderAuthMode,
  setProviderAuthModeRuntime,
  isApiKeyDisabledSync,
  isApiKeyDisabled,
  getProviderAuthStatus,
} from './provider-auth-config.js';

const logger = createLogger('AuthConfig');

/** Environment variable for disabling API key auth (legacy) */
const ENV_DISABLE_API_KEY_AUTH = 'AUTOMAKER_DISABLE_API_KEY_AUTH';

/**
 * Initialize auth mode at server startup.
 *
 * CRITICAL: This function MUST be called early in server startup,
 * BEFORE any provider or SDK code runs. It:
 *
 * 1. Determines the effective auth mode from env vars
 * 2. If mode is 'auth_token', CLEARS process.env.ANTHROPIC_API_KEY
 *    to prevent any fallback to API key usage
 * 3. Caches the mode for synchronous access
 *
 * Note: This function handles legacy env var mapping before delegating
 * to the unified provider-auth-config.
 *
 * @returns The effective auth mode
 */
export function initializeAuthMode(): AnthropicAuthMode {
  // Handle legacy env var mapping BEFORE delegating to provider-auth-config
  // This ensures legacy AUTOMAKER_DISABLE_API_KEY_AUTH is properly translated
  handleLegacyEnvVar();

  // Delegate to unified provider auth config
  return initializeProviderAuthMode('anthropic') as AnthropicAuthMode;
}

/**
 * Handle legacy AUTOMAKER_DISABLE_API_KEY_AUTH env var by mapping it
 * to the new AUTOMAKER_ANTHROPIC_AUTH_MODE format.
 *
 * This ensures backward compatibility with existing deployments.
 */
function handleLegacyEnvVar(): void {
  // Only process legacy var if new var is not set
  if (process.env.AUTOMAKER_ANTHROPIC_AUTH_MODE) {
    return;
  }

  const legacyDisabled = process.env[ENV_DISABLE_API_KEY_AUTH]?.toLowerCase();
  if (legacyDisabled === 'true') {
    process.env.AUTOMAKER_ANTHROPIC_AUTH_MODE = 'auth_token';
    logger.debug('Mapped legacy AUTOMAKER_DISABLE_API_KEY_AUTH=true to auth_token mode');
  } else if (legacyDisabled === 'false') {
    process.env.AUTOMAKER_ANTHROPIC_AUTH_MODE = 'api_key';
    logger.debug('Mapped legacy AUTOMAKER_DISABLE_API_KEY_AUTH=false to api_key mode');
  }
}

/**
 * Get auth mode synchronously (uses cached value after initialization).
 *
 * If initializeAuthMode() hasn't been called, falls back to env check.
 * Prefer this for performance-critical paths.
 *
 * @returns The current auth mode
 */
export function getAuthModeSync(): AnthropicAuthMode {
  return getProviderAuthModeSync('anthropic') as AnthropicAuthMode;
}

/**
 * Get auth mode asynchronously (checks settings file).
 *
 * Checks environment variables first (they take precedence),
 * then falls back to settings file if no env override.
 *
 * @returns Promise resolving to the auth mode
 */
export async function getAuthMode(): Promise<AnthropicAuthMode> {
  // Handle legacy env var mapping for async path as well
  handleLegacyEnvVar();
  return getProviderAuthMode('anthropic') as Promise<AnthropicAuthMode>;
}

/**
 * Set auth mode and update environment accordingly.
 *
 * This updates the cached mode and adjusts process.env.ANTHROPIC_API_KEY
 * based on the new mode.
 *
 * Note: This does NOT persist to settings - use SettingsService for that.
 * This is for runtime mode switching.
 *
 * @param mode The new auth mode to set
 */
export function setAuthModeRuntime(mode: AnthropicAuthMode): void {
  setProviderAuthModeRuntime('anthropic', mode);
}

/**
 * Check if API key authentication is disabled (OAuth-only mode).
 * This is a convenience function for backward compatibility.
 *
 * @deprecated Use getAuthMode() === 'auth_token' instead
 * @returns true if in auth_token mode (API keys disabled)
 */
export async function isApiKeyAuthDisabled(): Promise<boolean> {
  // Handle legacy env var mapping
  handleLegacyEnvVar();
  return isApiKeyDisabled('anthropic');
}

/**
 * Check if API key authentication is disabled (synchronous version).
 *
 * @deprecated Use getAuthModeSync() === 'auth_token' instead
 * @returns true if in auth_token mode (API keys disabled)
 */
export function isApiKeyAuthDisabledSync(): boolean {
  return isApiKeyDisabledSync('anthropic');
}

/**
 * Log the current authentication mode (for startup diagnostics).
 */
export async function logAuthMode(): Promise<void> {
  const mode = await getAuthMode();
  if (mode === 'auth_token') {
    logger.info('Auth Token mode active (subscription) - API key authentication is disabled');
  } else {
    logger.info('API Key mode active (pay-per-use) - using API key authentication');
  }
}

/**
 * Get auth status for API responses.
 * Provides detailed status information about the current auth configuration.
 */
export async function getAuthStatus(): Promise<{
  mode: AnthropicAuthMode;
  hasStoredOAuthToken: boolean;
  hasEnvAuthToken: boolean;
  hasCliOAuthToken: boolean;
  hasStoredApiKey: boolean;
  hasEnvApiKey: boolean;
  envApiKeyCleared: boolean;
}> {
  const providerStatus = await getProviderAuthStatus('anthropic');

  // Lazy import to avoid circular dependency
  const { getApiKey } = await import('../routes/setup/common.js');

  return {
    mode: providerStatus.mode as AnthropicAuthMode,
    hasStoredOAuthToken: !!getApiKey('anthropic_oauth_token'),
    hasEnvAuthToken: !!process.env.ANTHROPIC_AUTH_TOKEN,
    hasCliOAuthToken: !!process.env.CLAUDE_CODE_OAUTH_TOKEN,
    hasStoredApiKey: !!getApiKey('anthropic'),
    hasEnvApiKey: providerStatus.hasEnvApiKey,
    envApiKeyCleared: providerStatus.envApiKeyCleared,
  };
}
