/**
 * Auth Mode Routes - GET/POST endpoints for authentication mode management
 *
 * Provides endpoints for:
 * - GET /api/setup/auth-mode - Get current auth mode and status
 * - POST /api/setup/auth-mode - Set auth mode (persists to settings)
 */

import type { Request, Response } from 'express';
import { getDataDirectory } from '@automaker/platform';
import { createLogger } from '@automaker/utils';
import type { AnthropicAuthMode } from '@automaker/types';
import { getAuthMode, getAuthStatus, setAuthModeRuntime } from '../../../lib/auth-config.js';
import { SettingsService } from '../../../services/settings-service.js';

const logger = createLogger('AuthModeRoute');

/**
 * GET /api/setup/auth-mode
 *
 * Returns the current authentication mode and detailed status.
 */
export function createGetAuthModeHandler() {
  return async (_req: Request, res: Response): Promise<void> => {
    try {
      const mode = await getAuthMode();
      const status = await getAuthStatus();

      res.json({
        success: true,
        mode,
        status: {
          // Current mode
          isAuthTokenMode: mode === 'auth_token',
          isApiKeyMode: mode === 'api_key',

          // Auth token availability
          hasOAuthToken:
            status.hasStoredOAuthToken || status.hasEnvAuthToken || status.hasCliOAuthToken,
          hasStoredOAuthToken: status.hasStoredOAuthToken,
          hasEnvAuthToken: status.hasEnvAuthToken,
          hasCliOAuthToken: status.hasCliOAuthToken,

          // API key availability
          hasApiKey: status.hasStoredApiKey || status.hasEnvApiKey,
          hasStoredApiKey: status.hasStoredApiKey,
          hasEnvApiKey: status.hasEnvApiKey,

          // Defense status
          envApiKeyCleared: status.envApiKeyCleared,
        },
      });
    } catch (error) {
      logger.error('Failed to get auth mode:', error);
      res.status(500).json({
        success: false,
        error: error instanceof Error ? error.message : 'Failed to get auth mode',
      });
    }
  };
}

/**
 * POST /api/setup/auth-mode
 *
 * Set the authentication mode and persist to settings.
 *
 * Body: { mode: 'auth_token' | 'api_key' }
 */
export function createSetAuthModeHandler() {
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

      const newMode: AnthropicAuthMode = mode;

      // Update runtime mode (clears API key if switching to auth_token)
      setAuthModeRuntime(newMode);

      // Persist to settings
      const dataDir = getDataDirectory();
      if (dataDir) {
        const settingsService = new SettingsService(dataDir);
        const settings = await settingsService.getGlobalSettings();

        // Update both fields for compatibility
        settings.anthropicAuthMode = newMode;
        settings.disableApiKeyAuth = newMode === 'auth_token';

        await settingsService.updateGlobalSettings(settings);
        logger.info(`Auth mode changed to: ${newMode}`);
      }

      // Get updated status
      const status = await getAuthStatus();

      res.json({
        success: true,
        mode: newMode,
        status: {
          isAuthTokenMode: newMode === 'auth_token',
          isApiKeyMode: newMode === 'api_key',
          hasOAuthToken:
            status.hasStoredOAuthToken || status.hasEnvAuthToken || status.hasCliOAuthToken,
          hasApiKey: status.hasStoredApiKey || status.hasEnvApiKey,
          envApiKeyCleared: status.envApiKeyCleared,
        },
      });
    } catch (error) {
      logger.error('Failed to set auth mode:', error);
      res.status(500).json({
        success: false,
        error: error instanceof Error ? error.message : 'Failed to set auth mode',
      });
    }
  };
}
