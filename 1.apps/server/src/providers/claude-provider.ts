/**
 * Claude Provider - Executes queries using Claude Agent SDK
 *
 * Wraps the @anthropic-ai/claude-agent-sdk for seamless integration
 * with the provider architecture.
 */

import { query, type Options } from '@anthropic-ai/claude-agent-sdk';
import { BaseProvider } from './base-provider.js';
import { classifyError, getUserFriendlyErrorMessage, createLogger } from '@automaker/utils';
import { getAuthModeSync } from '../lib/auth-config.js';
import { getApiKey } from '../routes/setup/common.js';

const logger = createLogger('ClaudeProvider');
import {
  getThinkingTokenBudget,
  validateBareModelId,
  type ClaudeApiProfile,
  type ClaudeCompatibleProvider,
  type Credentials,
} from '@automaker/types';

/**
 * ProviderConfig - Union type for provider configuration
 *
 * Accepts either the legacy ClaudeApiProfile or new ClaudeCompatibleProvider.
 * Both share the same connection settings structure.
 */
type ProviderConfig = ClaudeApiProfile | ClaudeCompatibleProvider;
import type {
  ExecuteOptions,
  ProviderMessage,
  InstallationStatus,
  ModelDefinition,
} from './types.js';

// Explicit allowlist of environment variables to pass to the SDK.
// Only these vars are passed - nothing else from process.env leaks through.
const ALLOWED_ENV_VARS = [
  // Authentication
  'ANTHROPIC_API_KEY',
  'ANTHROPIC_AUTH_TOKEN',
  'CLAUDE_CODE_OAUTH_TOKEN', // Legacy CLI OAuth token (mapped to ANTHROPIC_AUTH_TOKEN)
  // Endpoint configuration
  'ANTHROPIC_BASE_URL',
  'API_TIMEOUT_MS',
  // Model mappings
  'ANTHROPIC_DEFAULT_HAIKU_MODEL',
  'ANTHROPIC_DEFAULT_SONNET_MODEL',
  'ANTHROPIC_DEFAULT_OPUS_MODEL',
  // Traffic control
  'CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC',
  // TTS hook control (fork-specific)
  'AUTOMAKER_DISABLE_HOOK_TTS',
  // System vars (always from process.env)
  'PATH',
  'HOME',
  'SHELL',
  'TERM',
  'USER',
  'LANG',
  'LC_ALL',
];

// System vars are always passed from process.env regardless of profile
const SYSTEM_ENV_VARS = ['PATH', 'HOME', 'SHELL', 'TERM', 'USER', 'LANG', 'LC_ALL'];

/**
 * Check if the config is a ClaudeCompatibleProvider (new system)
 * by checking for the 'models' array property
 */
function isClaudeCompatibleProvider(config: ProviderConfig): config is ClaudeCompatibleProvider {
  return 'models' in config && Array.isArray(config.models);
}

/**
 * Build environment for the SDK with only explicitly allowed variables.
 * When a provider/profile is provided, uses its configuration (clean switch - don't inherit from process.env).
 * When no provider is provided, uses direct Anthropic API settings from process.env.
 *
 * Supports both:
 * - ClaudeCompatibleProvider (new system with models[] array)
 * - ClaudeApiProfile (legacy system with modelMappings)
 *
 * @param providerConfig - Optional provider configuration for alternative endpoint
 * @param credentials - Optional credentials object for resolving 'credentials' apiKeySource
 */
function buildEnv(
  providerConfig?: ProviderConfig,
  credentials?: Credentials
): Record<string, string | undefined> {
  const env: Record<string, string | undefined> = {};

  // Get auth mode (auth_token = subscription/OAuth, api_key = pay-per-use)
  const authMode = getAuthModeSync();
  const isAuthTokenMode = authMode === 'auth_token';

  logger.debug('[buildEnv] Auth mode:', { authMode, isAuthTokenMode });

  if (providerConfig) {
    // Use provider configuration (clean switch - don't inherit non-system vars from process.env)
    logger.debug('[buildEnv] Using provider configuration:', {
      name: providerConfig.name,
      baseUrl: providerConfig.baseUrl,
      apiKeySource: providerConfig.apiKeySource ?? 'inline',
      isNewProvider: isClaudeCompatibleProvider(providerConfig),
      authMode,
    });

    // DEFENSE LAYER 2: In auth_token mode, explicitly clear API key
    if (isAuthTokenMode) {
      env['ANTHROPIC_API_KEY'] = '';
    } else {
      // Resolve API key based on source strategy (only in api_key mode)
      let apiKey: string | undefined;
      const source = providerConfig.apiKeySource ?? 'inline'; // Default to inline for backwards compat

      switch (source) {
        case 'inline':
          apiKey = providerConfig.apiKey;
          break;
        case 'env':
          apiKey = process.env.ANTHROPIC_API_KEY;
          break;
        case 'credentials':
          apiKey = credentials?.apiKeys?.anthropic;
          break;
      }

      // Warn if no API key found in api_key mode
      if (!apiKey) {
        logger.warn(
          `No API key found for provider "${providerConfig.name}" with source "${source}"`
        );
      }

      // Set authentication based on provider config
      if (providerConfig.useAuthToken) {
        env['ANTHROPIC_AUTH_TOKEN'] = apiKey;
      } else {
        env['ANTHROPIC_API_KEY'] = apiKey;
      }
    }

    // Endpoint configuration
    env['ANTHROPIC_BASE_URL'] = providerConfig.baseUrl;
    logger.debug(`[buildEnv] Set ANTHROPIC_BASE_URL to: ${providerConfig.baseUrl}`);

    if (providerConfig.timeoutMs) {
      env['API_TIMEOUT_MS'] = String(providerConfig.timeoutMs);
    }

    // Model mappings - only for legacy ClaudeApiProfile
    // For ClaudeCompatibleProvider, the model is passed directly (no mapping needed)
    if (!isClaudeCompatibleProvider(providerConfig) && providerConfig.modelMappings) {
      if (providerConfig.modelMappings.haiku) {
        env['ANTHROPIC_DEFAULT_HAIKU_MODEL'] = providerConfig.modelMappings.haiku;
      }
      if (providerConfig.modelMappings.sonnet) {
        env['ANTHROPIC_DEFAULT_SONNET_MODEL'] = providerConfig.modelMappings.sonnet;
      }
      if (providerConfig.modelMappings.opus) {
        env['ANTHROPIC_DEFAULT_OPUS_MODEL'] = providerConfig.modelMappings.opus;
      }
    }

    // Traffic control
    if (providerConfig.disableNonessentialTraffic) {
      env['CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC'] = '1';
    }
  } else {
    // Use direct Anthropic API - pass through credentials or environment variables
    //
    // AUTH TOKEN MODE (subscription):
    // - Prioritize OAuth tokens
    // - Throw error if no OAuth token available (don't fall back to API key)
    //
    // API KEY MODE (pay-per-use):
    // - Use stored or env API key
    //
    // AUTHENTICATION METHODS (mode-specific):
    // - auth_token mode: OAuth/CLI tokens only (no API key fallback)
    // - api_key mode: API key only (no OAuth/CLI fallback)

    if (isAuthTokenMode) {
      // AUTH TOKEN MODE - use OAuth tokens only
      const storedAuthToken = getApiKey('anthropic_oauth_token');

      if (storedAuthToken) {
        // User explicitly stored an auth token via UI - use it for direct API auth
        env['ANTHROPIC_AUTH_TOKEN'] = storedAuthToken;
        env['ANTHROPIC_API_KEY'] = ''; // DEFENSE LAYER 2: Clear to prevent SDK from using wrong auth
        logger.debug('[buildEnv] Using stored OAuth token as ANTHROPIC_AUTH_TOKEN');
      } else if (process.env.ANTHROPIC_AUTH_TOKEN) {
        // Direct API auth token from environment
        env['ANTHROPIC_AUTH_TOKEN'] = process.env.ANTHROPIC_AUTH_TOKEN;
        env['ANTHROPIC_API_KEY'] = ''; // DEFENSE LAYER 2: Clear to prevent SDK from using wrong auth
        logger.debug('[buildEnv] Using ANTHROPIC_AUTH_TOKEN from environment');
      } else if (process.env.CLAUDE_CODE_OAUTH_TOKEN) {
        // CLI OAuth token - pass through to SDK environment, CLI will handle OAuth flow
        // DO NOT map to ANTHROPIC_AUTH_TOKEN - that's for direct API auth
        env['CLAUDE_CODE_OAUTH_TOKEN'] = process.env.CLAUDE_CODE_OAUTH_TOKEN;
        env['ANTHROPIC_API_KEY'] = ''; // DEFENSE LAYER 2: Clear to prevent SDK from using pay-per-use key
        logger.debug('[buildEnv] Using CLAUDE_CODE_OAUTH_TOKEN (CLI will handle OAuth)');
      } else {
        // AUTH TOKEN MODE but no auth token found - don't fall back to API key
        // CRITICAL: This prevents accidental API key usage in subscription mode
        env['ANTHROPIC_API_KEY'] = ''; // DEFENSE LAYER 2: Explicitly clear
        logger.warn('[buildEnv] Auth Token mode: No OAuth token found');

        // Don't throw here - let the SDK handle the auth failure gracefully
        // The SDK will provide a better error message about authentication
        // Just make absolutely sure no API key is used
      }
    } else {
      // API KEY MODE - use API key only (ignore OAuth tokens)
      const storedApiKey = credentials?.apiKeys?.anthropic || getApiKey('anthropic');
      if (storedApiKey) {
        env['ANTHROPIC_API_KEY'] = storedApiKey;
        logger.debug('[buildEnv] API Key mode: Using stored API key');
      } else if (process.env.ANTHROPIC_API_KEY && process.env.ANTHROPIC_API_KEY !== '') {
        env['ANTHROPIC_API_KEY'] = process.env.ANTHROPIC_API_KEY;
        logger.debug('[buildEnv] API Key mode: Using API key from environment');
      } else {
        logger.warn('[buildEnv] API Key mode: No API key found');
      }
    }

    // Pass through ANTHROPIC_BASE_URL if set in environment (backward compatibility)
    if (process.env.ANTHROPIC_BASE_URL) {
      env['ANTHROPIC_BASE_URL'] = process.env.ANTHROPIC_BASE_URL;
    }
  }

  // Always add system vars from process.env
  for (const key of SYSTEM_ENV_VARS) {
    if (process.env[key]) {
      env[key] = process.env[key];
    }
  }

  // TTS hook control - disable by default to prevent audio during agent execution
  env.AUTOMAKER_DISABLE_HOOK_TTS = process.env.AUTOMAKER_DISABLE_HOOK_TTS ?? 'true';

  // Final debug logging to show what auth will be used
  logger.debug('[buildEnv] Final auth state:', {
    authMode,
    hasApiKey: !!env['ANTHROPIC_API_KEY'] && env['ANTHROPIC_API_KEY'] !== '',
    hasAuthToken: !!env['ANTHROPIC_AUTH_TOKEN'],
    hasCliOAuth: !!env['CLAUDE_CODE_OAUTH_TOKEN'],
    apiKeyLength: env['ANTHROPIC_API_KEY']?.length ?? 0,
    authTokenLength: env['ANTHROPIC_AUTH_TOKEN']?.length ?? 0,
  });

  return env;
}

export class ClaudeProvider extends BaseProvider {
  getName(): string {
    return 'claude';
  }

  /**
   * Execute a query using Claude Agent SDK
   */
  async *executeQuery(options: ExecuteOptions): AsyncGenerator<ProviderMessage> {
    // Validate that model doesn't have a provider prefix
    // AgentService should strip prefixes before passing to providers
    validateBareModelId(options.model, 'ClaudeProvider');

    const {
      prompt,
      model,
      cwd,
      systemPrompt,
      maxTurns = 20,
      allowedTools,
      abortController,
      conversationHistory,
      sdkSessionId,
      thinkingLevel,
      claudeApiProfile,
      claudeCompatibleProvider,
      credentials,
    } = options;

    // Determine which provider config to use
    // claudeCompatibleProvider takes precedence over claudeApiProfile
    const providerConfig = claudeCompatibleProvider || claudeApiProfile;

    // Convert thinking level to token budget
    const maxThinkingTokens = getThinkingTokenBudget(thinkingLevel);

    // Build Claude SDK options
    const sdkOptions: Options = {
      model,
      systemPrompt,
      maxTurns,
      cwd,
      // Pass only explicitly allowed environment variables to SDK
      // When a provider is active, uses provider settings (clean switch)
      // When no provider, uses direct Anthropic API (from process.env or CLI OAuth)
      env: buildEnv(providerConfig, credentials),
      // Pass through allowedTools if provided by caller (decided by sdk-options.ts)
      ...(allowedTools && { allowedTools }),
      // AUTONOMOUS MODE: Always bypass permissions for fully autonomous operation
      permissionMode: 'bypassPermissions',
      allowDangerouslySkipPermissions: true,
      abortController,
      // Resume existing SDK session if we have a session ID
      ...(sdkSessionId && conversationHistory && conversationHistory.length > 0
        ? { resume: sdkSessionId }
        : {}),
      // Forward settingSources for CLAUDE.md file loading
      ...(options.settingSources && { settingSources: options.settingSources }),
      // Forward MCP servers configuration
      ...(options.mcpServers && { mcpServers: options.mcpServers }),
      // Extended thinking configuration
      ...(maxThinkingTokens && { maxThinkingTokens }),
      // Subagents configuration for specialized task delegation
      ...(options.agents && { agents: options.agents }),
      // Pass through outputFormat for structured JSON outputs
      ...(options.outputFormat && { outputFormat: options.outputFormat }),
    };

    // Build prompt payload
    let promptPayload: string | AsyncIterable<any>;

    if (Array.isArray(prompt)) {
      // Multi-part prompt (with images)
      promptPayload = (async function* () {
        const multiPartPrompt = {
          type: 'user' as const,
          session_id: '',
          message: {
            role: 'user' as const,
            content: prompt,
          },
          parent_tool_use_id: null,
        };
        yield multiPartPrompt;
      })();
    } else {
      // Simple text prompt
      promptPayload = prompt;
    }

    // Log the environment being passed to the SDK for debugging
    const envForSdk = sdkOptions.env as Record<string, string | undefined>;
    logger.debug('[ClaudeProvider] SDK Configuration:', {
      model: sdkOptions.model,
      baseUrl: envForSdk?.['ANTHROPIC_BASE_URL'] || '(default Anthropic API)',
      hasApiKey: !!envForSdk?.['ANTHROPIC_API_KEY'],
      hasAuthToken: !!envForSdk?.['ANTHROPIC_AUTH_TOKEN'],
      providerName: providerConfig?.name || '(direct Anthropic)',
      maxTurns: sdkOptions.maxTurns,
      maxThinkingTokens: sdkOptions.maxThinkingTokens,
    });

    // Execute via Claude Agent SDK
    try {
      const stream = query({ prompt: promptPayload, options: sdkOptions });

      // Stream messages directly - they're already in the correct format
      for await (const msg of stream) {
        yield msg as ProviderMessage;
      }
    } catch (error) {
      // Enhance error with user-friendly message and classification
      const errorInfo = classifyError(error);
      const userMessage = getUserFriendlyErrorMessage(error);

      logger.error('executeQuery() error during execution:', {
        type: errorInfo.type,
        message: errorInfo.message,
        isRateLimit: errorInfo.isRateLimit,
        retryAfter: errorInfo.retryAfter,
        stack: (error as Error).stack,
      });

      // Build enhanced error message with additional guidance for rate limits
      const message = errorInfo.isRateLimit
        ? `${userMessage}\n\nTip: If you're running multiple features in auto-mode, consider reducing concurrency (maxConcurrency setting) to avoid hitting rate limits.`
        : userMessage;

      const enhancedError = new Error(message);
      (enhancedError as any).originalError = error;
      (enhancedError as any).type = errorInfo.type;

      if (errorInfo.isRateLimit) {
        (enhancedError as any).retryAfter = errorInfo.retryAfter;
      }

      throw enhancedError;
    }
  }

  /**
   * Detect Claude SDK installation (always available via npm)
   */
  async detectInstallation(): Promise<InstallationStatus> {
    // Claude SDK is always available since it's a dependency
    const hasApiKey = !!process.env.ANTHROPIC_API_KEY;

    const status: InstallationStatus = {
      installed: true,
      method: 'sdk',
      hasApiKey,
      authenticated: hasApiKey,
    };

    return status;
  }

  /**
   * Get available Claude models
   */
  getAvailableModels(): ModelDefinition[] {
    const models = [
      {
        id: 'claude-opus-4-5-20251101',
        name: 'Claude Opus 4.5',
        modelString: 'claude-opus-4-5-20251101',
        provider: 'anthropic',
        description: 'Most capable Claude model',
        contextWindow: 200000,
        maxOutputTokens: 16000,
        supportsVision: true,
        supportsTools: true,
        tier: 'premium' as const,
        default: true,
      },
      {
        id: 'claude-sonnet-4-20250514',
        name: 'Claude Sonnet 4',
        modelString: 'claude-sonnet-4-20250514',
        provider: 'anthropic',
        description: 'Balanced performance and cost',
        contextWindow: 200000,
        maxOutputTokens: 16000,
        supportsVision: true,
        supportsTools: true,
        tier: 'standard' as const,
      },
      {
        id: 'claude-3-5-sonnet-20241022',
        name: 'Claude 3.5 Sonnet',
        modelString: 'claude-3-5-sonnet-20241022',
        provider: 'anthropic',
        description: 'Fast and capable',
        contextWindow: 200000,
        maxOutputTokens: 8000,
        supportsVision: true,
        supportsTools: true,
        tier: 'standard' as const,
      },
      {
        id: 'claude-haiku-4-5-20251001',
        name: 'Claude Haiku 4.5',
        modelString: 'claude-haiku-4-5-20251001',
        provider: 'anthropic',
        description: 'Fastest Claude model',
        contextWindow: 200000,
        maxOutputTokens: 8000,
        supportsVision: true,
        supportsTools: true,
        tier: 'basic' as const,
      },
    ] satisfies ModelDefinition[];
    return models;
  }

  /**
   * Check if the provider supports a specific feature
   */
  supportsFeature(feature: string): boolean {
    const supportedFeatures = ['tools', 'text', 'vision', 'thinking'];
    return supportedFeatures.includes(feature);
  }
}
