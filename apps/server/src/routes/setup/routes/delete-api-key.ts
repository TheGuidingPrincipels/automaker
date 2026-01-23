/**
 * POST /delete-api-key endpoint - Delete a stored API key
 *
 * Removes API key from:
 * - In-memory cache
 * - process.env
 * - credentials.json (DATA_DIR/credentials.json)
 * - .env file (legacy cleanup)
 */

import type { Request, Response } from 'express';
import { createLogger } from '@automaker/utils';
import path from 'path';
import { secureFs } from '@automaker/platform';
import { SettingsService } from '../../../services/settings-service.js';
import {
  setApiKey,
  PROVIDER_CONFIG,
  SUPPORTED_PROVIDERS,
  isSupportedProvider,
  resolveDataDirectory,
} from '../common.js';

const logger = createLogger('Setup');

/**
 * Remove an API key from the .env file
 * Uses centralized secureFs.removeEnvKey for path validation
 */
async function removeApiKeyFromEnv(key: string): Promise<void> {
  const envPath = path.join(process.cwd(), '.env');

  try {
    await secureFs.removeEnvKey(envPath, key);
    logger.info(`[Setup] Removed ${key} from .env file`);
  } catch (error) {
    logger.error(`[Setup] Failed to remove ${key} from .env:`, error);
    throw error;
  }
}

export function createDeleteApiKeyHandler() {
  return async (req: Request, res: Response): Promise<void> => {
    try {
      const { provider } = req.body as { provider: string };

      if (!provider) {
        res.status(400).json({
          success: false,
          error: 'Provider is required',
        });
        return;
      }

      // Validate provider using shared configuration
      if (!isSupportedProvider(provider)) {
        res.status(400).json({
          success: false,
          error: `Unknown provider: ${provider}. Supported: ${SUPPORTED_PROVIDERS.join(', ')}.`,
        });
        return;
      }

      logger.info(`[Setup] Deleting API key for provider: ${provider}`);

      // Get provider configuration from shared config
      const providerConfig = PROVIDER_CONFIG[provider];
      const { envKey, credentialsKey } = providerConfig;

      // Clear from in-memory storage
      setApiKey(provider, '');

      // Remove from environment
      delete process.env[envKey];

      // Remove from credentials.json
      const dataDir = resolveDataDirectory();
      const settingsService = new SettingsService(dataDir);
      const apiKeysUpdate: Partial<{
        anthropic: string;
        anthropic_oauth_token: string;
        google: string;
        openai: string;
      }> = { [credentialsKey]: '' };

      await settingsService.updateCredentials({ apiKeys: apiKeysUpdate });
      logger.info(`[Setup] Removed ${provider} API key from credentials.json`);

      // Remove from .env file (legacy cleanup)
      await removeApiKeyFromEnv(envKey);

      logger.info(`[Setup] Successfully deleted API key for ${provider}`);

      res.json({
        success: true,
        message: `API key for ${provider} has been deleted`,
      });
    } catch (error) {
      logger.error('[Setup] Delete API key error:', error);
      res.status(500).json({
        success: false,
        error: error instanceof Error ? error.message : 'Failed to delete API key',
      });
    }
  };
}
