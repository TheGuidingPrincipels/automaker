/**
 * OpenAI Auth Mode Routes - GET/POST endpoints for OpenAI authentication mode management
 *
 * Provides endpoints for:
 * - GET /api/setup/openai-auth-mode - Get current OpenAI auth mode and status
 * - POST /api/setup/openai-auth-mode - Set OpenAI auth mode (persists to settings)
 *
 * This is the OpenAI/Codex equivalent of the Anthropic auth-mode routes.
 * Controls whether the app uses Codex CLI OAuth (auth_token) or OPENAI_API_KEY (api_key).
 */

import type { Request, Response } from 'express';
import { getCodexAuthIndicators, getDataDirectory } from '@automaker/platform';
import { createLogger } from '@automaker/utils';
import type { OpenaiAuthMode } from '@automaker/types';
import {
  getProviderAuthMode,
  getProviderAuthStatus,
  setProviderAuthModeRuntime,
} from '../../../lib/provider-auth-config.js';
import { getApiKey } from '../common.js';
import { SettingsService } from '../../../services/settings-service.js';

const logger = createLogger('OpenaiAuthModeRoute');

/**
 * GET /api/setup/openai-auth-mode
 *
 * Returns the current OpenAI authentication mode and detailed status.
 *
 * Response:
 * {
 *   success: true,
 *   mode: 'auth_token' | 'api_key',
 *   status: {
 *     isAuthTokenMode: boolean,
 *     isApiKeyMode: boolean,
 *     apiKeyAllowed: boolean,
 *     envApiKeyCleared: boolean,
 *     hasEnvApiKey: boolean
 *   }
 * }
 */
export function createGetOpenaiAuthModeHandler() {
  return async (_req: Request, res: Response): Promise<void> => {
    try {
      const mode = await getProviderAuthMode('openai');
      const status = await getProviderAuthStatus('openai');
      const authIndicators = await getCodexAuthIndicators();
      const storedApiKey = getApiKey('openai');

      res.json({
        success: true,
        mode,
        status: {
          // Current mode
          isAuthTokenMode: mode === 'auth_token',
          isApiKeyMode: mode === 'api_key',

          // API key availability/configuration
          hasOAuthToken: authIndicators.hasOAuthToken,
          hasApiKey: !!storedApiKey || status.hasEnvApiKey,
          apiKeyAllowed: status.apiKeyAllowed,
          envApiKeyCleared: status.envApiKeyCleared,
          hasEnvApiKey: status.hasEnvApiKey,
        },
      });
    } catch (error) {
      logger.error('Failed to get OpenAI auth mode:', error);
      res.status(500).json({
        success: false,
        error: error instanceof Error ? error.message : 'Failed to get OpenAI auth mode',
      });
    }
  };
}

/**
 * POST /api/setup/openai-auth-mode
 *
 * Set the OpenAI authentication mode and persist to settings.
 *
 * Body: { mode: 'auth_token' | 'api_key' }
 *
 * - 'auth_token': Use Codex CLI OAuth (~/.codex/auth.json). API keys are stored but inactive.
 * - 'api_key': Use OPENAI_API_KEY for pay-per-use access.
 *
 * When switching to 'auth_token' mode, any environment OPENAI_API_KEY is cleared
 * to prevent accidental API key usage when the user intends to use subscription billing.
 *
 * Response:
 * {
 *   success: true,
 *   mode: 'auth_token' | 'api_key',
 *   status: {
 *     isAuthTokenMode: boolean,
 *     isApiKeyMode: boolean,
 *     apiKeyAllowed: boolean,
 *     envApiKeyCleared: boolean
 *   }
 * }
 */
export function createSetOpenaiAuthModeHandler() {
  return async (req: Request, res: Response): Promise<void> => {
    try {
      const { mode } = req.body as { mode?: string };

      // Validate mode
      if (mode !== 'auth_token' && mode !== 'api_key') {
        res.status(400).json({
          success: false,
          error: "Invalid mode. Must be 'auth_token' or 'api_key'",
        });
        return;
      }

      const newMode: OpenaiAuthMode = mode;

      // Update runtime mode (clears OPENAI_API_KEY if switching to auth_token)
      setProviderAuthModeRuntime('openai', newMode);

      // Persist to settings
      const dataDir = getDataDirectory();
      if (dataDir) {
        const settingsService = new SettingsService(dataDir);
        const settings = await settingsService.getGlobalSettings();

        // Update the OpenAI auth mode field
        settings.openaiAuthMode = newMode;

        await settingsService.updateGlobalSettings(settings);
        logger.info(`OpenAI auth mode changed to: ${newMode}`);
      }

      // Get updated status
      const status = await getProviderAuthStatus('openai');

      res.json({
        success: true,
        mode: newMode,
        status: {
          isAuthTokenMode: newMode === 'auth_token',
          isApiKeyMode: newMode === 'api_key',
          apiKeyAllowed: status.apiKeyAllowed,
          envApiKeyCleared: status.envApiKeyCleared,
        },
      });
    } catch (error) {
      logger.error('Failed to set OpenAI auth mode:', error);
      res.status(500).json({
        success: false,
        error: error instanceof Error ? error.message : 'Failed to set OpenAI auth mode',
      });
    }
  };
}
