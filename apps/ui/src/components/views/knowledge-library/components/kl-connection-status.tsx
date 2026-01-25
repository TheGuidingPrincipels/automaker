/**
 * Knowledge Library Connection Status
 *
 * Shows the connection status to the AI-Library backend.
 * Uses the useKLHealth hook to monitor connectivity.
 */

import { Wifi, WifiOff, AlertCircle, RefreshCw } from 'lucide-react';
import { Spinner } from '@/components/ui/spinner';
import { Button } from '@/components/ui/button';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import { useKLHealth, isKLOfflineError } from '@/hooks/queries/use-knowledge-library';

type ConnectionState = 'connected' | 'disconnected' | 'checking' | 'error';

interface KLConnectionStatusProps {
  showRefresh?: boolean;
  showVersion?: boolean;
  className?: string;
  'data-testid'?: string;
}

function getConnectionState(
  isLoading: boolean,
  isFetching: boolean,
  isError: boolean,
  error: unknown,
  status?: string
): ConnectionState {
  if (isLoading) return 'checking';
  if (isError || isKLOfflineError(error)) return 'disconnected';
  if (status === 'healthy' || status === 'ok') return isFetching ? 'checking' : 'connected';
  return 'error';
}

interface StatusConfig {
  icon: typeof Wifi;
  label: string;
  description: string;
  className: string;
  bgClassName: string;
}

function getStatusConfig(state: ConnectionState): StatusConfig {
  switch (state) {
    case 'connected':
      return {
        icon: Wifi,
        label: 'Connected',
        description: 'Knowledge Library API is healthy',
        className: 'text-emerald-500',
        bgClassName: 'bg-emerald-500/10 border-emerald-500/20',
      };
    case 'disconnected':
      return {
        icon: WifiOff,
        label: 'Disconnected',
        description: 'Knowledge Library disconnected',
        className: 'text-red-500',
        bgClassName: 'bg-red-500/10 border-red-500/20',
      };
    case 'error':
      return {
        icon: AlertCircle,
        label: 'Error',
        description: 'Knowledge Library API returned an error',
        className: 'text-amber-500',
        bgClassName: 'bg-amber-500/10 border-amber-500/20',
      };
    case 'checking':
    default:
      return {
        icon: Wifi,
        label: 'Checking',
        description: 'Checking Knowledge Library connection...',
        className: 'text-blue-500',
        bgClassName: 'bg-blue-500/10 border-blue-500/20',
      };
  }
}

export function KLConnectionStatus({
  showRefresh = false,
  showVersion = false,
  className,
  'data-testid': testId,
}: KLConnectionStatusProps) {
  const { data, isLoading, isFetching, isError, error, refetch } = useKLHealth();
  const state = getConnectionState(isLoading, isFetching, isError, error, data?.status);
  const config = getStatusConfig(state);
  const Icon = config.icon;

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <div
            className={cn(
              'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border',
              config.bgClassName,
              className
            )}
            data-testid={testId || 'kl-connection-status'}
          >
            {state === 'checking' ? (
              <Spinner size="sm" className={config.className} />
            ) : (
              <Icon className={cn('w-3.5 h-3.5', config.className)} />
            )}
            <span className={config.className}>{config.label}</span>
            {showVersion && data?.version && (
              <span className="text-muted-foreground ml-1">v{data.version}</span>
            )}
            {showRefresh && (
              <Button
                variant="ghost"
                size="icon"
                onClick={(e) => {
                  e.stopPropagation();
                  refetch();
                }}
                disabled={isFetching}
                className="h-4 w-4 p-0 ml-1 hover:bg-transparent"
                data-testid="kl-connection-status-refresh"
              >
                <RefreshCw className={cn('w-3 h-3', isFetching && 'animate-spin')} />
              </Button>
            )}
          </div>
        </TooltipTrigger>
        <TooltipContent>
          <p>{config.description}</p>
          {data?.database && (
            <p className="text-xs text-muted-foreground mt-1">Database: {data.database}</p>
          )}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
