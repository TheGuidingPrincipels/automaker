/**
 * Shared utility for checking Codex CLI authentication status
 *
 * Uses 'codex login status' command to verify authentication.
 * Never assumes authenticated - only returns true if CLI confirms.
 *
 * Authentication mode is determined by the OpenAI-specific auth mode
 * (via provider-auth-config). In 'auth_token' mode, API keys are ignored
 * and only CLI OAuth is checked. In 'api_key' mode, both CLI auth and
 * API keys are considered valid authentication methods.
 */

import { spawnProcess } from '@automaker/platform';
import { findCodexCliPath } from '@automaker/platform';
import { createLogger } from '@automaker/utils';
import { isOpenaiApiKeyDisabledSync } from './provider-auth-config.js';

const logger = createLogger('CodexAuth');

const CODEX_COMMAND = 'codex';
const OPENAI_API_KEY_ENV = 'OPENAI_API_KEY';

export interface CodexAuthCheckResult {
  authenticated: boolean;
  method: 'api_key_env' | 'cli_authenticated' | 'none';
}

/**
 * Check Codex authentication status using 'codex login status' command
 *
 * @param cliPath Optional CLI path. If not provided, will attempt to find it.
 * @returns Authentication status and method
 */
export async function checkCodexAuthentication(
  cliPath?: string | null
): Promise<CodexAuthCheckResult> {
  const resolvedCliPath = cliPath || (await findCodexCliPath());
  // In auth_token (OAuth) mode, ignore API key in environment
  const apiKeyDisabled = isOpenaiApiKeyDisabledSync();
  const hasApiKey = apiKeyDisabled ? false : !!process.env[OPENAI_API_KEY_ENV];

  // If CLI is not installed, cannot be authenticated
  if (!resolvedCliPath) {
    logger.info('CLI not found');
    return { authenticated: false, method: 'none' };
  }

  try {
    const result = await spawnProcess({
      command: resolvedCliPath || CODEX_COMMAND,
      args: ['login', 'status'],
      cwd: process.cwd(),
      env: {
        ...process.env,
        TERM: 'dumb', // Avoid interactive output
      },
    });

    // Check both stdout and stderr for "logged in" - Codex CLI outputs to stderr
    const combinedOutput = (result.stdout + result.stderr).toLowerCase();
    const isLoggedIn = combinedOutput.includes('logged in');

    if (result.exitCode === 0 && isLoggedIn) {
      // Determine auth method based on what we know
      const method = hasApiKey ? 'api_key_env' : 'cli_authenticated';
      logger.info(`✓ Authenticated (${method})`);
      return { authenticated: true, method };
    }

    logger.info('Not authenticated');
    return { authenticated: false, method: 'none' };
  } catch (error) {
    logger.error('Failed to check authentication:', error);
    return { authenticated: false, method: 'none' };
  }
}
