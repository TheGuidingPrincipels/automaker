/**
 * POST /store-api-key endpoint - Store API key
 *
 * Supports storing API keys in two modes:
 * - Active (default): Key is stored and activated in process.env immediately
 * - Inactive: Key is stored in memory and credentials.json but NOT activated in process.env
 *
 * Inactive storage is useful when:
 * - User is in auth_token mode but wants to save their API key for later
 * - User wants to store multiple keys without switching which one is active
 *
 * Storage locations:
 * - credentials.json: Persistent storage (DATA_DIR/credentials.json)
 * - In-memory cache: Runtime access via getApiKey()
 * - process.env: Active keys only (when makeActive=true)
 */

import type { Request, Response } from 'express';
import {
  setApiKey,
  getErrorMessage,
  logError,
  PROVIDER_CONFIG,
  SUPPORTED_PROVIDERS,
  isSupportedProvider,
  resolveDataDirectory,
} from '../common.js';
import { createLogger } from '@automaker/utils';
import { isApiKeyDisabled } from '../../../lib/provider-auth-config.js';
import { SettingsService } from '../../../services/settings-service.js';

const logger = createLogger('Setup');

export function createStoreApiKeyHandler() {
  return async (req: Request, res: Response): Promise<void> => {
    try {
      const {
        provider,
        apiKey,
        makeActive = true,
      } = req.body as {
        provider: string;
        apiKey: string;
        /** If false, store the key but don't activate it in process.env. Defaults to true. */
        makeActive?: boolean;
      };

      if (!provider || !apiKey) {
        res.status(400).json({ success: false, error: 'provider and apiKey required' });
        return;
      }

      // Validate provider using shared configuration
      if (!isSupportedProvider(provider)) {
        res.status(400).json({
          success: false,
          error: `Unsupported provider: ${provider}. Supported: ${SUPPORTED_PROVIDERS.join(', ')}.`,
        });
        return;
      }

      // Block API key activation in OAuth-only mode (unless storing inactive)
      // When storing inactive keys, we allow it even in OAuth-only mode
      // because the key won't be used until the user switches modes
      if (makeActive && (provider === 'anthropic' || provider === 'openai')) {
        if (await isApiKeyDisabled(provider)) {
          res.status(403).json({
            success: false,
            error: 'API key storage is disabled in OAuth-only mode',
            apiKeyAuthDisabled: true,
          });
          return;
        }
      }

      // Get provider configuration from shared config
      const providerConfig = PROVIDER_CONFIG[provider];
      const { envKey, credentialsKey } = providerConfig;
      const dataDir = resolveDataDirectory();

      // Persist to credentials.json (DATA_DIR/credentials.json)
      const settingsService = new SettingsService(dataDir);
      const apiKeysUpdate: Partial<{
        anthropic: string;
        anthropic_oauth_token: string;
        google: string;
        openai: string;
      }> = { [credentialsKey]: apiKey };

      try {
        await settingsService.updateCredentials({ apiKeys: apiKeysUpdate });
        logger.info(`[Setup] Persisted ${provider} API key to credentials.json`);
      } catch (persistError) {
        logger.error(`[Setup] Failed to persist ${provider} API key:`, persistError);
        res.status(500).json({
          success: false,
          error: `Failed to persist API key: ${getErrorMessage(persistError)}`,
        });
        return;
      }

      // Store in memory cache only after persistence succeeds
      setApiKey(provider, apiKey);

      // Only activate in process.env if makeActive is true
      if (makeActive) {
        process.env[envKey] = apiKey;
        logger.info(`[Setup] Stored and activated API key as ${envKey}`);
      } else {
        logger.info(`[Setup] Stored API key for ${provider} (inactive - not set in process.env)`);
      }

      res.json({ success: true, active: makeActive });
    } catch (error) {
      logError(error, 'Store API key failed');
      res.status(500).json({ success: false, error: getErrorMessage(error) });
    }
  };
}
