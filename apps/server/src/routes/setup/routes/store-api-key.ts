/**
 * POST /store-api-key endpoint - Store API key
 *
 * Supports storing API keys in two modes:
 * - Active (default): Key is stored and activated in process.env immediately
 * - Inactive: Key is stored in memory and .env file but NOT activated in process.env
 *
 * Inactive storage is useful when:
 * - User is in auth_token mode but wants to save their API key for later
 * - User wants to store multiple keys without switching which one is active
 */

import type { Request, Response } from 'express';
import { setApiKey, persistApiKeyToEnv, getErrorMessage, logError } from '../common.js';
import { createLogger } from '@automaker/utils';
import { isApiKeyDisabled } from '../../../lib/provider-auth-config.js';

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

      const providerEnvMap: Record<string, string> = {
        anthropic: 'ANTHROPIC_API_KEY',
        anthropic_oauth_token: 'ANTHROPIC_AUTH_TOKEN',
        openai: 'OPENAI_API_KEY',
      };
      const envKey = providerEnvMap[provider];
      if (!envKey) {
        res.status(400).json({
          success: false,
          error: `Unsupported provider: ${provider}. Only anthropic and openai are supported.`,
        });
        return;
      }

      // Always store in memory cache
      setApiKey(provider, apiKey);

      // Always persist to .env file for future use
      await persistApiKeyToEnv(envKey, apiKey);

      // Only activate in process.env if makeActive is true
      if (makeActive) {
        process.env[envKey] = apiKey;
        logger.info(`[Setup] Stored and activated API key as ${envKey}`);
      } else {
        logger.info(`[Setup] Stored API key as ${envKey} (inactive - not set in process.env)`);
      }

      res.json({ success: true, active: makeActive });
    } catch (error) {
      logError(error, 'Store API key failed');
      res.status(500).json({ success: false, error: getErrorMessage(error) });
    }
  };
}
