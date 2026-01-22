/**
 * Auth Config Utility - Centralized authentication mode management
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

import { getDataDirectory } from '@automaker/platform';
import { createLogger } from '@automaker/utils';
import type { AnthropicAuthMode } from '@automaker/types';
import { SettingsService } from '../services/settings-service.js';

const logger = createLogger('AuthConfig');

/** Environment variable for auth mode (new) */
const ENV_AUTH_MODE = 'AUTOMAKER_ANTHROPIC_AUTH_MODE';

/** Environment variable for disabling API key auth (legacy) */
const ENV_DISABLE_API_KEY_AUTH = 'AUTOMAKER_DISABLE_API_KEY_AUTH';

/** Cached auth mode for synchronous access after initialization */
let cachedAuthMode: AnthropicAuthMode = 'auth_token';

/** Flag to track if initialization has been called */
let initialized = false;

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
 * @returns The effective auth mode
 */
export function initializeAuthMode(): AnthropicAuthMode {
  const mode = getAuthModeFromEnv();
  cachedAuthMode = mode;
  initialized = true;

  if (mode === 'auth_token') {
    // CRITICAL: Clear inherited env var to prevent accidental API key usage
    // This is defense layer 1 of 4
    const hadApiKey = !!process.env.ANTHROPIC_API_KEY;
    delete process.env.ANTHROPIC_API_KEY;
    // Double-ensure by setting to empty string (some code checks for truthy)
    process.env.ANTHROPIC_API_KEY = '';

    if (hadApiKey) {
      logger.info('[AuthMode] Auth Token mode: ANTHROPIC_API_KEY cleared from environment');
      logger.info('[AuthMode] To use API key mode, set AUTOMAKER_ANTHROPIC_AUTH_MODE=api_key');
    } else {
      logger.debug('[AuthMode] Auth Token mode active (no env API key to clear)');
    }
  } else {
    logger.info(
      '[AuthMode] API Key mode active - using ANTHROPIC_API_KEY from environment or credentials'
    );
  }

  return mode;
}

/**
 * Get auth mode from environment variables only (synchronous).
 * Does NOT check settings file - use for early startup before settings are loaded.
 */
function getAuthModeFromEnv(): AnthropicAuthMode {
  // Check new env var first
  const envMode = process.env[ENV_AUTH_MODE]?.toLowerCase();
  if (envMode === 'api_key') return 'api_key';
  if (envMode === 'auth_token') return 'auth_token';

  // Check legacy env var
  const legacyDisabled = process.env[ENV_DISABLE_API_KEY_AUTH]?.toLowerCase();
  if (legacyDisabled === 'true') return 'auth_token';
  if (legacyDisabled === 'false') return 'api_key';

  // Default to auth_token (subscription mode)
  return 'auth_token';
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
  if (initialized) {
    return cachedAuthMode;
  }
  // Fallback to env-only check if not initialized
  return getAuthModeFromEnv();
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
  // Environment variables take precedence
  const envMode = process.env[ENV_AUTH_MODE]?.toLowerCase();
  if (envMode === 'api_key' || envMode === 'auth_token') {
    return envMode as AnthropicAuthMode;
  }

  const legacyEnv = process.env[ENV_DISABLE_API_KEY_AUTH]?.toLowerCase();
  if (legacyEnv === 'true') return 'auth_token';
  if (legacyEnv === 'false') return 'api_key';

  // Check settings file
  try {
    const dataDir = getDataDirectory();
    if (!dataDir) {
      return 'auth_token'; // Default
    }

    const settingsService = new SettingsService(dataDir);
    const settings = await settingsService.getGlobalSettings();

    // Check new field first
    if (settings.anthropicAuthMode === 'api_key' || settings.anthropicAuthMode === 'auth_token') {
      return settings.anthropicAuthMode;
    }

    // Check legacy field
    if (typeof settings.disableApiKeyAuth === 'boolean') {
      return settings.disableApiKeyAuth ? 'auth_token' : 'api_key';
    }

    return 'auth_token'; // Default
  } catch (error) {
    logger.warn('Failed to read settings for auth mode:', error);
    return 'auth_token'; // Default on error
  }
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
  const oldMode = cachedAuthMode;
  cachedAuthMode = mode;
  initialized = true;

  if (mode === 'auth_token' && oldMode !== 'auth_token') {
    // Switching TO auth_token mode - clear API key
    delete process.env.ANTHROPIC_API_KEY;
    process.env.ANTHROPIC_API_KEY = '';
    logger.info('[AuthMode] Switched to Auth Token mode, cleared ANTHROPIC_API_KEY');
  } else if (mode === 'api_key' && oldMode !== 'api_key') {
    logger.info('[AuthMode] Switched to API Key mode');
  }
}

/**
 * Check if API key authentication is disabled (OAuth-only mode).
 * This is a convenience function for backward compatibility.
 *
 * @deprecated Use getAuthMode() === 'auth_token' instead
 * @returns true if in auth_token mode (API keys disabled)
 */
export async function isApiKeyAuthDisabled(): Promise<boolean> {
  const mode = await getAuthMode();
  return mode === 'auth_token';
}

/**
 * Check if API key authentication is disabled (synchronous version).
 *
 * @deprecated Use getAuthModeSync() === 'auth_token' instead
 * @returns true if in auth_token mode (API keys disabled)
 */
export function isApiKeyAuthDisabledSync(): boolean {
  return getAuthModeSync() === 'auth_token';
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
  const mode = await getAuthMode();

  // Lazy import to avoid circular dependency
  const { getApiKey } = await import('../routes/setup/common.js');

  return {
    mode,
    hasStoredOAuthToken: !!getApiKey('anthropic_oauth_token'),
    hasEnvAuthToken: !!process.env.ANTHROPIC_AUTH_TOKEN,
    hasCliOAuthToken: !!process.env.CLAUDE_CODE_OAUTH_TOKEN,
    hasStoredApiKey: !!getApiKey('anthropic'),
    // In auth_token mode, env API key should be cleared
    hasEnvApiKey:
      mode === 'api_key' && !!process.env.ANTHROPIC_API_KEY && process.env.ANTHROPIC_API_KEY !== '',
    // Indicates if we cleared the env API key at startup
    envApiKeyCleared: mode === 'auth_token' && process.env.ANTHROPIC_API_KEY === '',
  };
}
