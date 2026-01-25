/**
 * Knowledge Library API Client
 *
 * Typed client for communicating with the AI-Library backend service.
 * This is a SEPARATE service from the main Automaker backend.
 *
 * Key behaviors:
 * - Does NOT trigger global "server offline" UX on connection errors
 * - Throws KnowledgeLibraryError for all failures (check isOfflineError for disconnected state)
 * - Supports WebSocket streaming for real-time updates
 */

import type {
  KLHealthResponse,
  KLCreateSessionRequest,
  KLSessionResponse,
  KLSessionListResponse,
  KLBlockListResponse,
  KLCleanupPlanResponse,
  KLCleanupDecisionRequest,
  KLRoutingPlanResponse,
  KLSelectDestinationRequest,
  KLSetModeRequest,
  KLExecuteResponse,
  KLLibraryStructureResponse,
  KLLibraryFileResponse,
  KLLibraryFileContentResponse,
  KLLibrarySearchResponse,
  KLIndexResponse,
  KLSemanticSearchRequest,
  KLSemanticSearchResponse,
  KLAskRequest,
  KLAskResponse,
  KLConversationListResponse,
  KLConversation,
  KLSuccessResponse,
  KLStreamEvent,
  KLStreamCommandRequest,
} from '@automaker/types';

// ============================================================================
// Error Handling
// ============================================================================

/**
 * Custom error for Knowledge Library API failures.
 * Check `isOfflineError` to determine if the service is disconnected.
 */
export class KnowledgeLibraryError extends Error {
  public readonly isOfflineError: boolean;
  public readonly statusCode?: number;

  constructor(message: string, options?: { isOfflineError?: boolean; statusCode?: number }) {
    super(message);
    this.name = 'KnowledgeLibraryError';
    this.isOfflineError = options?.isOfflineError ?? false;
    this.statusCode = options?.statusCode;
  }
}

/**
 * Check if an error indicates the Knowledge Library service is offline
 */
export function isKLOfflineError(error: unknown): boolean {
  if (error instanceof KnowledgeLibraryError) {
    return error.isOfflineError;
  }
  if (error instanceof TypeError) {
    const message = error.message.toLowerCase();
    return (
      message.includes('failed to fetch') ||
      message.includes('network') ||
      message.includes('econnrefused')
    );
  }
  return false;
}

/**
 * Handle fetch errors consistently across API methods
 */
function handleFetchError(error: unknown): never {
  if (error instanceof KnowledgeLibraryError) throw error;
  if (error instanceof TypeError) {
    throw new KnowledgeLibraryError('Knowledge Library service is disconnected', {
      isOfflineError: true,
    });
  }
  throw new KnowledgeLibraryError(
    error instanceof Error ? error.message : 'Unknown error',
    { isOfflineError: false }
  );
}

// ============================================================================
// Configuration
// ============================================================================

/**
 * Get the Knowledge Library API base URL from environment
 */
function getBaseUrl(): string {
  // Use environment variable or default
  const envUrl = import.meta.env.VITE_KNOWLEDGE_LIBRARY_API;
  return envUrl || 'http://localhost:8001';
}

/**
 * Encode a file path for URL (encode each segment, preserve slashes)
 */
function encodePath(path: string): string {
  const normalized = path.replace(/^\/+/, '');
  return normalized.split('/').map(encodeURIComponent).join('/');
}

// ============================================================================
// HTTP Client
// ============================================================================

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';
  body?: unknown;
  params?: Record<string, string | number | boolean | undefined>;
}

/**
 * Make an HTTP request to the Knowledge Library API
 */
async function request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, params } = options;

  // Build URL with query params
  let url = `${getBaseUrl()}${endpoint}`;
  if (params) {
    const searchParams = new URLSearchParams();
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined) {
        searchParams.append(key, String(value));
      }
    }
    const queryString = searchParams.toString();
    if (queryString) {
      url += `?${queryString}`;
    }
  }

  const headers: HeadersInit = {
    'Content-Type': 'application/json',
  };

  try {
    const response = await fetch(url, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });

    if (!response.ok) {
      // Try to extract error message from response
      let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
      try {
        const errorBody = await response.json();
        if (errorBody.error) {
          errorMessage = errorBody.error;
        } else if (errorBody.detail) {
          errorMessage = errorBody.detail;
        }
      } catch {
        // Ignore JSON parse errors
      }

      throw new KnowledgeLibraryError(errorMessage, {
        statusCode: response.status,
        isOfflineError: false,
      });
    }

    return (await response.json()) as T;
  } catch (error) {
    handleFetchError(error);
  }
}

// ============================================================================
// API Methods
// ============================================================================

export const knowledgeLibraryApi = {
  // --------------------------------------------------------------------------
  // Health Check
  // --------------------------------------------------------------------------

  /**
   * Check if the Knowledge Library service is healthy
   */
  async getHealth(): Promise<KLHealthResponse> {
    return request<KLHealthResponse>('/health');
  },

  // --------------------------------------------------------------------------
  // Sessions
  // --------------------------------------------------------------------------

  /**
   * List all sessions
   */
  async getSessions(limit?: number, offset?: number): Promise<KLSessionListResponse> {
    return request<KLSessionListResponse>('/api/sessions', {
      params: { limit, offset },
    });
  },

  /**
   * Create a new session (upload-first flow: create empty, then upload)
   */
  async createSession(data?: KLCreateSessionRequest): Promise<KLSessionResponse> {
    return request<KLSessionResponse>('/api/sessions', {
      method: 'POST',
      body: data ?? {},
    });
  },

  /**
   * Upload a source file to a session
   */
  async uploadSource(sessionId: string, file: File): Promise<KLSessionResponse> {
    const url = `${getBaseUrl()}/api/sessions/${sessionId}/upload`;

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch(url, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
        try {
          const errorBody = await response.json();
          if (errorBody.error) {
            errorMessage = errorBody.error;
          } else if (errorBody.detail) {
            errorMessage = errorBody.detail;
          }
        } catch {
          // Response body is not JSON; fall back to HTTP status message
        }
        throw new KnowledgeLibraryError(errorMessage, {
          statusCode: response.status,
          isOfflineError: false,
        });
      }

      return (await response.json()) as KLSessionResponse;
    } catch (error) {
      handleFetchError(error);
    }
  },

  /**
   * Get a session by ID
   */
  async getSession(sessionId: string): Promise<KLSessionResponse> {
    return request<KLSessionResponse>(`/api/sessions/${sessionId}`);
  },

  /**
   * Delete a session
   */
  async deleteSession(sessionId: string): Promise<KLSuccessResponse> {
    return request<KLSuccessResponse>(`/api/sessions/${sessionId}`, {
      method: 'DELETE',
    });
  },

  /**
   * Get blocks for a session
   */
  async getBlocks(sessionId: string): Promise<KLBlockListResponse> {
    return request<KLBlockListResponse>(`/api/sessions/${sessionId}/blocks`);
  },

  /**
   * Set the content mode for a session
   */
  async setMode(sessionId: string, data: KLSetModeRequest): Promise<KLSessionResponse> {
    return request<KLSessionResponse>(`/api/sessions/${sessionId}/mode`, {
      method: 'POST',
      body: data,
    });
  },

  // --------------------------------------------------------------------------
  // Cleanup Plan
  // --------------------------------------------------------------------------

  /**
   * Generate cleanup plan (AI-assisted)
   */
  async generateCleanupPlan(
    sessionId: string,
    useAi = true
  ): Promise<KLCleanupPlanResponse> {
    return request<KLCleanupPlanResponse>(
      `/api/sessions/${sessionId}/cleanup/generate`,
      {
        method: 'POST',
        params: { use_ai: useAi },
      }
    );
  },

  /**
   * Get the cleanup plan for a session
   */
  async getCleanupPlan(sessionId: string): Promise<KLCleanupPlanResponse> {
    return request<KLCleanupPlanResponse>(`/api/sessions/${sessionId}/cleanup`);
  },

  /**
   * Decide on a cleanup item (keep/discard)
   */
  async decideCleanupItem(
    sessionId: string,
    blockId: string,
    data: KLCleanupDecisionRequest
  ): Promise<KLSuccessResponse> {
    return request<KLSuccessResponse>(
      `/api/sessions/${sessionId}/cleanup/decide/${blockId}`,
      {
        method: 'POST',
        body: data,
      }
    );
  },

  /**
   * Approve the cleanup plan
   */
  async approveCleanupPlan(sessionId: string): Promise<KLSuccessResponse> {
    return request<KLSuccessResponse>(
      `/api/sessions/${sessionId}/cleanup/approve`,
      {
        method: 'POST',
      }
    );
  },

  // --------------------------------------------------------------------------
  // Routing Plan
  // --------------------------------------------------------------------------

  /**
   * Generate routing plan (AI-assisted)
   */
  async generateRoutingPlan(
    sessionId: string,
    useAi = true,
    useCandidateFinder = true
  ): Promise<KLRoutingPlanResponse> {
    return request<KLRoutingPlanResponse>(
      `/api/sessions/${sessionId}/plan/generate`,
      {
        method: 'POST',
        params: { use_ai: useAi, use_candidate_finder: useCandidateFinder },
      }
    );
  },

  /**
   * Get the routing plan for a session
   */
  async getRoutingPlan(sessionId: string): Promise<KLRoutingPlanResponse> {
    return request<KLRoutingPlanResponse>(`/api/sessions/${sessionId}/plan`);
  },

  /**
   * Select a destination for a block
   */
  async selectDestination(
    sessionId: string,
    blockId: string,
    data: KLSelectDestinationRequest
  ): Promise<KLSuccessResponse> {
    return request<KLSuccessResponse>(
      `/api/sessions/${sessionId}/plan/select/${blockId}`,
      {
        method: 'POST',
        body: data,
      }
    );
  },

  /**
   * Reject a block (exclude from routing)
   */
  async rejectBlock(sessionId: string, blockId: string): Promise<KLSuccessResponse> {
    return request<KLSuccessResponse>(
      `/api/sessions/${sessionId}/plan/reject-block/${blockId}`,
      {
        method: 'POST',
      }
    );
  },

  /**
   * Approve the routing plan
   */
  async approveRoutingPlan(sessionId: string): Promise<KLSuccessResponse> {
    return request<KLSuccessResponse>(`/api/sessions/${sessionId}/plan/approve`, {
      method: 'POST',
    });
  },

  // --------------------------------------------------------------------------
  // Execution
  // --------------------------------------------------------------------------

  /**
   * Execute the session (write blocks to library)
   */
  async executeSession(sessionId: string): Promise<KLExecuteResponse> {
    return request<KLExecuteResponse>(`/api/sessions/${sessionId}/execute`, {
      method: 'POST',
    });
  },

  // --------------------------------------------------------------------------
  // Library
  // --------------------------------------------------------------------------

  /**
   * Get the library structure (categories and files)
   */
  async getLibrary(): Promise<KLLibraryStructureResponse> {
    return request<KLLibraryStructureResponse>('/api/library');
  },

  /**
   * Get metadata for a library file
   */
  async getFileMetadata(filePath: string): Promise<KLLibraryFileResponse> {
    return request<KLLibraryFileResponse>(`/api/library/files/${encodePath(filePath)}`);
  },

  /**
   * Get content of a library file
   */
  async getFileContent(filePath: string): Promise<KLLibraryFileContentResponse> {
    return request<KLLibraryFileContentResponse>(
      `/api/library/files/${encodePath(filePath)}/content`
    );
  },

  /**
   * Search library files by keyword
   */
  async searchKeyword(query: string): Promise<KLLibrarySearchResponse> {
    return request<KLLibrarySearchResponse>('/api/library/search', {
      params: { query },
    });
  },

  /**
   * Trigger library indexing
   */
  async indexLibrary(): Promise<KLIndexResponse> {
    return request<KLIndexResponse>('/api/library/index', {
      method: 'POST',
    });
  },

  /**
   * Get library index stats
   */
  async getIndexStats(): Promise<KLIndexResponse> {
    return request<KLIndexResponse>('/api/library/index/stats');
  },

  // --------------------------------------------------------------------------
  // Query (Semantic Search & RAG)
  // --------------------------------------------------------------------------

  /**
   * Semantic search in the library
   */
  async semanticSearch(data: KLSemanticSearchRequest): Promise<KLSemanticSearchResponse> {
    return request<KLSemanticSearchResponse>('/api/query/search', {
      method: 'POST',
      body: data,
    });
  },

  /**
   * Ask the library a question (RAG)
   */
  async ask(data: KLAskRequest): Promise<KLAskResponse> {
    return request<KLAskResponse>('/api/query/ask', {
      method: 'POST',
      body: data,
    });
  },

  /**
   * List all conversations
   */
  async getConversations(): Promise<KLConversationListResponse> {
    return request<KLConversationListResponse>('/api/query/conversations');
  },

  /**
   * Get a conversation by ID
   */
  async getConversation(conversationId: string): Promise<KLConversation> {
    return request<KLConversation>(`/api/query/conversations/${conversationId}`);
  },

  /**
   * Delete a conversation
   */
  async deleteConversation(conversationId: string): Promise<KLSuccessResponse> {
    return request<KLSuccessResponse>(`/api/query/conversations/${conversationId}`, {
      method: 'DELETE',
    });
  },

  // --------------------------------------------------------------------------
  // WebSocket Helpers
  // --------------------------------------------------------------------------

  /**
   * Get the WebSocket URL for session streaming
   */
  getSessionStreamUrl(sessionId: string): string {
    const base = getBaseUrl();
    // Convert http(s) to ws(s)
    const wsBase = base.replace(/^http/, 'ws');
    return `${wsBase}/api/sessions/${sessionId}/stream`;
  },

  /**
   * Open a WebSocket stream for a session
   *
   * @param sessionId - The session ID to stream
   * @param handlers - Event handlers for the stream
   * @returns Object with WebSocket instance and helper methods
   */
  openSessionStream(
    sessionId: string,
    handlers: {
      onEvent?: (event: KLStreamEvent) => void;
      onOpen?: () => void;
      onClose?: () => void;
      onError?: (error: Event) => void;
    } = {}
  ): {
    ws: WebSocket;
    send: (command: KLStreamCommandRequest) => void;
    close: () => void;
  } {
    const url = this.getSessionStreamUrl(sessionId);
    const ws = new WebSocket(url);

    ws.onopen = () => {
      handlers.onOpen?.();
    };

    ws.onclose = () => {
      handlers.onClose?.();
    };

    ws.onerror = (event) => {
      handlers.onError?.(event);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as KLStreamEvent;
        handlers.onEvent?.(data);
      } catch {
        // Malformed message - log in dev mode for debugging
        if (import.meta.env.DEV) {
          console.warn('[KL] Malformed WebSocket message:', event.data);
        }
      }
    };

    return {
      ws,
      send: (command: KLStreamCommandRequest) => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify(command));
        }
      },
      close: () => {
        ws.close();
      },
    };
  },

  /**
   * Send a user guidance message over WebSocket
   */
  sendUserMessage(ws: WebSocket, message: string): void {
    if (ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ command: 'user_message', message }));
    }
  },
};
