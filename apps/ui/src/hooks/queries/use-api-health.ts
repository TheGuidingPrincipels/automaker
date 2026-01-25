/**
 * API Health Query Hook
 *
 * React Query hook for fetching and monitoring API health status.
 */

import { useQuery } from '@tanstack/react-query';
import { getServerUrlSync } from '@/lib/http-api-client';
import { queryKeys } from '@/lib/query-keys';
import { STALE_TIMES } from '@/lib/query-client';

/** Health check response from /api/health endpoint */
export interface ApiHealthResponse {
  status: 'ok' | 'error';
  timestamp: string;
  version: string;
}

/** Detailed health check response from /api/health/detailed endpoint */
export interface ApiHealthDetailedResponse extends ApiHealthResponse {
  uptime: number;
  memory: {
    rss: number;
    heapTotal: number;
    heapUsed: number;
    external: number;
    arrayBuffers: number;
  };
  dataDir: string;
  auth: {
    enabled: boolean;
    method: string;
  };
  env: {
    nodeVersion: string;
    platform: string;
    arch: string;
  };
}

/**
 * Fetch basic health status from the API (unauthenticated)
 */
async function fetchHealthStatus(): Promise<ApiHealthResponse> {
  const serverUrl = getServerUrlSync();
  const response = await fetch(`${serverUrl}/api/health`, {
    method: 'GET',
    cache: 'no-store',
    signal: AbortSignal.timeout(5000), // 5 second timeout
  });

  if (!response.ok) {
    throw new Error(`Health check failed: ${response.status}`);
  }

  return response.json();
}

/**
 * Hook to fetch and monitor basic API health status
 *
 * @example
 * ```tsx
 * const { data, isLoading, isError } = useApiHealth();
 *
 * if (isLoading) return <p>Checking...</p>;
 * if (isError) return <p>Disconnected</p>;
 * if (data?.status === 'ok') return <p>Connected</p>;
 * ```
 */
export function useApiHealth() {
  return useQuery({
    queryKey: queryKeys.health.api(),
    queryFn: fetchHealthStatus,
    staleTime: STALE_TIMES.DEFAULT,
    refetchInterval: 30000, // Refetch every 30 seconds
    retry: 1, // Only retry once for health checks
    refetchOnWindowFocus: true,
  });
}
