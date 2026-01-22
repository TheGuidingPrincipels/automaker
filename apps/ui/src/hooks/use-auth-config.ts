import { useState, useEffect, useCallback } from 'react';
import { getServerUrlSync } from '@/lib/http-api-client';
import type { AnthropicAuthMode } from '@automaker/types';

interface AuthModeStatus {
  isAuthTokenMode: boolean;
  isApiKeyMode: boolean;
  hasOAuthToken: boolean;
  hasApiKey: boolean;
  envApiKeyCleared: boolean;
}

interface AuthModeResponse {
  success: boolean;
  mode: AnthropicAuthMode;
  status: AuthModeStatus;
  error?: string;
}

/**
 * Hook to get and manage the Anthropic authentication mode
 *
 * Fetches the auth mode from the server's auth-mode endpoint.
 * - 'auth_token': OAuth/CLI subscription mode (API keys ignored)
 * - 'api_key': Pay-per-use mode using API keys
 *
 * @returns Object containing:
 *   - authMode: 'auth_token' | 'api_key' - current authentication mode
 *   - status: AuthModeStatus | null - detailed status information
 *   - isLoading: boolean - true while fetching
 *   - setAuthMode: function - callback to change auth mode
 *   - refresh: function - callback to refresh status
 */
export function useAuthMode() {
  const [authMode, setAuthModeState] = useState<AnthropicAuthMode>('auth_token');
  const [status, setStatus] = useState<AuthModeStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const refresh = useCallback(async () => {
    setIsLoading(true);
    try {
      const response = await fetch(`${getServerUrlSync()}/api/setup/auth-mode`, {
        method: 'GET',
        credentials: 'include',
      });

      if (response.ok) {
        const data: AuthModeResponse = await response.json();
        if (data.success) {
          setAuthModeState(data.mode);
          setStatus(data.status);
        }
      }
    } catch (error) {
      console.warn('Failed to fetch auth mode:', error);
      // Default to auth_token mode on error
      setAuthModeState('auth_token');
    } finally {
      setIsLoading(false);
    }
  }, []);

  const setAuthMode = useCallback(async (mode: AnthropicAuthMode) => {
    try {
      const response = await fetch(`${getServerUrlSync()}/api/setup/auth-mode`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode }),
      });

      if (response.ok) {
        const data: AuthModeResponse = await response.json();
        if (data.success) {
          setAuthModeState(data.mode);
          setStatus(data.status);
          return { success: true };
        }
      }
      return { success: false };
    } catch (error) {
      console.error('Failed to set auth mode:', error);
      return { success: false };
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return {
    authMode,
    status,
    isLoading,
    setAuthMode,
    refresh,
  };
}

/**
 * Hook to check if API key authentication is disabled (OAuth-only mode)
 *
 * @deprecated Use useAuthMode() instead
 * @returns Object containing:
 *   - apiKeyAuthDisabled: boolean - true if OAuth-only mode is active
 *   - isLoading: boolean - true while fetching status
 *   - refresh: function - callback to refresh the status
 */
export function useAuthConfig() {
  const { authMode, isLoading, refresh } = useAuthMode();

  return {
    apiKeyAuthDisabled: authMode === 'auth_token',
    isLoading,
    refresh,
  };
}
