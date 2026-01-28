/**
 * Knowledge Library Query Hooks
 *
 * TanStack Query hooks for the Knowledge Library (AI-Library) integration.
 * These hooks manage server state for sessions, cleanup plans, routing plans,
 * library browsing, and RAG queries.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { queryKeys } from '@/lib/query-keys';
import { STALE_TIMES } from '@/lib/query-client';
import {
  knowledgeLibraryApi,
  KnowledgeLibraryError,
  isKLOfflineError,
} from '@/lib/knowledge-library-api';
import type {
  KLSelectDestinationRequest,
  KLSemanticSearchRequest,
  KLAskRequest,
  KLCreateSessionRequest,
  KLCleanupDisposition,
  KLCleanupMode,
  KLContentMode,
} from '@automaker/types';

// ============================================================================
// Stale Times
// ============================================================================

/** Knowledge Library specific stale times */
const KL_STALE_TIMES = {
  /** Health check - relatively fast */
  HEALTH: 30 * 1000, // 30 seconds
  /** Sessions change during workflow */
  SESSIONS: 10 * 1000, // 10 seconds
  /** Library structure is relatively stable */
  LIBRARY: 2 * 60 * 1000, // 2 minutes
  /** File content rarely changes */
  FILE_CONTENT: 5 * 60 * 1000, // 5 minutes
  /** Conversations are stable */
  CONVERSATIONS: 60 * 1000, // 1 minute
} as const;

// ============================================================================
// Health Check
// ============================================================================

const KL_HEALTH_REFETCH_INTERVAL_MS = {
  CONNECTED: 30000,
  DISCONNECTED: 5000,
} as const;

type KLHealthQueryStatus = 'pending' | 'error' | 'success';

export const getKLHealthRefetchIntervalMs = (params: {
  queryStatus?: KLHealthQueryStatus;
  dataStatus?: string;
  error?: unknown;
}): number => {
  // TanStack Query can keep the last successful data even when later refetches fail,
  // so make sure we react to the query's error state (not just cached data).
  if (params.queryStatus === 'error' || params.error != null) {
    return KL_HEALTH_REFETCH_INTERVAL_MS.DISCONNECTED;
  }

  if (params.dataStatus === 'healthy' || params.dataStatus === 'ok') {
    return KL_HEALTH_REFETCH_INTERVAL_MS.CONNECTED;
  }

  return KL_HEALTH_REFETCH_INTERVAL_MS.DISCONNECTED;
};

/**
 * Check Knowledge Library service health
 *
 * @example
 * ```tsx
 * const { data: health, isLoading, error } = useKLHealth();
 * if (isKLOfflineError(error)) {
 *   // Show "Knowledge Library disconnected"
 * }
 * ```
 */
export function useKLHealth() {
  return useQuery({
    queryKey: queryKeys.knowledgeLibrary.health(),
    queryFn: () => knowledgeLibraryApi.getHealth(),
    staleTime: KL_STALE_TIMES.HEALTH,
    retry: 3, // Retry 3 times before giving up
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 10000),
    refetchOnWindowFocus: true,
    // Dynamic interval: faster when disconnected, slower when connected
    refetchInterval: (query) =>
      getKLHealthRefetchIntervalMs({
        queryStatus: query.state.status,
        dataStatus: query.state.data?.status,
        error: query.state.error,
      }),
  });
}

// ============================================================================
// Sessions
// ============================================================================

/**
 * List all Knowledge Library sessions
 */
export function useKLSessions(limit?: number, offset?: number) {
  return useQuery({
    queryKey: queryKeys.knowledgeLibrary.sessions(limit, offset),
    queryFn: () => knowledgeLibraryApi.getSessions(limit, offset),
    staleTime: KL_STALE_TIMES.SESSIONS,
  });
}

/**
 * Get a single session by ID
 */
export function useKLSession(sessionId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.knowledgeLibrary.session(sessionId ?? ''),
    queryFn: () => knowledgeLibraryApi.getSession(sessionId!),
    enabled: !!sessionId,
    staleTime: KL_STALE_TIMES.SESSIONS,
  });
}

/**
 * Create a new session (upload-first flow)
 */
export function useKLCreateSession() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data?: KLCreateSessionRequest) => knowledgeLibraryApi.createSession(data),
    onSuccess: () => {
      // Invalidate sessions list
      queryClient.invalidateQueries({
        queryKey: queryKeys.knowledgeLibrary.sessionsBase(),
      });
    },
  });
}

/**
 * Upload a source file to a session
 */
type KLUploadSourceVariables = { sessionId: string; file: File };

export function useKLUploadSource() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ sessionId, file }: KLUploadSourceVariables) =>
      knowledgeLibraryApi.uploadSource(sessionId, file),
    onSuccess: (data, variables) => {
      const { sessionId } = variables;
      // Update session cache
      queryClient.setQueryData(queryKeys.knowledgeLibrary.session(sessionId), data);
      // Invalidate related queries
      queryClient.invalidateQueries({
        queryKey: queryKeys.knowledgeLibrary.blocks(sessionId),
      });
    },
  });
}

/**
 * Delete a session
 */
export function useKLDeleteSession() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (sessionId: string) => knowledgeLibraryApi.deleteSession(sessionId),
    onSuccess: (_, sessionId) => {
      // Remove from cache
      queryClient.removeQueries({
        queryKey: queryKeys.knowledgeLibrary.session(sessionId),
      });
      // Invalidate sessions list
      queryClient.invalidateQueries({
        queryKey: queryKeys.knowledgeLibrary.sessionsBase(),
      });
    },
  });
}

// ============================================================================
// Blocks
// ============================================================================

/**
 * Get blocks for a session
 */
export function useKLBlocks(sessionId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.knowledgeLibrary.blocks(sessionId ?? ''),
    queryFn: () => knowledgeLibraryApi.getBlocks(sessionId!),
    enabled: !!sessionId,
    staleTime: KL_STALE_TIMES.SESSIONS,
  });
}

// ============================================================================
// Mode
// ============================================================================

/**
 * Set session content mode (strict/refinement)
 */
export function useKLSetMode(sessionId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (mode: KLContentMode) => knowledgeLibraryApi.setMode(sessionId, { mode }),
    onSuccess: (data) => {
      queryClient.setQueryData(queryKeys.knowledgeLibrary.session(sessionId), data);
    },
  });
}

// ============================================================================
// Cleanup Plan
// ============================================================================

/**
 * Generate cleanup plan for a session
 *
 * @param sessionId - The session ID to generate cleanup plan for
 *
 * @example
 * ```tsx
 * const generateCleanupPlan = useKLGenerateCleanupPlan(sessionId);
 *
 * // Generate with defaults (useAi: true, cleanupMode: 'balanced')
 * generateCleanupPlan.mutate({});
 *
 * // Generate with specific mode
 * generateCleanupPlan.mutate({ cleanupMode: 'aggressive' });
 *
 * // Generate without AI
 * generateCleanupPlan.mutate({ useAi: false });
 * ```
 */
export function useKLGenerateCleanupPlan(sessionId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      useAi = true,
      cleanupMode = 'balanced',
    }: {
      useAi?: boolean;
      cleanupMode?: KLCleanupMode;
    } = {}) => knowledgeLibraryApi.generateCleanupPlan(sessionId, { useAi, cleanupMode }),
    onSuccess: () => {
      // Invalidate cleanup plan cache to refetch fresh data
      queryClient.invalidateQueries({
        queryKey: queryKeys.knowledgeLibrary.cleanupPlan(sessionId),
      });
      // Also refresh session (phase may have changed)
      queryClient.invalidateQueries({
        queryKey: queryKeys.knowledgeLibrary.session(sessionId),
      });
    },
  });
}

/**
 * Get cleanup plan for a session
 */
export function useKLCleanupPlan(sessionId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.knowledgeLibrary.cleanupPlan(sessionId ?? ''),
    queryFn: () => knowledgeLibraryApi.getCleanupPlan(sessionId!),
    enabled: !!sessionId,
    staleTime: KL_STALE_TIMES.SESSIONS,
  });
}

/**
 * Decide on a cleanup item (keep/discard)
 */
export function useKLDecideCleanupItem(sessionId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      blockId,
      disposition,
    }: {
      blockId: string;
      disposition: KLCleanupDisposition;
    }) => knowledgeLibraryApi.decideCleanupItem(sessionId, blockId, { disposition }),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.knowledgeLibrary.cleanupPlan(sessionId),
      });
    },
  });
}

/**
 * Approve the cleanup plan
 */
export function useKLApproveCleanupPlan(sessionId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => knowledgeLibraryApi.approveCleanupPlan(sessionId),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.knowledgeLibrary.cleanupPlan(sessionId),
      });
      // Refresh session (phase changed)
      queryClient.invalidateQueries({
        queryKey: queryKeys.knowledgeLibrary.session(sessionId),
      });
    },
  });
}

// ============================================================================
// Routing Plan
// ============================================================================

/**
 * Generate routing plan for a session
 */
export function useKLGenerateRoutingPlan(sessionId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (options: { useAi?: boolean; useCandidateFinder?: boolean } = {}) => {
      const { useAi = true, useCandidateFinder = true } = options;
      return knowledgeLibraryApi.generateRoutingPlan(sessionId, useAi, useCandidateFinder);
    },
    onSuccess: (data) => {
      queryClient.setQueryData(queryKeys.knowledgeLibrary.routingPlan(sessionId), data);
      // Refresh session (phase changed)
      queryClient.invalidateQueries({
        queryKey: queryKeys.knowledgeLibrary.session(sessionId),
      });
    },
  });
}

/**
 * Valid session phases where routing plan exists
 */
const ROUTING_PLAN_PHASES = [
  'routing_plan_ready',
  'awaiting_approval',
  'ready_to_execute',
  'executing',
  'verifying',
  'completed',
];

export const isKLRoutingPlanPhase = (sessionPhase?: string): boolean =>
  !!sessionPhase && ROUTING_PLAN_PHASES.includes(sessionPhase);

/**
 * Get routing plan for a session
 *
 * @param sessionId - The session ID
 * @param sessionPhase - Optional session phase.
 *   - If you pass this argument, the query only runs during routing-related phases
 *     (routing_plan_ready, awaiting_approval, etc.) to avoid premature 404s.
 *   - If you omit this argument, the query runs whenever `sessionId` exists.
 */
export function useKLRoutingPlan(sessionId: string | undefined, sessionPhase?: string) {
  // If `sessionPhase` is provided, gate this query to routing phases to avoid 404s.
  // If it is omitted, enable the query whenever `sessionId` exists.
  const hasSessionPhaseArg = arguments.length >= 2;
  const isRoutingPhase = isKLRoutingPlanPhase(sessionPhase);

  return useQuery({
    queryKey: queryKeys.knowledgeLibrary.routingPlan(sessionId ?? ''),
    queryFn: () => knowledgeLibraryApi.getRoutingPlan(sessionId!),
    enabled: !!sessionId && (!hasSessionPhaseArg || isRoutingPhase),
    staleTime: KL_STALE_TIMES.SESSIONS,
  });
}

/**
 * Select a destination for a block
 */
export function useKLSelectDestination(sessionId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ blockId, data }: { blockId: string; data: KLSelectDestinationRequest }) =>
      knowledgeLibraryApi.selectDestination(sessionId, blockId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.knowledgeLibrary.routingPlan(sessionId),
      });
    },
  });
}

/**
 * Reject a block from routing
 */
export function useKLRejectBlock(sessionId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (blockId: string) => knowledgeLibraryApi.rejectBlock(sessionId, blockId),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.knowledgeLibrary.routingPlan(sessionId),
      });
    },
  });
}

/**
 * Approve the routing plan
 */
export function useKLApproveRoutingPlan(sessionId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => knowledgeLibraryApi.approveRoutingPlan(sessionId),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.knowledgeLibrary.routingPlan(sessionId),
      });
      // Refresh session (phase changed)
      queryClient.invalidateQueries({
        queryKey: queryKeys.knowledgeLibrary.session(sessionId),
      });
    },
  });
}

// ============================================================================
// Execution
// ============================================================================

/**
 * Execute a session (write blocks to library)
 */
export function useKLExecuteSession(sessionId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => knowledgeLibraryApi.executeSession(sessionId),
    onSuccess: () => {
      // Refresh session (phase changed to completed)
      queryClient.invalidateQueries({
        queryKey: queryKeys.knowledgeLibrary.session(sessionId),
      });
      // Refresh library (new files may have been created)
      queryClient.invalidateQueries({
        queryKey: queryKeys.knowledgeLibrary.library(),
      });
    },
  });
}

// ============================================================================
// Library
// ============================================================================

/**
 * Get the library structure (categories and files)
 */
export function useKLLibrary() {
  return useQuery({
    queryKey: queryKeys.knowledgeLibrary.library(),
    queryFn: () => knowledgeLibraryApi.getLibrary(),
    staleTime: KL_STALE_TIMES.LIBRARY,
  });
}

/**
 * Get metadata for a library file
 */
export function useKLFileMetadata(filePath: string | undefined) {
  return useQuery({
    queryKey: queryKeys.knowledgeLibrary.fileMetadata(filePath ?? ''),
    queryFn: () => knowledgeLibraryApi.getFileMetadata(filePath!),
    enabled: !!filePath,
    staleTime: KL_STALE_TIMES.LIBRARY,
  });
}

/**
 * Get content of a library file
 */
export function useKLFileContent(filePath: string | undefined) {
  return useQuery({
    queryKey: queryKeys.knowledgeLibrary.fileContent(filePath ?? ''),
    queryFn: () => knowledgeLibraryApi.getFileContent(filePath!),
    enabled: !!filePath,
    staleTime: KL_STALE_TIMES.FILE_CONTENT,
  });
}

/**
 * Search library by keyword
 */
export function useKLLibraryKeywordSearch(query: string | undefined) {
  return useQuery({
    queryKey: queryKeys.knowledgeLibrary.keywordSearch(query ?? ''),
    queryFn: () => knowledgeLibraryApi.searchKeyword(query!),
    enabled: !!query && query.length >= 2,
    staleTime: STALE_TIMES.DEFAULT,
  });
}

/**
 * Trigger library indexing
 */
export function useKLIndexLibrary() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => knowledgeLibraryApi.indexLibrary(),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.knowledgeLibrary.indexStats(),
      });
    },
  });
}

/**
 * Get library index stats
 */
export function useKLIndexStats() {
  return useQuery({
    queryKey: queryKeys.knowledgeLibrary.indexStats(),
    queryFn: () => knowledgeLibraryApi.getIndexStats(),
    staleTime: KL_STALE_TIMES.LIBRARY,
  });
}

// ============================================================================
// Query (Semantic Search & RAG)
// ============================================================================

/**
 * Semantic search in the library
 */
export function useKLSemanticSearch() {
  return useMutation({
    mutationFn: (data: KLSemanticSearchRequest) => knowledgeLibraryApi.semanticSearch(data),
  });
}

/**
 * Ask the library a question (RAG)
 */
export function useKLAsk() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: KLAskRequest) => knowledgeLibraryApi.ask(data),
    onSuccess: (data) => {
      // If conversation was created/updated, invalidate conversations list
      if (data.conversation_id) {
        queryClient.invalidateQueries({
          queryKey: queryKeys.knowledgeLibrary.conversations(),
        });
      }
    },
  });
}

/**
 * Get all conversations
 */
export function useKLConversations() {
  return useQuery({
    queryKey: queryKeys.knowledgeLibrary.conversations(),
    queryFn: () => knowledgeLibraryApi.getConversations(),
    staleTime: KL_STALE_TIMES.CONVERSATIONS,
  });
}

/**
 * Get a single conversation
 */
export function useKLConversation(conversationId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.knowledgeLibrary.conversation(conversationId ?? ''),
    queryFn: () => knowledgeLibraryApi.getConversation(conversationId!),
    enabled: !!conversationId,
    staleTime: KL_STALE_TIMES.CONVERSATIONS,
  });
}

/**
 * Delete a conversation
 */
export function useKLDeleteConversation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (conversationId: string) => knowledgeLibraryApi.deleteConversation(conversationId),
    onSuccess: (_, conversationId) => {
      queryClient.removeQueries({
        queryKey: queryKeys.knowledgeLibrary.conversation(conversationId),
      });
      queryClient.invalidateQueries({
        queryKey: queryKeys.knowledgeLibrary.conversations(),
      });
    },
  });
}

// ============================================================================
// Re-exports for convenience
// ============================================================================

export { KnowledgeLibraryError, isKLOfflineError };
