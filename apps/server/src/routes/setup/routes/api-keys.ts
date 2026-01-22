/**
 * GET /api-keys endpoint - Get API keys status
 */

import type { Request, Response } from 'express';
import { getApiKey, getErrorMessage, logError } from '../common.js';
import { isApiKeyAuthDisabled } from '../../../lib/auth-config.js';

export function createApiKeysHandler() {
  return async (_req: Request, res: Response): Promise<void> => {
    try {
      const apiKeyAuthDisabled = await isApiKeyAuthDisabled();

      // In OAuth-only mode, report no API keys available
      if (apiKeyAuthDisabled) {
        res.json({
          success: true,
          apiKeyAuthDisabled: true,
          hasAnthropicKey: false,
          hasGoogleKey: false,
          hasOpenaiKey: false,
        });
        return;
      }

      res.json({
        success: true,
        apiKeyAuthDisabled: false,
        hasAnthropicKey: !!getApiKey('anthropic') || !!process.env.ANTHROPIC_API_KEY,
        hasGoogleKey: !!getApiKey('google'),
        hasOpenaiKey: !!getApiKey('openai') || !!process.env.OPENAI_API_KEY,
      });
    } catch (error) {
      logError(error, 'Get API keys failed');
      res.status(500).json({ success: false, error: getErrorMessage(error) });
    }
  };
}
