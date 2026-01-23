import { useState, useEffect, useCallback } from 'react';
import { getServerUrlSync } from '@/lib/http-api-client';
import type { AnthropicAuthMode, OpenaiAuthMode } from '@automaker/types';

// ============================================================================
// Generic Provider Auth Mode Hook
// ============================================================================

export type AuthProvider = 'anthropic' | 'openai';
export type AnyAuthMode = AnthropicAuthMode | OpenaiAuthMode;

interface AuthModeStatus {
  isAuthTokenMode: boolean;
  isApiKeyMode: boolean;
  apiKeyAllowed: boolean;
  envApiKeyCleared: boolean;
  hasEnvApiKey: boolean;
  hasOAuthToken?: boolean; // Specific to some providers
  hasApiKey?: boolean; // Specific to some providers
}

interface AuthModeResponse {
  success: boolean;
  mode: AnyAuthMode;
  status: AuthModeStatus;
  error?: string;
}

const PROVIDER_ENDPOINTS: Record<AuthProvider, string> = {
  // Legacy endpoint for Anthropic
  anthropic: '/api/setup/auth-mode',
  // New pattern for other providers
  openai: '/api/setup/openai-auth-mode',
};

/**
 * Generic hook to manage authentication mode for any provider.
 *
 * @param provider The provider to manage ('anthropic', 'openai')
 * @returns Object containing authMode, status, isLoading, error, setAuthMode, and refresh
 */
export function useProviderAuthMode<T extends AnyAuthMode = AnyAuthMode>(provider: AuthProvider) {
  const [authMode, setAuthModeState] = useState<T>('auth_token' as T);
  const [status, setStatus] = useState<AuthModeStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const endpoint = PROVIDER_ENDPOINTS[provider];

  const refresh = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch(`${getServerUrlSync()}${endpoint}`, {
        method: 'GET',
        credentials: 'include',
      });

      if (response.ok) {
        const data: AuthModeResponse = await response.json();
        if (data.success) {
          setAuthModeState(data.mode as T);
          setStatus(data.status);
        }
      }
    } catch (err) {
      console.warn(`Failed to fetch ${provider} auth mode:`, err);
      setError(err instanceof Error ? err : new Error('Unknown error'));
      // Default to auth_token mode on error
      setAuthModeState('auth_token' as T);
    } finally {
      setIsLoading(false);
    }
  }, [provider, endpoint]);

  const setAuthMode = useCallback(
    async (mode: T) => {
      try {
        const response = await fetch(`${getServerUrlSync()}${endpoint}`, {
          method: 'POST',
          credentials: 'include',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ mode }),
        });

        if (response.ok) {
          const data: AuthModeResponse = await response.json();
          if (data.success) {
            setAuthModeState(data.mode as T);
            setStatus(data.status);
            return { success: true };
          }
        }
        return { success: false };
      } catch (error) {
        console.error(`Failed to set ${provider} auth mode:`, error);
        return { success: false };
      }
    },
    [provider, endpoint]
  );

  useEffect(() => {
    refresh();
  }, [refresh]);

  return {
    authMode,
    status,
    isLoading,
    error,
    setAuthMode,
    refresh,
  };
}

// ============================================================================
// Anthropic Auth Mode Hook (Wrapper)
// ============================================================================

/**
 * Hook to get and manage the Anthropic authentication mode
 * @deprecated Use useProviderAuthMode('anthropic') instead
 */
export function useAuthMode() {
  return useProviderAuthMode<AnthropicAuthMode>('anthropic');
}

/**
 * @deprecated Use useAuthMode instead
 */
export function useAuthConfig() {
  const { authMode, status, isLoading, refresh } = useAuthMode();

  return {
    authMode,
    apiKeyAuthDisabled: authMode === 'auth_token',
    hasStoredOAuthToken: status?.hasOAuthToken ?? false,
    hasEnvAuthToken: false, // Legacy field, not actively tracked in status
    hasCliOAuthToken: false, // Legacy field
    hasStoredApiKey: status?.hasApiKey ?? false,
    hasEnvApiKey: status?.hasEnvApiKey ?? false,
    envApiKeyCleared: status?.envApiKeyCleared ?? false,
    isLoading,
    refresh,
  };
}

// ============================================================================
// OpenAI Auth Mode Hook (Wrapper)
// ============================================================================

/**
 * Hook to get and manage the OpenAI/Codex authentication mode
 * @deprecated Use useProviderAuthMode('openai') instead
 */
export function useOpenAIAuthMode() {
  return useProviderAuthMode<OpenaiAuthMode>('openai');
}

// ============================================================================
// Aggregated Auth Modes Hook
// ============================================================================

/**
 * Hook to get auth modes for all known providers at once.
 * Useful for generic UI rendering that needs to check multiple providers.
 *
 * @returns Object containing:
 *   - anthropic: Auth state for Anthropic provider
 *   - openai: Auth state for OpenAI provider
 *   - getMode(key): Get auth mode by provider key string
 *   - isAllAuthTokenMode: True if all providers are in auth_token mode
 *   - isLoading: True if any provider is still loading
 *   - isProviderManaged(key): Check if provider has auth mode support
 *   - shouldShowApiKeyField(key): Check if API key field should be shown
 */
export function useAllAuthModes() {
  /**
   * NOTE: Providers are hardcoded here because React hooks must be called
   * unconditionally. If adding a new provider:
   * 1. Add the hook call here
   * 2. Update the return object
   * 3. Update isProviderManaged() and shouldShowApiKeyField()
   */
  const anthropic = useProviderAuthMode<AnthropicAuthMode>('anthropic');
  const openai = useProviderAuthMode<OpenaiAuthMode>('openai');

  return {
    anthropic,
    openai,
    // Helper to get by key string
    getMode: (key: string) => {
      if (key === 'anthropic') return anthropic.authMode;
      if (key === 'openai') return openai.authMode;
      if (process.env.NODE_ENV === 'development') {
        console.warn(`[useAllAuthModes] Unknown provider key: "${key}", defaulting to auth_token`);
      }
      return 'auth_token'; // Default safe fallback
    },
    // Helper to check if all are in auth_token mode
    isAllAuthTokenMode: anthropic.authMode === 'auth_token' && openai.authMode === 'auth_token',
    isLoading: anthropic.isLoading || openai.isLoading,
    // Helper to check if provider has auth mode support
    isProviderManaged: (key: string): boolean => {
      return key === 'anthropic' || key === 'openai';
    },
    // Helper to determine if API key field should be shown for a provider
    shouldShowApiKeyField: (key: string): boolean => {
      // Only hide for managed providers in auth_token mode
      if (key === 'anthropic') return anthropic.authMode === 'api_key';
      if (key === 'openai') return openai.authMode === 'api_key';
      return true; // Non-managed providers always show API key field
    },
  };
}
