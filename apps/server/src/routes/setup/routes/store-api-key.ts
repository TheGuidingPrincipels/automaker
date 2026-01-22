/**
 * POST /store-api-key endpoint - Store API key
 */

import type { Request, Response } from 'express';
import { setApiKey, persistApiKeyToEnv, getErrorMessage, logError } from '../common.js';
import { createLogger } from '@automaker/utils';
import { isApiKeyAuthDisabled } from '../../../lib/auth-config.js';

const logger = createLogger('Setup');

export function createStoreApiKeyHandler() {
  return async (req: Request, res: Response): Promise<void> => {
    try {
      // Block API key storage in OAuth-only mode
      if (await isApiKeyAuthDisabled()) {
        res.status(403).json({
          success: false,
          error: 'API key storage is disabled in OAuth-only mode',
          apiKeyAuthDisabled: true,
        });
        return;
      }

      const { provider, apiKey } = req.body as {
        provider: string;
        apiKey: string;
      };

      if (!provider || !apiKey) {
        res.status(400).json({ success: false, error: 'provider and apiKey required' });
        return;
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

      setApiKey(provider, apiKey);
      process.env[envKey] = apiKey;
      await persistApiKeyToEnv(envKey, apiKey);
      logger.info(`[Setup] Stored API key as ${envKey}`);

      res.json({ success: true });
    } catch (error) {
      logError(error, 'Store API key failed');
      res.status(500).json({ success: false, error: getErrorMessage(error) });
    }
  };
}
