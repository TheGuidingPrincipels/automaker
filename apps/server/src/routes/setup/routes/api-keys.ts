/**
 * GET /api-keys endpoint - Get API keys status
 *
 * Returns both simple boolean flags for backward compatibility (hasAnthropicKey, etc.)
 * and detailed per-provider status including auth mode configuration.
 */

import type { Request, Response } from 'express';
import { getApiKey, getErrorMessage, logError } from '../common.js';
import { isApiKeyAuthDisabled } from '../../../lib/auth-config.js';
import { getAllProviderAuthStatus } from '../../../lib/provider-auth-config.js';

/**
 * Per-provider status for API response
 */
interface ProviderApiKeyStatus {
  /** Whether this provider has an API key configured (stored or env) */
  hasKey: boolean;
  /** Whether the key comes from environment variable */
  hasEnvKey: boolean;
  /** Whether the key is stored in the application */
  hasStoredKey: boolean;
  /** Auth mode for this provider */
  authMode: 'auth_token' | 'api_key';
  /** Whether API key auth is allowed for this provider */
  apiKeyAllowed: boolean;
}

export function createApiKeysHandler() {
  return async (_req: Request, res: Response): Promise<void> => {
    try {
      // Get per-provider auth status
      const providerAuthStatus = await getAllProviderAuthStatus();

      // Legacy: check if Anthropic API key auth is disabled (for backward compatibility)
      const apiKeyAuthDisabled = await isApiKeyAuthDisabled();

      // Build per-provider status
      const anthropicHasStoredKey = !!getApiKey('anthropic');
      const anthropicHasEnvKey =
        !!process.env.ANTHROPIC_API_KEY && process.env.ANTHROPIC_API_KEY !== '';
      const googleHasStoredKey = !!getApiKey('google');
      const googleHasEnvKey = !!process.env.GOOGLE_API_KEY && process.env.GOOGLE_API_KEY !== '';
      const openaiHasStoredKey = !!getApiKey('openai');
      const openaiHasEnvKey = !!process.env.OPENAI_API_KEY && process.env.OPENAI_API_KEY !== '';

      const providers: Record<string, ProviderApiKeyStatus> = {
        anthropic: {
          hasKey: anthropicHasStoredKey || anthropicHasEnvKey,
          hasEnvKey: anthropicHasEnvKey,
          hasStoredKey: anthropicHasStoredKey,
          authMode: providerAuthStatus.anthropic.mode,
          apiKeyAllowed: providerAuthStatus.anthropic.apiKeyAllowed,
        },
        google: {
          // Google doesn't have provider-auth-config yet, default to api_key mode
          hasKey: googleHasStoredKey || googleHasEnvKey,
          hasEnvKey: googleHasEnvKey,
          hasStoredKey: googleHasStoredKey,
          authMode: 'api_key',
          apiKeyAllowed: true,
        },
        openai: {
          hasKey: openaiHasStoredKey || openaiHasEnvKey,
          hasEnvKey: openaiHasEnvKey,
          hasStoredKey: openaiHasStoredKey,
          authMode: providerAuthStatus.openai.mode,
          apiKeyAllowed: providerAuthStatus.openai.apiKeyAllowed,
        },
      };

      res.json({
        success: true,
        // Legacy fields for backward compatibility
        apiKeyAuthDisabled,
        hasAnthropicKey: providers.anthropic.hasKey,
        hasGoogleKey: providers.google.hasKey,
        hasOpenaiKey: providers.openai.hasKey,
        // New per-provider detailed status
        providers,
      });
    } catch (error) {
      logError(error, 'Get API keys failed');
      res.status(500).json({ success: false, error: getErrorMessage(error) });
    }
  };
}
