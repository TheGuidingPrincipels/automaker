import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Mock dependencies before importing the module
vi.mock('@automaker/utils', async () => {
  const actual = await vi.importActual('@automaker/utils');
  const mockLogger = {
    info: vi.fn(),
    error: vi.fn(),
    warn: vi.fn(),
    debug: vi.fn(),
  };
  return {
    ...actual,
    createLogger: () => mockLogger,
  };
});

vi.mock('@automaker/platform', () => ({
  getDataDirectory: vi.fn(() => '/mock/data/dir'),
}));

vi.mock('../../../src/services/settings-service.js', () => ({
  SettingsService: vi.fn().mockImplementation(() => ({
    getGlobalSettings: vi.fn().mockResolvedValue({}),
  })),
}));

describe('provider-auth-config.ts', () => {
  let originalEnv: NodeJS.ProcessEnv;

  beforeEach(() => {
    originalEnv = { ...process.env };
    vi.resetModules();
    // Clear relevant env vars
    delete process.env.AUTOMAKER_ANTHROPIC_AUTH_MODE;
    delete process.env.AUTOMAKER_OPENAI_AUTH_MODE;
    delete process.env.AUTOMAKER_DISABLE_API_KEY_AUTH;
    delete process.env.ANTHROPIC_API_KEY;
    delete process.env.OPENAI_API_KEY;
  });

  afterEach(() => {
    process.env = originalEnv;
  });

  describe('getSupportedProviders', () => {
    it('should return array of supported providers', async () => {
      const { getSupportedProviders } = await import('@/lib/provider-auth-config.js');
      const providers = getSupportedProviders();

      expect(providers).toContain('anthropic');
      expect(providers).toContain('openai');
      expect(providers).toHaveLength(2);
    });
  });

  describe('isValidProvider', () => {
    it('should return true for anthropic', async () => {
      const { isValidProvider } = await import('@/lib/provider-auth-config.js');
      expect(isValidProvider('anthropic')).toBe(true);
    });

    it('should return true for openai', async () => {
      const { isValidProvider } = await import('@/lib/provider-auth-config.js');
      expect(isValidProvider('openai')).toBe(true);
    });

    it('should return false for unknown provider', async () => {
      const { isValidProvider } = await import('@/lib/provider-auth-config.js');
      expect(isValidProvider('unknown')).toBe(false);
      expect(isValidProvider('google')).toBe(false);
      expect(isValidProvider('')).toBe(false);
    });
  });

  describe('getProviderSpec', () => {
    it('should return correct spec for anthropic', async () => {
      const { getProviderSpec } = await import('@/lib/provider-auth-config.js');
      const spec = getProviderSpec('anthropic');

      expect(spec.envAuthModeVar).toBe('AUTOMAKER_ANTHROPIC_AUTH_MODE');
      expect(spec.envApiKeyVar).toBe('ANTHROPIC_API_KEY');
      expect(spec.settingsField).toBe('anthropicAuthMode');
      expect(spec.displayName).toBe('Anthropic');
    });

    it('should return correct spec for openai', async () => {
      const { getProviderSpec } = await import('@/lib/provider-auth-config.js');
      const spec = getProviderSpec('openai');

      expect(spec.envAuthModeVar).toBe('AUTOMAKER_OPENAI_AUTH_MODE');
      expect(spec.envApiKeyVar).toBe('OPENAI_API_KEY');
      expect(spec.settingsField).toBe('openaiAuthMode');
      expect(spec.displayName).toBe('OpenAI');
    });
  });

  describe('initializeProviderAuthModes', () => {
    it('should default to auth_token mode for all providers', async () => {
      const { initializeProviderAuthModes } = await import('@/lib/provider-auth-config.js');
      const modes = initializeProviderAuthModes();

      expect(modes.anthropic).toBe('auth_token');
      expect(modes.openai).toBe('auth_token');
    });

    it('should respect AUTOMAKER_ANTHROPIC_AUTH_MODE=api_key env var', async () => {
      process.env.AUTOMAKER_ANTHROPIC_AUTH_MODE = 'api_key';

      const { initializeProviderAuthModes } = await import('@/lib/provider-auth-config.js');
      const modes = initializeProviderAuthModes();

      expect(modes.anthropic).toBe('api_key');
      expect(modes.openai).toBe('auth_token');
    });

    it('should respect AUTOMAKER_OPENAI_AUTH_MODE=api_key env var', async () => {
      process.env.AUTOMAKER_OPENAI_AUTH_MODE = 'api_key';

      const { initializeProviderAuthModes } = await import('@/lib/provider-auth-config.js');
      const modes = initializeProviderAuthModes();

      expect(modes.anthropic).toBe('auth_token');
      expect(modes.openai).toBe('api_key');
    });

    it('should map legacy AUTOMAKER_DISABLE_API_KEY_AUTH=false to api_key mode', async () => {
      process.env.AUTOMAKER_DISABLE_API_KEY_AUTH = 'false';

      const { initializeProviderAuthModes } = await import('@/lib/provider-auth-config.js');
      const modes = initializeProviderAuthModes();

      expect(modes.anthropic).toBe('api_key');
      expect(modes.openai).toBe('api_key');
    });

    it('should map legacy AUTOMAKER_DISABLE_API_KEY_AUTH=true to auth_token mode', async () => {
      process.env.AUTOMAKER_DISABLE_API_KEY_AUTH = 'true';

      const { initializeProviderAuthModes } = await import('@/lib/provider-auth-config.js');
      const modes = initializeProviderAuthModes();

      expect(modes.anthropic).toBe('auth_token');
      expect(modes.openai).toBe('auth_token');
    });

    it('should clear ANTHROPIC_API_KEY in auth_token mode', async () => {
      process.env.ANTHROPIC_API_KEY = 'test-key-12345';

      const { initializeProviderAuthModes } = await import('@/lib/provider-auth-config.js');
      initializeProviderAuthModes();

      expect(process.env.ANTHROPIC_API_KEY).toBe('');
    });

    it('should clear OPENAI_API_KEY in auth_token mode', async () => {
      process.env.OPENAI_API_KEY = 'sk-test-key-12345';

      const { initializeProviderAuthModes } = await import('@/lib/provider-auth-config.js');
      initializeProviderAuthModes();

      expect(process.env.OPENAI_API_KEY).toBe('');
    });

    it('should NOT clear API key in api_key mode', async () => {
      process.env.AUTOMAKER_ANTHROPIC_AUTH_MODE = 'api_key';
      process.env.ANTHROPIC_API_KEY = 'test-key-12345';

      const { initializeProviderAuthModes } = await import('@/lib/provider-auth-config.js');
      initializeProviderAuthModes();

      expect(process.env.ANTHROPIC_API_KEY).toBe('test-key-12345');
    });

    it('should handle case-insensitive env var values', async () => {
      process.env.AUTOMAKER_ANTHROPIC_AUTH_MODE = 'API_KEY';

      const { initializeProviderAuthModes } = await import('@/lib/provider-auth-config.js');
      const modes = initializeProviderAuthModes();

      expect(modes.anthropic).toBe('api_key');
    });
  });

  describe('initializeProviderAuthMode', () => {
    it('should initialize single provider to auth_token by default', async () => {
      const { initializeProviderAuthMode } = await import('@/lib/provider-auth-config.js');
      const mode = initializeProviderAuthMode('anthropic');

      expect(mode).toBe('auth_token');
    });

    it('should respect env var for single provider', async () => {
      process.env.AUTOMAKER_OPENAI_AUTH_MODE = 'api_key';

      const { initializeProviderAuthMode } = await import('@/lib/provider-auth-config.js');
      const mode = initializeProviderAuthMode('openai');

      expect(mode).toBe('api_key');
    });

    it('should clear API key in auth_token mode for single provider', async () => {
      process.env.OPENAI_API_KEY = 'sk-test-key';

      const { initializeProviderAuthMode } = await import('@/lib/provider-auth-config.js');
      initializeProviderAuthMode('openai');

      expect(process.env.OPENAI_API_KEY).toBe('');
    });
  });

  describe('getProviderAuthModeSync', () => {
    it('should return auth_token by default before initialization', async () => {
      const { getProviderAuthModeSync } = await import('@/lib/provider-auth-config.js');
      const mode = getProviderAuthModeSync('anthropic');

      expect(mode).toBe('auth_token');
    });

    it('should return cached value after initialization', async () => {
      process.env.AUTOMAKER_ANTHROPIC_AUTH_MODE = 'api_key';

      const { initializeProviderAuthModes, getProviderAuthModeSync } =
        await import('@/lib/provider-auth-config.js');
      initializeProviderAuthModes();

      // Clear env var to ensure we're using cached value
      delete process.env.AUTOMAKER_ANTHROPIC_AUTH_MODE;

      const mode = getProviderAuthModeSync('anthropic');
      expect(mode).toBe('api_key');
    });

    it('should work for both providers', async () => {
      process.env.AUTOMAKER_ANTHROPIC_AUTH_MODE = 'api_key';
      process.env.AUTOMAKER_OPENAI_AUTH_MODE = 'auth_token';

      const { initializeProviderAuthModes, getProviderAuthModeSync } =
        await import('@/lib/provider-auth-config.js');
      initializeProviderAuthModes();

      expect(getProviderAuthModeSync('anthropic')).toBe('api_key');
      expect(getProviderAuthModeSync('openai')).toBe('auth_token');
    });
  });

  describe('isApiKeyAllowedSync', () => {
    it('should return false when in auth_token mode', async () => {
      const { initializeProviderAuthModes, isApiKeyAllowedSync } =
        await import('@/lib/provider-auth-config.js');
      initializeProviderAuthModes();

      expect(isApiKeyAllowedSync('anthropic')).toBe(false);
      expect(isApiKeyAllowedSync('openai')).toBe(false);
    });

    it('should return true when in api_key mode', async () => {
      process.env.AUTOMAKER_ANTHROPIC_AUTH_MODE = 'api_key';

      const { initializeProviderAuthModes, isApiKeyAllowedSync } =
        await import('@/lib/provider-auth-config.js');
      initializeProviderAuthModes();

      expect(isApiKeyAllowedSync('anthropic')).toBe(true);
      expect(isApiKeyAllowedSync('openai')).toBe(false);
    });
  });

  describe('isApiKeyDisabledSync', () => {
    it('should return true when in auth_token mode', async () => {
      const { initializeProviderAuthModes, isApiKeyDisabledSync } =
        await import('@/lib/provider-auth-config.js');
      initializeProviderAuthModes();

      expect(isApiKeyDisabledSync('anthropic')).toBe(true);
      expect(isApiKeyDisabledSync('openai')).toBe(true);
    });

    it('should return false when in api_key mode', async () => {
      process.env.AUTOMAKER_OPENAI_AUTH_MODE = 'api_key';

      const { initializeProviderAuthModes, isApiKeyDisabledSync } =
        await import('@/lib/provider-auth-config.js');
      initializeProviderAuthModes();

      expect(isApiKeyDisabledSync('anthropic')).toBe(true);
      expect(isApiKeyDisabledSync('openai')).toBe(false);
    });
  });

  describe('getProviderAuthMode (async)', () => {
    it('should return auth_token by default', async () => {
      const { getProviderAuthMode } = await import('@/lib/provider-auth-config.js');
      const mode = await getProviderAuthMode('anthropic');

      expect(mode).toBe('auth_token');
    });

    it('should prioritize env var over settings', async () => {
      process.env.AUTOMAKER_ANTHROPIC_AUTH_MODE = 'api_key';

      // Mock settings to return auth_token
      const mockSettingsService = {
        getGlobalSettings: vi.fn().mockResolvedValue({ anthropicAuthMode: 'auth_token' }),
      };
      vi.mocked(await import('@/services/settings-service.js')).SettingsService = vi
        .fn()
        .mockImplementation(() => mockSettingsService) as any;

      const { getProviderAuthMode } = await import('@/lib/provider-auth-config.js');
      const mode = await getProviderAuthMode('anthropic');

      // Env var should take precedence
      expect(mode).toBe('api_key');
    });

    it('should return auth_token when env var not set and settings unavailable', async () => {
      // Without env var, the async function should return auth_token as the default
      // since our mock settings service returns empty settings
      const { getProviderAuthMode } = await import('@/lib/provider-auth-config.js');
      const mode = await getProviderAuthMode('anthropic');

      // With our mock returning empty settings {}, it defaults to auth_token
      expect(mode).toBe('auth_token');
    });

    it('should use env var value when set (env takes precedence)', async () => {
      // This demonstrates that env vars take precedence over settings
      process.env.AUTOMAKER_OPENAI_AUTH_MODE = 'api_key';

      const { getProviderAuthMode } = await import('@/lib/provider-auth-config.js');
      const mode = await getProviderAuthMode('openai');

      expect(mode).toBe('api_key');
    });
  });

  describe('isApiKeyAllowed (async)', () => {
    it('should return false when in auth_token mode', async () => {
      const { isApiKeyAllowed } = await import('@/lib/provider-auth-config.js');
      const allowed = await isApiKeyAllowed('anthropic');

      expect(allowed).toBe(false);
    });

    it('should return true when in api_key mode', async () => {
      process.env.AUTOMAKER_ANTHROPIC_AUTH_MODE = 'api_key';

      const { isApiKeyAllowed } = await import('@/lib/provider-auth-config.js');
      const allowed = await isApiKeyAllowed('anthropic');

      expect(allowed).toBe(true);
    });
  });

  describe('isApiKeyDisabled (async)', () => {
    it('should return true when in auth_token mode', async () => {
      const { isApiKeyDisabled } = await import('@/lib/provider-auth-config.js');
      const disabled = await isApiKeyDisabled('anthropic');

      expect(disabled).toBe(true);
    });

    it('should return false when in api_key mode', async () => {
      process.env.AUTOMAKER_OPENAI_AUTH_MODE = 'api_key';

      const { isApiKeyDisabled } = await import('@/lib/provider-auth-config.js');
      const disabled = await isApiKeyDisabled('openai');

      expect(disabled).toBe(false);
    });
  });

  describe('setProviderAuthModeRuntime', () => {
    it('should update cached mode for provider', async () => {
      const { initializeProviderAuthModes, setProviderAuthModeRuntime, getProviderAuthModeSync } =
        await import('@/lib/provider-auth-config.js');

      initializeProviderAuthModes();
      expect(getProviderAuthModeSync('anthropic')).toBe('auth_token');

      setProviderAuthModeRuntime('anthropic', 'api_key');
      expect(getProviderAuthModeSync('anthropic')).toBe('api_key');
    });

    it('should clear API key when switching to auth_token mode', async () => {
      process.env.AUTOMAKER_ANTHROPIC_AUTH_MODE = 'api_key';
      process.env.ANTHROPIC_API_KEY = 'test-key';

      const { initializeProviderAuthModes, setProviderAuthModeRuntime } =
        await import('@/lib/provider-auth-config.js');

      initializeProviderAuthModes();
      expect(process.env.ANTHROPIC_API_KEY).toBe('test-key');

      setProviderAuthModeRuntime('anthropic', 'auth_token');
      expect(process.env.ANTHROPIC_API_KEY).toBe('');
    });

    it('should not clear API key when switching to api_key mode', async () => {
      process.env.ANTHROPIC_API_KEY = 'test-key';

      const { initializeProviderAuthModes, setProviderAuthModeRuntime } =
        await import('@/lib/provider-auth-config.js');

      initializeProviderAuthModes();
      // Key was cleared during init because default is auth_token
      process.env.ANTHROPIC_API_KEY = 'new-test-key';

      setProviderAuthModeRuntime('anthropic', 'api_key');
      expect(process.env.ANTHROPIC_API_KEY).toBe('new-test-key');
    });
  });

  describe('getProviderAuthStatus', () => {
    it('should return correct status in auth_token mode', async () => {
      const { initializeProviderAuthModes, getProviderAuthStatus } =
        await import('@/lib/provider-auth-config.js');

      initializeProviderAuthModes();
      const status = await getProviderAuthStatus('anthropic');

      expect(status.mode).toBe('auth_token');
      expect(status.apiKeyAllowed).toBe(false);
      expect(status.envApiKeyCleared).toBe(true);
      expect(status.hasEnvApiKey).toBe(false);
    });

    it('should return correct status in api_key mode with key present', async () => {
      process.env.AUTOMAKER_ANTHROPIC_AUTH_MODE = 'api_key';
      process.env.ANTHROPIC_API_KEY = 'test-key';

      const { initializeProviderAuthModes, getProviderAuthStatus } =
        await import('@/lib/provider-auth-config.js');

      initializeProviderAuthModes();
      const status = await getProviderAuthStatus('anthropic');

      expect(status.mode).toBe('api_key');
      expect(status.apiKeyAllowed).toBe(true);
      expect(status.envApiKeyCleared).toBe(false);
      expect(status.hasEnvApiKey).toBe(true);
    });

    it('should return correct status in api_key mode without key', async () => {
      process.env.AUTOMAKER_ANTHROPIC_AUTH_MODE = 'api_key';
      // No API key set

      const { initializeProviderAuthModes, getProviderAuthStatus } =
        await import('@/lib/provider-auth-config.js');

      initializeProviderAuthModes();
      const status = await getProviderAuthStatus('anthropic');

      expect(status.mode).toBe('api_key');
      expect(status.apiKeyAllowed).toBe(true);
      expect(status.envApiKeyCleared).toBe(false);
      expect(status.hasEnvApiKey).toBe(false);
    });
  });

  describe('getAllProviderAuthStatus', () => {
    it('should return status for all providers', async () => {
      process.env.AUTOMAKER_ANTHROPIC_AUTH_MODE = 'api_key';
      process.env.ANTHROPIC_API_KEY = 'anthropic-key';
      // OpenAI defaults to auth_token

      const { initializeProviderAuthModes, getAllProviderAuthStatus } =
        await import('@/lib/provider-auth-config.js');

      initializeProviderAuthModes();
      const statuses = await getAllProviderAuthStatus();

      expect(statuses.anthropic.mode).toBe('api_key');
      expect(statuses.anthropic.apiKeyAllowed).toBe(true);
      expect(statuses.anthropic.hasEnvApiKey).toBe(true);

      expect(statuses.openai.mode).toBe('auth_token');
      expect(statuses.openai.apiKeyAllowed).toBe(false);
      expect(statuses.openai.envApiKeyCleared).toBe(true);
    });
  });

  describe('Backward Compatibility - Anthropic Aliases', () => {
    it('getAnthropicAuthModeSync should work like getProviderAuthModeSync("anthropic")', async () => {
      process.env.AUTOMAKER_ANTHROPIC_AUTH_MODE = 'api_key';

      const { initializeProviderAuthModes, getAnthropicAuthModeSync, getProviderAuthModeSync } =
        await import('@/lib/provider-auth-config.js');

      initializeProviderAuthModes();

      expect(getAnthropicAuthModeSync()).toBe(getProviderAuthModeSync('anthropic'));
      expect(getAnthropicAuthModeSync()).toBe('api_key');
    });

    it('getAnthropicAuthMode should work like getProviderAuthMode("anthropic")', async () => {
      const { getAnthropicAuthMode, getProviderAuthMode } =
        await import('@/lib/provider-auth-config.js');

      const [aliasResult, directResult] = await Promise.all([
        getAnthropicAuthMode(),
        getProviderAuthMode('anthropic'),
      ]);

      expect(aliasResult).toBe(directResult);
    });

    it('isAnthropicApiKeyDisabledSync should work like isApiKeyDisabledSync("anthropic")', async () => {
      const { initializeProviderAuthModes, isAnthropicApiKeyDisabledSync, isApiKeyDisabledSync } =
        await import('@/lib/provider-auth-config.js');

      initializeProviderAuthModes();

      expect(isAnthropicApiKeyDisabledSync()).toBe(isApiKeyDisabledSync('anthropic'));
      expect(isAnthropicApiKeyDisabledSync()).toBe(true);
    });
  });

  describe('OpenAI Convenience Functions', () => {
    it('getOpenaiAuthModeSync should return correct mode', async () => {
      process.env.AUTOMAKER_OPENAI_AUTH_MODE = 'api_key';

      const { initializeProviderAuthModes, getOpenaiAuthModeSync } =
        await import('@/lib/provider-auth-config.js');

      initializeProviderAuthModes();
      expect(getOpenaiAuthModeSync()).toBe('api_key');
    });

    it('getOpenaiAuthMode should return correct mode asynchronously', async () => {
      process.env.AUTOMAKER_OPENAI_AUTH_MODE = 'api_key';

      const { getOpenaiAuthMode } = await import('@/lib/provider-auth-config.js');

      const mode = await getOpenaiAuthMode();
      expect(mode).toBe('api_key');
    });

    it('isOpenaiApiKeyDisabledSync should return true in auth_token mode', async () => {
      const { initializeProviderAuthModes, isOpenaiApiKeyDisabledSync } =
        await import('@/lib/provider-auth-config.js');

      initializeProviderAuthModes();
      expect(isOpenaiApiKeyDisabledSync()).toBe(true);
    });

    it('isOpenaiApiKeyAllowedSync should return true in api_key mode', async () => {
      process.env.AUTOMAKER_OPENAI_AUTH_MODE = 'api_key';

      const { initializeProviderAuthModes, isOpenaiApiKeyAllowedSync } =
        await import('@/lib/provider-auth-config.js');

      initializeProviderAuthModes();
      expect(isOpenaiApiKeyAllowedSync()).toBe(true);
    });
  });

  describe('logAllProviderAuthModes', () => {
    it('should log auth modes for all providers', async () => {
      const { createLogger } = await import('@automaker/utils');
      const mockLogger = (createLogger as ReturnType<typeof vi.fn>)();

      const { initializeProviderAuthModes, logAllProviderAuthModes } =
        await import('@/lib/provider-auth-config.js');

      initializeProviderAuthModes();
      await logAllProviderAuthModes();

      // Verify logger was called for each provider (anthropic and openai)
      expect(mockLogger.info).toHaveBeenCalled();
    });
  });

  describe('Edge Cases', () => {
    it('should handle invalid env var values by defaulting to auth_token', async () => {
      process.env.AUTOMAKER_ANTHROPIC_AUTH_MODE = 'invalid_mode';

      const { initializeProviderAuthModes, getProviderAuthModeSync } =
        await import('@/lib/provider-auth-config.js');

      initializeProviderAuthModes();
      expect(getProviderAuthModeSync('anthropic')).toBe('auth_token');
    });

    it('should handle empty env var values by defaulting to auth_token', async () => {
      process.env.AUTOMAKER_ANTHROPIC_AUTH_MODE = '';

      const { initializeProviderAuthModes, getProviderAuthModeSync } =
        await import('@/lib/provider-auth-config.js');

      initializeProviderAuthModes();
      expect(getProviderAuthModeSync('anthropic')).toBe('auth_token');
    });

    it('should handle whitespace in env var values', async () => {
      process.env.AUTOMAKER_ANTHROPIC_AUTH_MODE = '  api_key  ';

      const { initializeProviderAuthModes, getProviderAuthModeSync } =
        await import('@/lib/provider-auth-config.js');

      initializeProviderAuthModes();
      // With trim() added, whitespace should be handled correctly
      expect(getProviderAuthModeSync('anthropic')).toBe('api_key');
    });

    it('should handle multiple consecutive initializations', async () => {
      const { initializeProviderAuthModes, getProviderAuthModeSync } =
        await import('@/lib/provider-auth-config.js');

      // First init with default
      initializeProviderAuthModes();
      expect(getProviderAuthModeSync('anthropic')).toBe('auth_token');

      // Change env and reinit
      process.env.AUTOMAKER_ANTHROPIC_AUTH_MODE = 'api_key';
      initializeProviderAuthModes();
      expect(getProviderAuthModeSync('anthropic')).toBe('api_key');
    });
  });
});
