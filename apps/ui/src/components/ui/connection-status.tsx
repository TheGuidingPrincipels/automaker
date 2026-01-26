/**
 * ConnectionStatus Component
 *
 * Displays the API health/connection status with visual indicators.
 * Shows connected, disconnected, or checking states with appropriate styling.
 */

import { AlertCircle, RefreshCw, Wifi, WifiOff } from 'lucide-react';
import { Spinner } from '@/components/ui/spinner';
import { Button } from '@/components/ui/button';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import { useApiHealth, type ApiHealthResponse } from '@/hooks/queries';

/** Connection status states */
type ConnectionState = 'connected' | 'disconnected' | 'checking' | 'error';

interface ConnectionStatusProps {
  /** Show as a compact badge (default) or expanded card */
  variant?: 'badge' | 'card';
  /** Show the refresh button */
  showRefresh?: boolean;
  /** Additional CSS classes */
  className?: string;
  /** Show version information */
  showVersion?: boolean;
  /** Data test id for testing */
  'data-testid'?: string;
}

// Re-export the hook for convenience
export { useApiHealth } from '@/hooks/queries';

/**
 * Get the connection state from query status
 */
function getConnectionState(
  isLoading: boolean,
  isFetching: boolean,
  isError: boolean,
  data: ApiHealthResponse | undefined
): ConnectionState {
  if (isLoading) return 'checking';
  if (isError) return 'disconnected';
  if (data?.status === 'ok') return isFetching ? 'checking' : 'connected';
  if (data?.status === 'error') return 'error';
  return 'disconnected';
}

/** Status configuration type */
interface StatusConfig {
  icon: typeof Wifi;
  label: string;
  description: string;
  className: string;
  bgClassName: string;
}

/**
 * Get status configuration based on connection state
 */
function getStatusConfig(state: ConnectionState): StatusConfig {
  switch (state) {
    case 'connected':
      return {
        icon: Wifi,
        label: 'Connected',
        description: 'API is healthy and responding',
        className: 'text-emerald-500',
        bgClassName: 'bg-emerald-500/10 border-emerald-500/20',
      };
    case 'disconnected':
      return {
        icon: WifiOff,
        label: 'Disconnected',
        description: 'Unable to reach the API server',
        className: 'text-red-500',
        bgClassName: 'bg-red-500/10 border-red-500/20',
      };
    case 'error':
      return {
        icon: AlertCircle,
        label: 'Error',
        description: 'API returned an error status',
        className: 'text-amber-500',
        bgClassName: 'bg-amber-500/10 border-amber-500/20',
      };
    case 'checking':
    default:
      return {
        icon: Wifi, // Placeholder - we render Spinner directly for checking state
        label: 'Checking',
        description: 'Checking API connection...',
        className: 'text-blue-500',
        bgClassName: 'bg-blue-500/10 border-blue-500/20',
      };
  }
}

/**
 * ConnectionStatus - Badge variant (compact indicator)
 */
function ConnectionStatusBadge({
  className,
  showVersion,
  showRefresh,
  'data-testid': testId,
}: ConnectionStatusProps) {
  const { data, isLoading, isFetching, isError, refetch } = useApiHealth();
  const state = getConnectionState(isLoading, isFetching, isError, data);
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
            data-testid={testId || 'connection-status-badge'}
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
                data-testid="connection-status-refresh"
              >
                <RefreshCw className={cn('w-3 h-3', isFetching && 'animate-spin')} />
              </Button>
            )}
          </div>
        </TooltipTrigger>
        <TooltipContent>
          <p>{config.description}</p>
          {data?.timestamp && (
            <p className="text-xs text-muted-foreground mt-1">
              Last check: {new Date(data.timestamp).toLocaleTimeString()}
            </p>
          )}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

/**
 * ConnectionStatus - Card variant (expanded view)
 */
function ConnectionStatusCard({
  className,
  showVersion = true,
  showRefresh = true,
  'data-testid': testId,
}: ConnectionStatusProps) {
  const { data, isLoading, isFetching, isError, refetch } = useApiHealth();
  const state = getConnectionState(isLoading, isFetching, isError, data);
  const config = getStatusConfig(state);
  const Icon = config.icon;

  return (
    <div
      className={cn(
        'rounded-2xl overflow-hidden',
        'border border-border/50',
        'bg-gradient-to-br from-card/90 via-card/70 to-card/80 backdrop-blur-xl',
        'shadow-sm shadow-black/5',
        className
      )}
      data-testid={testId || 'connection-status-card'}
    >
      <div className="p-6 border-b border-border/50 bg-gradient-to-r from-transparent via-accent/5 to-transparent">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-3">
            <div
              className={cn(
                'w-9 h-9 rounded-xl flex items-center justify-center border',
                config.bgClassName
              )}
            >
              {state === 'checking' ? (
                <Spinner size="sm" className={config.className} />
              ) : (
                <Icon className={cn('w-5 h-5', config.className)} />
              )}
            </div>
            <h2 className="text-lg font-semibold text-foreground tracking-tight">API Connection</h2>
          </div>
          {showRefresh && (
            <Button
              variant="ghost"
              size="icon"
              onClick={() => refetch()}
              disabled={isFetching}
              data-testid="connection-status-card-refresh"
              title="Refresh connection status"
              className={cn(
                'h-9 w-9 rounded-lg',
                'hover:bg-accent/50 hover:scale-105',
                'transition-all duration-200'
              )}
            >
              {isFetching ? <Spinner size="sm" /> : <RefreshCw className="w-4 h-4" />}
            </Button>
          )}
        </div>
        <p className="text-sm text-muted-foreground/80 ml-12">
          Monitor backend API health and connectivity
        </p>
      </div>

      <div className="p-6 space-y-4">
        <div className={cn('flex items-center gap-3 p-4 rounded-xl border', config.bgClassName)}>
          <div
            className={cn(
              'w-10 h-10 rounded-xl flex items-center justify-center border shrink-0',
              config.bgClassName
            )}
          >
            {state === 'checking' ? (
              <Spinner size="sm" className={config.className} />
            ) : (
              <Icon className={cn('w-5 h-5', config.className)} />
            )}
          </div>
          <div className="flex-1 min-w-0">
            <p className={cn('text-sm font-medium', config.className)}>{config.label}</p>
            <p className={cn('text-xs mt-1', config.className, 'opacity-70')}>
              {config.description}
            </p>
          </div>
        </div>

        {(data?.version || data?.timestamp) && (
          <div className="space-y-2 text-xs text-muted-foreground">
            {showVersion && data?.version && (
              <div className="flex items-center justify-between">
                <span>Server Version</span>
                <span className="font-mono">{data.version}</span>
              </div>
            )}
            {data?.timestamp && (
              <div className="flex items-center justify-between">
                <span>Last Check</span>
                <span>{new Date(data.timestamp).toLocaleString()}</span>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * ConnectionStatus Component
 *
 * A visual indicator showing the API health status.
 * Can be rendered as a compact badge or expanded card.
 *
 * @example
 * // Compact badge (default)
 * <ConnectionStatus />
 *
 * @example
 * // Expanded card with all details
 * <ConnectionStatus variant="card" showVersion showRefresh />
 */
export function ConnectionStatus({ variant = 'badge', ...props }: ConnectionStatusProps) {
  if (variant === 'card') {
    return <ConnectionStatusCard {...props} />;
  }
  return <ConnectionStatusBadge {...props} />;
}

export default ConnectionStatus;
