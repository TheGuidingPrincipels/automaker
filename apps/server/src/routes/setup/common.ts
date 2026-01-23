/**
 * Common utilities and state for setup routes
 */

import { createLogger } from '@automaker/utils';
import path from 'path';
import { secureFs, getDataDirectory } from '@automaker/platform';
import { getErrorMessage as getErrorMessageShared, createLogError } from '../common.js';
import { SettingsService } from '../../services/settings-service.js';

const logger = createLogger('Setup');

// =============================================================================
// Provider Configuration
// =============================================================================

/**
 * Centralized provider configuration mapping.
 * Maps provider names to their environment variable keys and credentials.json field names.
 */
export const PROVIDER_CONFIG = {
  anthropic: { envKey: 'ANTHROPIC_API_KEY', credentialsKey: 'anthropic' },
  anthropic_oauth_token: {
    envKey: 'ANTHROPIC_AUTH_TOKEN',
    credentialsKey: 'anthropic_oauth_token',
  },
  google: { envKey: 'GOOGLE_API_KEY', credentialsKey: 'google' },
  openai: { envKey: 'OPENAI_API_KEY', credentialsKey: 'openai' },
} as const;

/** Supported provider names */
export type SupportedProvider = keyof typeof PROVIDER_CONFIG;

/** List of supported provider names for error messages */
export const SUPPORTED_PROVIDERS = Object.keys(PROVIDER_CONFIG) as SupportedProvider[];

/**
 * Type guard to check if a string is a supported provider
 */
export function isSupportedProvider(provider: string): provider is SupportedProvider {
  return provider in PROVIDER_CONFIG;
}

// =============================================================================
// Data Directory Resolution
// =============================================================================

/** Default data directory when no other configuration is available */
export const DEFAULT_DATA_DIR = './data';

/**
 * Resolve the data directory with consistent fallback chain.
 *
 * Priority order:
 * 1. Explicit directory passed as argument
 * 2. getDataDirectory() from @automaker/platform
 * 3. DATA_DIR environment variable
 * 4. DEFAULT_DATA_DIR constant ('./data')
 *
 * @param explicitDir - Optional explicit directory to use
 * @returns Resolved data directory path
 */
export function resolveDataDirectory(explicitDir?: string | null): string {
  if (explicitDir) return explicitDir;

  const platformDir = getDataDirectory();
  if (platformDir) return platformDir;

  if (process.env.DATA_DIR) return process.env.DATA_DIR;

  logger.warn(`[Setup] DATA_DIR not configured, defaulting to ${DEFAULT_DATA_DIR}`);
  return DEFAULT_DATA_DIR;
}

// Storage for API keys (in-memory cache) - private
const apiKeys: Record<string, string> = {};

/**
 * Get an API key for a provider
 */
export function getApiKey(provider: string): string | undefined {
  return apiKeys[provider];
}

/**
 * Set an API key for a provider
 */
export function setApiKey(provider: string, key: string): void {
  apiKeys[provider] = key;
}

/**
 * Get all API keys (for read-only access)
 */
export function getAllApiKeys(): Record<string, string> {
  return { ...apiKeys };
}

/**
 * Helper to persist API keys to .env file
 * Uses centralized secureFs.writeEnvKey for path validation
 */
export async function persistApiKeyToEnv(key: string, value: string): Promise<void> {
  const envPath = path.join(process.cwd(), '.env');

  try {
    await secureFs.writeEnvKey(envPath, key, value);
    logger.info(`[Setup] Persisted ${key} to .env file`);
  } catch (error) {
    logger.error(`[Setup] Failed to persist ${key} to .env:`, error);
    throw error;
  }
}

// Re-export shared utilities
export { getErrorMessageShared as getErrorMessage };
export const logError = createLogError(logger);

/**
 * Load API keys from credentials.json into memory cache
 *
 * Called during server startup to restore API keys from persistent storage.
 * This ensures keys stored in credentials.json are available via getApiKey()
 * after server restart.
 *
 * @param dataDir - Optional data directory path. If not provided, uses resolveDataDirectory()
 */
export async function loadApiKeysFromCredentials(dataDir?: string): Promise<void> {
  const dir = resolveDataDirectory(dataDir);

  try {
    const settingsService = new SettingsService(dir);
    const credentials = await settingsService.getCredentials();

    // Load each provider's API key into memory cache using centralized config
    for (const [provider, config] of Object.entries(PROVIDER_CONFIG)) {
      const key = credentials.apiKeys[config.credentialsKey as keyof typeof credentials.apiKeys];
      if (key) {
        setApiKey(provider, key);
        logger.info(`[Setup] Loaded ${provider} API key from credentials.json`);
      }
    }
  } catch (error) {
    logger.error('[Setup] Failed to load API keys from credentials.json:', error);
  }
}
