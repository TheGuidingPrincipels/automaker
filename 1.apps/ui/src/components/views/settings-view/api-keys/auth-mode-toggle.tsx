/**
 * AuthModeToggle - UI component for switching between authentication modes
 *
 * Allows users to switch between:
 * - Auth Token mode (subscription/CLI OAuth)
 * - API Key mode (pay-per-use)
 *
 * In Auth Token mode, API keys are completely ignored for 100% reliable
 * subscription-only usage, even if ANTHROPIC_API_KEY is set in the environment.
 *
 * Supports multiple providers via the `provider` prop:
 * - 'anthropic': Anthropic/Claude authentication (default)
 * - 'openai': OpenAI/Codex authentication
 */

import { useState, useCallback } from 'react';
import { toast } from 'sonner';
import { Badge } from '@/components/ui/badge';
import { Spinner } from '@/components/ui/spinner';
import { cn } from '@/lib/utils';
import { CheckCircle2, Key, ShieldCheck, AlertTriangle, Terminal, Copy, Info } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useProviderAuthMode, type AuthProvider, type AnyAuthMode } from '@/hooks/use-auth-config';

/** Supported provider types for auth mode toggle */
export type AuthModeProvider = AuthProvider;

/** Union type for auth modes across providers */
type AuthMode = AnyAuthMode;

/** Provider-specific configuration */
interface ProviderConfig {
  /** API endpoint path for auth mode */
  endpoint: string;
  /** Display name for the provider */
  displayName: string;
  /** CLI command for login */
  loginCommand: string;
  /** Description for subscription mode */
  subscriptionDesc: string;
  /** Description for API key mode */
  apiKeyDesc: string;
}

/** Provider-specific configurations */
const PROVIDER_CONFIGS: Record<AuthModeProvider, ProviderConfig> = {
  anthropic: {
    endpoint: '/api/setup/auth-mode',
    displayName: 'Anthropic',
    loginCommand: 'claude login',
    subscriptionDesc: 'CLI OAuth (Subscription)',
    apiKeyDesc: 'Pay-per-use',
  },
  openai: {
    endpoint: '/api/setup/openai-auth-mode',
    displayName: 'OpenAI',
    loginCommand: 'codex login',
    subscriptionDesc: 'Codex CLI OAuth',
    apiKeyDesc: 'Pay-per-use',
  },
};

export interface AuthModeToggleProps {
  /** Provider to manage auth mode for (default: 'anthropic') */
  provider?: AuthModeProvider;
  /** Optional callback when mode changes */
  onModeChange?: (mode: AuthMode) => void;
  /** Optional test ID for e2e testing */
  testId?: string;
}

export function AuthModeToggle({
  provider = 'anthropic',
  onModeChange,
  testId = 'auth-mode-toggle',
}: AuthModeToggleProps) {
  // Use shared hook for single source of truth (syncs with api-keys-section.tsx)
  const { authMode: mode, status, isLoading, setAuthMode } = useProviderAuthMode(provider);
  const [isSwitching, setIsSwitching] = useState(false);

  const config = PROVIDER_CONFIGS[provider];

  // Switch auth mode using shared hook
  const switchMode = useCallback(
    async (newMode: AuthMode) => {
      if (isSwitching) return;

      setIsSwitching(true);
      try {
        const result = await setAuthMode(newMode as AnyAuthMode);

        if (result.success) {
          onModeChange?.(newMode);
          toast.success(
            newMode === 'auth_token'
              ? `Switched ${config.displayName} to Auth Token mode (subscription)`
              : `Switched ${config.displayName} to API Key mode (pay-per-use)`
          );
        } else {
          toast.error(`Failed to switch ${config.displayName} auth mode`);
        }
      } catch (error) {
        toast.error(`Failed to switch ${config.displayName} auth mode`);
        console.error(`Failed to switch ${config.displayName} auth mode:`, error);
      } finally {
        setIsSwitching(false);
      }
    },
    [isSwitching, config.displayName, onModeChange, setAuthMode]
  );

  if (isLoading) {
    return (
      <div className="p-4 rounded-lg border border-border/50 bg-card/50" data-testid={testId}>
        <div className="flex items-center justify-center gap-2 text-muted-foreground">
          <Spinner size="sm" />
          <span className="text-sm">Loading {config.displayName} authentication mode...</span>
        </div>
      </div>
    );
  }

  const isAuthTokenMode = mode === 'auth_token';
  const hasAuth = isAuthTokenMode
    ? Boolean(status?.hasOAuthToken)
    : Boolean(status?.hasApiKey ?? status?.hasEnvApiKey);
  const hasInactiveAuthToken = !isAuthTokenMode && Boolean(status?.hasOAuthToken);

  return (
    <div
      className="p-4 rounded-lg border border-border/50 bg-card/50 space-y-4"
      data-testid={testId}
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h3 className="font-medium text-foreground">{config.displayName} Authentication Mode</h3>
          <Badge variant={isAuthTokenMode ? 'success' : 'info'} size="sm">
            {isAuthTokenMode ? 'Subscription' : 'Pay-per-use'}
          </Badge>
        </div>
      </div>

      {/* Mode Selection */}
      <div className="grid grid-cols-2 gap-3">
        {/* Auth Token Mode */}
        <button
          onClick={() => switchMode('auth_token')}
          disabled={isSwitching || isAuthTokenMode}
          className={cn(
            'relative p-4 rounded-lg border text-left transition-all',
            'hover:shadow-md focus:outline-none focus:ring-2 focus:ring-ring',
            isAuthTokenMode
              ? 'border-green-500/50 bg-green-500/10 shadow-sm'
              : 'border-border/50 hover:border-border hover:bg-accent/50',
            isSwitching && 'opacity-50 cursor-not-allowed'
          )}
        >
          <div className="flex items-start gap-3">
            <div
              className={cn(
                'w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0',
                isAuthTokenMode
                  ? 'bg-green-500/20 text-green-500'
                  : 'bg-muted text-muted-foreground'
              )}
            >
              <ShieldCheck className="w-4 h-4" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="font-medium text-sm">Auth Token</span>
                {isAuthTokenMode && <CheckCircle2 className="w-4 h-4 text-green-500" />}
              </div>
              <p className="text-xs text-muted-foreground mt-0.5">{config.subscriptionDesc}</p>
            </div>
          </div>
          {isSwitching && !isAuthTokenMode && (
            <div className="absolute inset-0 flex items-center justify-center bg-background/50 rounded-lg">
              <Spinner size="sm" />
            </div>
          )}
        </button>

        {/* API Key Mode */}
        <button
          onClick={() => switchMode('api_key')}
          disabled={isSwitching || !isAuthTokenMode}
          className={cn(
            'relative p-4 rounded-lg border text-left transition-all',
            'hover:shadow-md focus:outline-none focus:ring-2 focus:ring-ring',
            !isAuthTokenMode
              ? 'border-blue-500/50 bg-blue-500/10 shadow-sm'
              : 'border-border/50 hover:border-border hover:bg-accent/50',
            isSwitching && 'opacity-50 cursor-not-allowed'
          )}
        >
          <div className="flex items-start gap-3">
            <div
              className={cn(
                'w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0',
                !isAuthTokenMode ? 'bg-blue-500/20 text-blue-500' : 'bg-muted text-muted-foreground'
              )}
            >
              <Key className="w-4 h-4" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="font-medium text-sm">API Key</span>
                {!isAuthTokenMode && <CheckCircle2 className="w-4 h-4 text-blue-500" />}
              </div>
              <p className="text-xs text-muted-foreground mt-0.5">{config.apiKeyDesc}</p>
            </div>
          </div>
          {isSwitching && isAuthTokenMode && (
            <div className="absolute inset-0 flex items-center justify-center bg-background/50 rounded-lg">
              <Spinner size="sm" />
            </div>
          )}
        </button>
      </div>

      {/* Status Info */}
      {isAuthTokenMode && (
        <div className="p-3 rounded-lg bg-green-500/10 border border-green-500/20">
          <div className="flex items-start gap-2">
            {hasAuth ? (
              <>
                <CheckCircle2 className="w-4 h-4 text-green-500 flex-shrink-0 mt-0.5" />
                <div className="text-xs">
                  <p className="font-medium text-foreground">OAuth authentication active</p>
                  <p className="text-muted-foreground mt-0.5">
                    API keys are ignored. Using CLI authentication for all {config.displayName}{' '}
                    requests.
                  </p>
                </div>
              </>
            ) : (
              <>
                <AlertTriangle className="w-4 h-4 text-amber-500 flex-shrink-0 mt-0.5" />
                <div className="text-xs">
                  <p className="font-medium text-foreground">CLI login required</p>
                  <p className="text-muted-foreground mt-0.5 mb-2">
                    Run the following command to authenticate:
                  </p>
                  <div className="flex items-center gap-2">
                    <Terminal className="w-3 h-3 text-muted-foreground" />
                    <code className="text-xs bg-muted px-2 py-1 rounded font-mono">
                      {config.loginCommand}
                    </code>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-5 px-1.5"
                      onClick={(e) => {
                        e.stopPropagation();
                        navigator.clipboard.writeText(config.loginCommand);
                        toast.success('Command copied!');
                      }}
                    >
                      <Copy className="w-3 h-3" />
                    </Button>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {!isAuthTokenMode && (
        <div className="p-3 rounded-lg bg-blue-500/10 border border-blue-500/20">
          <div className="flex items-start gap-2">
            {hasAuth ? (
              <>
                <CheckCircle2 className="w-4 h-4 text-blue-500 flex-shrink-0 mt-0.5" />
                <div className="text-xs">
                  <p className="font-medium text-foreground">API key configured</p>
                  <p className="text-muted-foreground mt-0.5">
                    Using API key for pay-per-use {config.displayName} billing.
                  </p>
                </div>
              </>
            ) : (
              <>
                <AlertTriangle className="w-4 h-4 text-amber-500 flex-shrink-0 mt-0.5" />
                <div className="text-xs">
                  <p className="font-medium text-foreground">API key required</p>
                  <p className="text-muted-foreground mt-0.5">
                    Enter your {config.displayName} API key below to use pay-per-use billing.
                  </p>
                </div>
              </>
            )}
          </div>
          {hasInactiveAuthToken && (
            <div className="mt-2 flex items-start gap-2 text-xs text-muted-foreground">
              <Info className="w-3.5 h-3.5 text-blue-500 flex-shrink-0 mt-0.5" />
              <p>Auth token detected but inactive. Switch to Auth Token mode to use it.</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
