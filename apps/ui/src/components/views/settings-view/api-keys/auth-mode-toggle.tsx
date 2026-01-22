/**
 * AuthModeToggle - UI component for switching between authentication modes
 *
 * Allows users to switch between:
 * - Auth Token mode (subscription/CLI OAuth)
 * - API Key mode (pay-per-use)
 *
 * In Auth Token mode, API keys are completely ignored for 100% reliable
 * subscription-only usage, even if ANTHROPIC_API_KEY is set in the environment.
 */

import { useState, useCallback, useEffect } from 'react';
import { getServerUrlSync } from '@/lib/http-api-client';
import { toast } from 'sonner';
import { Badge } from '@/components/ui/badge';
import { Spinner } from '@/components/ui/spinner';
import { cn } from '@/lib/utils';
import { CheckCircle2, Key, ShieldCheck, AlertTriangle, Terminal, Copy } from 'lucide-react';
import { Button } from '@/components/ui/button';
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

export function AuthModeToggle() {
  const [mode, setMode] = useState<AnthropicAuthMode>('auth_token');
  const [status, setStatus] = useState<AuthModeStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSwitching, setIsSwitching] = useState(false);

  // Fetch current auth mode on mount
  useEffect(() => {
    const fetchAuthMode = async () => {
      try {
        const response = await fetch(`${getServerUrlSync()}/api/setup/auth-mode`, {
          method: 'GET',
          credentials: 'include',
        });
        if (response.ok) {
          const data: AuthModeResponse = await response.json();
          if (data.success) {
            setMode(data.mode);
            setStatus(data.status);
          }
        }
      } catch (error) {
        console.error('Failed to fetch auth mode:', error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchAuthMode();
  }, []);

  // Switch auth mode
  const switchMode = useCallback(
    async (newMode: AnthropicAuthMode) => {
      if (isSwitching) return;

      setIsSwitching(true);
      try {
        const response = await fetch(`${getServerUrlSync()}/api/setup/auth-mode`, {
          method: 'POST',
          credentials: 'include',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ mode: newMode }),
        });

        if (response.ok) {
          const data: AuthModeResponse = await response.json();
          if (data.success) {
            setMode(data.mode);
            setStatus(data.status);
            toast.success(
              newMode === 'auth_token'
                ? 'Switched to Auth Token mode (subscription)'
                : 'Switched to API Key mode (pay-per-use)'
            );
          } else {
            toast.error(data.error || 'Failed to switch auth mode');
          }
        } else {
          toast.error('Failed to switch auth mode');
        }
      } catch (error) {
        toast.error('Failed to switch auth mode');
        console.error('Failed to switch auth mode:', error);
      } finally {
        setIsSwitching(false);
      }
    },
    [isSwitching]
  );

  if (isLoading) {
    return (
      <div className="p-4 rounded-lg border border-border/50 bg-card/50">
        <div className="flex items-center justify-center gap-2 text-muted-foreground">
          <Spinner size="sm" />
          <span className="text-sm">Loading authentication mode...</span>
        </div>
      </div>
    );
  }

  const isAuthTokenMode = mode === 'auth_token';
  const hasAuth = isAuthTokenMode ? status?.hasOAuthToken : status?.hasApiKey;

  return (
    <div className="p-4 rounded-lg border border-border/50 bg-card/50 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h3 className="font-medium text-foreground">Authentication Mode</h3>
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
              <p className="text-xs text-muted-foreground mt-0.5">CLI OAuth (Subscription)</p>
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
              <p className="text-xs text-muted-foreground mt-0.5">Pay-per-use</p>
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
            {status?.hasOAuthToken ? (
              <>
                <CheckCircle2 className="w-4 h-4 text-green-500 flex-shrink-0 mt-0.5" />
                <div className="text-xs">
                  <p className="font-medium text-foreground">OAuth authentication active</p>
                  <p className="text-muted-foreground mt-0.5">
                    API keys are ignored. Using CLI authentication for all requests.
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
                      claude login
                    </code>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-5 px-1.5"
                      onClick={(e) => {
                        e.stopPropagation();
                        navigator.clipboard.writeText('claude login');
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
            {status?.hasApiKey ? (
              <>
                <CheckCircle2 className="w-4 h-4 text-blue-500 flex-shrink-0 mt-0.5" />
                <div className="text-xs">
                  <p className="font-medium text-foreground">API key configured</p>
                  <p className="text-muted-foreground mt-0.5">
                    Using API key for pay-per-use billing.
                  </p>
                </div>
              </>
            ) : (
              <>
                <AlertTriangle className="w-4 h-4 text-amber-500 flex-shrink-0 mt-0.5" />
                <div className="text-xs">
                  <p className="font-medium text-foreground">API key required</p>
                  <p className="text-muted-foreground mt-0.5">
                    Enter your Anthropic API key below to use pay-per-use billing.
                  </p>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
