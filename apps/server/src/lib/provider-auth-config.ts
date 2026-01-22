/**
 * Provider Auth Config - Unified authentication mode management for all providers
 *
 * This module provides a centralized, provider-agnostic way to manage authentication modes
 * across multiple AI providers (Anthropic, OpenAI/Codex, etc.).
 *
 * For each provider, supports two authentication modes:
 * - 'auth_token': OAuth/CLI-based authentication (subscription mode)
 * - 'api_key': API key authentication (pay-per-use mode)
 *
 * CRITICAL: In auth_token mode, API keys are completely ignored at multiple defense layers:
 * 1. Startup: Provider-specific env vars (e.g., OPENAI_API_KEY) are cleared
 * 2. Provider: buildEnv() explicitly sets the env var to ''
 * 3. Subprocess: Env vars are filtered based on mode
 * 4. UI: Mode indicator shows active mode
 *
 * Configuration priority (per provider):
 * 1. Environment variable AUTOMAKER_{PROVIDER}_AUTH_MODE takes precedence
 * 2. Legacy AUTOMAKER_DISABLE_API_KEY_AUTH (global default)
 * 3. Global settings {provider}AuthMode field
 * 4. Default: 'auth_token' (strict mode - subscription first)
 */

import { getDataDirectory } from '@automaker/platform';
import { createLogger } from '@automaker/utils';
import type { AnthropicAuthMode, OpenaiAuthMode } from '@automaker/types';
import { SettingsService } from '../services/settings-service.js';

const logger = createLogger('ProviderAuthConfig');
const ENV_DISABLE_API_KEY_AUTH = 'AUTOMAKER_DISABLE_API_KEY_AUTH';

// ============================================================================
// Type Definitions
// ============================================================================

/**
 * Supported provider names for authentication gating
 */
export type AuthProvider = 'anthropic' | 'openai';

/**
 * Auth mode type - same for all providers
 */
export type AuthMode = 'auth_token' | 'api_key';

/**
 * Provider-specific configuration
 */
export interface ProviderAuthSpec {
  /** Environment variable for auth mode override (e.g., AUTOMAKER_OPENAI_AUTH_MODE) */
  envAuthModeVar: string;
  /** Environment variable for the provider's API key (e.g., OPENAI_API_KEY) */
  envApiKeyVar: string;
  /** Settings field name for auth mode (e.g., 'openaiAuthMode') */
  settingsField: keyof {
    anthropicAuthMode?: AnthropicAuthMode;
    openaiAuthMode?: OpenaiAuthMode;
  };
  /** Human-readable name for logging */
  displayName: string;
}

/**
 * Provider specifications - defines how to handle auth for each provider.
 *
 * TO ADD A NEW PROVIDER:
 * 1. Add the provider name to the `AuthProvider` type definition.
 * 2. Add the provider's auth mode type to `ProviderAuthSpec['settingsField']`.
 * 3. Add the provider's configuration to this `PROVIDER_SPECS` object.
 * 4. (Optional) Add a dedicated route handler if unique logic is required,
 *    or use the generic handlers (future work).
 */
const PROVIDER_SPECS: Record<AuthProvider, ProviderAuthSpec> = {
  anthropic: {
    envAuthModeVar: 'AUTOMAKER_ANTHROPIC_AUTH_MODE',
    envApiKeyVar: 'ANTHROPIC_API_KEY',
    settingsField: 'anthropicAuthMode',
    displayName: 'Anthropic',
  },
  openai: {
    envAuthModeVar: 'AUTOMAKER_OPENAI_AUTH_MODE',
    envApiKeyVar: 'OPENAI_API_KEY',
    settingsField: 'openaiAuthMode',
    displayName: 'OpenAI',
  },
};

/**
 * Auth status for a provider - detailed information about authentication configuration
 */
export interface ProviderAuthStatus {
  /** Current auth mode for this provider */
  mode: AuthMode;
  /** Whether API key auth is allowed (mode === 'api_key') */
  apiKeyAllowed: boolean;
  /** Whether the env API key was cleared at startup (auth_token mode) */
  envApiKeyCleared: boolean;
  /** Whether there's an API key in the environment (only true in api_key mode) */
  hasEnvApiKey: boolean;
}

// ============================================================================
// State Management
// ============================================================================

/** Cached auth modes for synchronous access after initialization */
const cachedAuthModes: Record<AuthProvider, AuthMode> = {
  anthropic: 'auth_token',
  openai: 'auth_token',
};

/** Track whether initialization has been called */
let initialized = false;

/** Cached SettingsService instance to prevent race conditions */
let settingsServiceInstance: SettingsService | null = null;

/**
 * Get or create a cached SettingsService instance.
 * Caching prevents race conditions when multiple async calls request settings simultaneously.
 */
function getSettingsService(): SettingsService | null {
  if (settingsServiceInstance) {
    return settingsServiceInstance;
  }
  const dataDir = getDataDirectory();
  if (!dataDir) {
    return null;
  }
  settingsServiceInstance = new SettingsService(dataDir);
  return settingsServiceInstance;
}

// ============================================================================
// Initialization
// ============================================================================

/**
 * Initialize auth modes for all providers at server startup.
 *
 * CRITICAL: This function MUST be called early in server startup,
 * BEFORE any provider or SDK code runs. It:
 *
 * 1. Determines the effective auth mode from env vars for each provider
 * 2. If mode is 'auth_token', CLEARS the provider's API key env var
 *    to prevent any fallback to API key usage
 * 3. Caches the modes for synchronous access
 *
 * @returns Object with the effective auth mode for each provider
 */
export function initializeProviderAuthModes(): Record<AuthProvider, AuthMode> {
  const modes: Record<AuthProvider, AuthMode> = {} as Record<AuthProvider, AuthMode>;

  for (const [provider, spec] of Object.entries(PROVIDER_SPECS) as [
    AuthProvider,
    ProviderAuthSpec,
  ][]) {
    const mode = getAuthModeFromEnv(provider);
    cachedAuthModes[provider] = mode;
    modes[provider] = mode;

    if (mode === 'auth_token') {
      // CRITICAL: Clear inherited env var to prevent accidental API key usage
      // This is defense layer 1 of 4
      const hadApiKey = !!process.env[spec.envApiKeyVar];
      delete process.env[spec.envApiKeyVar];
      // Double-ensure by setting to empty string (some code checks for truthy)
      process.env[spec.envApiKeyVar] = '';

      if (hadApiKey) {
        logger.info(
          `[${spec.displayName}] Auth Token mode: ${spec.envApiKeyVar} cleared from environment`
        );
        logger.info(
          `[${spec.displayName}] To use API key mode, set ${spec.envAuthModeVar}=api_key`
        );
      } else {
        logger.debug(`[${spec.displayName}] Auth Token mode active (no env API key to clear)`);
      }
    } else {
      logger.info(
        `[${spec.displayName}] API Key mode active - using ${spec.envApiKeyVar} from environment or credentials`
      );
    }
  }

  initialized = true;
  return modes;
}

/**
 * Initialize auth mode for a single provider.
 * Useful when you only need to initialize one provider.
 *
 * @param provider The provider to initialize
 * @returns The effective auth mode for that provider
 */
export function initializeProviderAuthMode(provider: AuthProvider): AuthMode {
  const spec = PROVIDER_SPECS[provider];
  const mode = getAuthModeFromEnv(provider);
  cachedAuthModes[provider] = mode;

  if (mode === 'auth_token') {
    const hadApiKey = !!process.env[spec.envApiKeyVar];
    delete process.env[spec.envApiKeyVar];
    process.env[spec.envApiKeyVar] = '';

    if (hadApiKey) {
      logger.info(
        `[${spec.displayName}] Auth Token mode: ${spec.envApiKeyVar} cleared from environment`
      );
    }
  }

  return mode;
}

// ============================================================================
// Environment-Based Mode Resolution (Synchronous)
// ============================================================================

/**
 * Get auth mode from environment variables only (synchronous).
 * Does NOT check settings file - use for early startup before settings are loaded.
 *
 * @param provider The provider to check
 * @returns The auth mode determined from environment variables
 */
function getAuthModeFromEnv(provider: AuthProvider): AuthMode {
  const envMode = resolveAuthModeFromEnv(provider);
  if (envMode) {
    return envMode;
  }

  // Default to auth_token (subscription mode - strict by default)
  return 'auth_token';
}

function getLegacyAuthModeFromEnv(): AuthMode | null {
  const legacyDisabled = process.env[ENV_DISABLE_API_KEY_AUTH]?.toLowerCase().trim();
  if (legacyDisabled === 'true') {
    return 'auth_token';
  }
  if (legacyDisabled === 'false') {
    return 'api_key';
  }
  return null;
}

function resolveAuthModeFromEnv(provider: AuthProvider): AuthMode | null {
  const spec = PROVIDER_SPECS[provider];

  const envMode = process.env[spec.envAuthModeVar]?.toLowerCase().trim();
  if (envMode === 'api_key' || envMode === 'auth_token') {
    return envMode as AuthMode;
  }

  return getLegacyAuthModeFromEnv();
}

// ============================================================================
// Synchronous Getters (Use Cached Values)
// ============================================================================

/**
 * Get auth mode synchronously (uses cached value after initialization).
 *
 * If initializeProviderAuthModes() hasn't been called, falls back to env check.
 * Prefer this for performance-critical paths.
 *
 * @param provider The provider to check
 * @returns The current auth mode
 */
export function getProviderAuthModeSync(provider: AuthProvider): AuthMode {
  if (initialized) {
    return cachedAuthModes[provider];
  }
  // Fallback to env-only check if not initialized
  return getAuthModeFromEnv(provider);
}

/**
 * Check if API key authentication is allowed for a provider (synchronous).
 *
 * @param provider The provider to check
 * @returns true if in api_key mode (API keys allowed), false if in auth_token mode
 */
export function isApiKeyAllowedSync(provider: AuthProvider): boolean {
  return getProviderAuthModeSync(provider) === 'api_key';
}

/**
 * Check if API key authentication is disabled for a provider (synchronous).
 * Inverse of isApiKeyAllowedSync - returns true when in auth_token (OAuth) mode.
 *
 * @param provider The provider to check
 * @returns true if in auth_token mode (API keys disabled)
 */
export function isApiKeyDisabledSync(provider: AuthProvider): boolean {
  return getProviderAuthModeSync(provider) === 'auth_token';
}

// ============================================================================
// Asynchronous Getters (Check Settings File)
// ============================================================================

/**
 * Get auth mode asynchronously (checks settings file).
 *
 * Checks environment variables first (they take precedence),
 * then falls back to settings file if no env override.
 *
 * @param provider The provider to check
 * @returns Promise resolving to the auth mode
 */
export async function getProviderAuthMode(provider: AuthProvider): Promise<AuthMode> {
  const spec = PROVIDER_SPECS[provider];

  // Environment variables take precedence (including legacy mapping)
  const envMode = resolveAuthModeFromEnv(provider);
  if (envMode) {
    return envMode;
  }

  // Check settings file using cached SettingsService instance
  try {
    const settingsService = getSettingsService();
    if (!settingsService) {
      return 'auth_token'; // Default when no data directory
    }

    const settings = await settingsService.getGlobalSettings();

    // Check provider-specific field
    const settingsValue = settings[spec.settingsField as keyof typeof settings] as
      | AuthMode
      | undefined;
    if (settingsValue === 'api_key' || settingsValue === 'auth_token') {
      return settingsValue;
    }

    return 'auth_token'; // Default
  } catch (error) {
    logger.warn(`Failed to read settings for ${spec.displayName} auth mode:`, error);
    return 'auth_token'; // Default on error
  }
}

/**
 * Check if API key authentication is allowed for a provider (async).
 *
 * @param provider The provider to check
 * @returns Promise resolving to true if in api_key mode
 */
export async function isApiKeyAllowed(provider: AuthProvider): Promise<boolean> {
  const mode = await getProviderAuthMode(provider);
  return mode === 'api_key';
}

/**
 * Check if API key authentication is disabled for a provider (async).
 *
 * @param provider The provider to check
 * @returns Promise resolving to true if in auth_token mode
 */
export async function isApiKeyDisabled(provider: AuthProvider): Promise<boolean> {
  const mode = await getProviderAuthMode(provider);
  return mode === 'auth_token';
}

// ============================================================================
// Runtime Mode Management
// ============================================================================

/**
 * Set auth mode at runtime and update environment accordingly.
 *
 * This updates the cached mode and adjusts the provider's API key env var
 * based on the new mode.
 *
 * Note: This does NOT persist to settings - use SettingsService for that.
 * This is for runtime mode switching.
 *
 * @param provider The provider to update
 * @param mode The new auth mode to set
 */
export function setProviderAuthModeRuntime(provider: AuthProvider, mode: AuthMode): void {
  const spec = PROVIDER_SPECS[provider];
  const oldMode = cachedAuthModes[provider];
  cachedAuthModes[provider] = mode;

  if (mode === 'auth_token' && oldMode !== 'auth_token') {
    // Switching TO auth_token mode - clear API key
    delete process.env[spec.envApiKeyVar];
    process.env[spec.envApiKeyVar] = '';
    logger.info(`[${spec.displayName}] Switched to Auth Token mode, cleared ${spec.envApiKeyVar}`);
  } else if (mode === 'api_key' && oldMode !== 'api_key') {
    logger.info(`[${spec.displayName}] Switched to API Key mode`);
  }
}

// ============================================================================
// Status Reporting
// ============================================================================

/**
 * Get detailed auth status for a provider.
 * Provides comprehensive status information for API responses and debugging.
 *
 * @param provider The provider to check
 * @returns Promise resolving to detailed auth status
 */
export async function getProviderAuthStatus(provider: AuthProvider): Promise<ProviderAuthStatus> {
  const spec = PROVIDER_SPECS[provider];
  const mode = await getProviderAuthMode(provider);
  const envApiKey = process.env[spec.envApiKeyVar];

  return {
    mode,
    apiKeyAllowed: mode === 'api_key',
    envApiKeyCleared: mode === 'auth_token' && envApiKey === '',
    // In auth_token mode, env API key should be empty/cleared
    hasEnvApiKey: mode === 'api_key' && !!envApiKey && envApiKey !== '',
  };
}

/**
 * Get auth status for all providers.
 *
 * @returns Promise resolving to status for all providers
 */
export async function getAllProviderAuthStatus(): Promise<
  Record<AuthProvider, ProviderAuthStatus>
> {
  const result: Partial<Record<AuthProvider, ProviderAuthStatus>> = {};

  for (const provider of Object.keys(PROVIDER_SPECS) as AuthProvider[]) {
    result[provider] = await getProviderAuthStatus(provider);
  }

  return result as Record<AuthProvider, ProviderAuthStatus>;
}

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Get the list of supported providers.
 *
 * @returns Array of provider names
 */
export function getSupportedProviders(): AuthProvider[] {
  return Object.keys(PROVIDER_SPECS) as AuthProvider[];
}

/**
 * Get the provider specification for a given provider.
 * Useful for accessing provider-specific env var names.
 *
 * @param provider The provider to get specs for
 * @returns The provider specification
 */
export function getProviderSpec(provider: AuthProvider): ProviderAuthSpec {
  return PROVIDER_SPECS[provider];
}

/**
 * Check if a provider name is valid.
 *
 * @param provider The provider name to check
 * @returns true if the provider is supported
 */
export function isValidProvider(provider: string): provider is AuthProvider {
  return provider in PROVIDER_SPECS;
}

/**
 * Log the current authentication mode for all providers (for startup diagnostics).
 */
export async function logAllProviderAuthModes(): Promise<void> {
  for (const provider of Object.keys(PROVIDER_SPECS) as AuthProvider[]) {
    const spec = PROVIDER_SPECS[provider];
    const mode = await getProviderAuthMode(provider);

    if (mode === 'auth_token') {
      logger.info(
        `[${spec.displayName}] Auth Token mode active (subscription) - API key authentication is disabled`
      );
    } else {
      logger.info(
        `[${spec.displayName}] API Key mode active (pay-per-use) - using API key authentication`
      );
    }
  }
}

// ============================================================================
// Backward Compatibility - Anthropic-Specific Aliases
// ============================================================================

/**
 * @deprecated Use getProviderAuthModeSync('anthropic') instead.
 * Kept for backward compatibility during migration.
 */
export function getAnthropicAuthModeSync(): AnthropicAuthMode {
  return getProviderAuthModeSync('anthropic') as AnthropicAuthMode;
}

/**
 * @deprecated Use getProviderAuthMode('anthropic') instead.
 * Kept for backward compatibility during migration.
 */
export async function getAnthropicAuthMode(): Promise<AnthropicAuthMode> {
  return getProviderAuthMode('anthropic') as Promise<AnthropicAuthMode>;
}

/**
 * @deprecated Use isApiKeyDisabledSync('anthropic') instead.
 * Kept for backward compatibility during migration.
 */
export function isAnthropicApiKeyDisabledSync(): boolean {
  return isApiKeyDisabledSync('anthropic');
}

// ============================================================================
// OpenAI-Specific Convenience Functions
// ============================================================================

/**
 * Get OpenAI auth mode synchronously.
 * Convenience function for common use case.
 */
export function getOpenaiAuthModeSync(): OpenaiAuthMode {
  return getProviderAuthModeSync('openai') as OpenaiAuthMode;
}

/**
 * Get OpenAI auth mode asynchronously.
 * Convenience function for common use case.
 */
export async function getOpenaiAuthMode(): Promise<OpenaiAuthMode> {
  return getProviderAuthMode('openai') as Promise<OpenaiAuthMode>;
}

/**
 * Check if OpenAI API key auth is disabled (in auth_token mode).
 * Convenience function for common use case.
 */
export function isOpenaiApiKeyDisabledSync(): boolean {
  return isApiKeyDisabledSync('openai');
}

/**
 * Check if OpenAI API key auth is allowed (in api_key mode).
 * Convenience function for common use case.
 */
export function isOpenaiApiKeyAllowedSync(): boolean {
  return isApiKeyAllowedSync('openai');
}
