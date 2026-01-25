/**
 * Session Workflow Hook
 *
 * Orchestrates the session phases for the Knowledge Library Input Mode:
 * 1. File staging (pre-upload)
 * 2. Session creation + file upload
 * 3. Cleanup plan generation + review
 * 4. Routing plan generation + review
 * 5. Execution
 *
 * This hook manages:
 * - WebSocket connection for streaming events
 * - Session state transitions
 * - Transcript accumulation
 * - User message sending
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { queryKeys } from '@/lib/query-keys';
import { useKnowledgeLibraryStore, type KLTranscriptEntry } from '@/store/knowledge-library-store';
import {
  useKLCreateSession,
  useKLUploadSource,
  useKLSession,
  useKLCleanupPlan,
  useKLRoutingPlan,
  useKLApproveCleanupPlan,
  useKLApproveRoutingPlan,
  useKLExecuteSession,
  useKLDeleteSession,
} from '@/hooks/queries/use-knowledge-library';
import { knowledgeLibraryApi } from '@/lib/knowledge-library-api';
import type { KLStreamEvent, KLStreamCommand, KLSessionPhase } from '@automaker/types';

// ============================================================================
// Types
// ============================================================================

export type WorkflowState =
  | 'idle' // No session, waiting for file
  | 'file_staged' // File selected, ready to start
  | 'creating_session' // Creating session + uploading
  | 'cleanup_generating' // Waiting for cleanup plan
  | 'cleanup_review' // User reviewing cleanup decisions
  | 'routing_generating' // Waiting for routing plan
  | 'routing_review' // User reviewing routing decisions
  | 'ready_to_execute' // All decisions made, ready to execute
  | 'executing' // Execution in progress
  | 'completed' // Session completed
  | 'error'; // Error state

export const getAutoGenerationCommand = (workflowState: WorkflowState): KLStreamCommand | null => {
  if (workflowState === 'cleanup_generating' || workflowState === 'cleanup_review') {
    return 'generate_cleanup';
  }
  if (workflowState === 'routing_generating' || workflowState === 'routing_review') {
    return 'generate_routing';
  }
  return null;
};

const WEBSOCKET_OPEN_TIMEOUT_MS = 10000;

type ReconnectDecision = {
  allowReconnect: boolean;
  sessionId: string | null | undefined;
  latestSessionId: string | null | undefined;
  workflowState: WorkflowState;
};

export const shouldReconnectSession = ({
  allowReconnect,
  sessionId,
  latestSessionId,
  workflowState,
}: ReconnectDecision): boolean => {
  if (!allowReconnect) return false;
  if (!sessionId || sessionId !== latestSessionId) return false;
  return workflowState !== 'completed' && workflowState !== 'error';
};

export interface PendingQuestion {
  id: string;
  question: string;
  createdAt: string;
}

export interface WorkflowActions {
  /** Stage a file for upload */
  stageFile: (file: File) => void;
  /** Clear the staged file */
  clearStagedFile: () => void;
  /** Start a new session with the staged file */
  startSession: () => Promise<void>;
  /** Send a user message (guidance or answer) */
  sendMessage: (message: string) => void;
  /** Answer a pending question */
  answerQuestion: (questionId: string, answer: string) => void;
  /** Approve the cleanup plan and proceed to routing */
  approveCleanup: () => Promise<void>;
  /** Approve the routing plan and proceed to execution */
  approveRouting: () => Promise<void>;
  /** Execute the session */
  execute: () => Promise<void>;
  /** Cancel the current session */
  cancelSession: () => Promise<void>;
  /** Select an existing session */
  selectSession: (sessionId: string) => void;
  /** Reset the workflow to idle */
  reset: () => void;
}

export interface UseSessionWorkflowResult {
  /** Current workflow state */
  workflowState: WorkflowState;
  /** Current session ID (if any) */
  sessionId: string | null;
  /** Session data from server */
  session: ReturnType<typeof useKLSession>['data'];
  /** Cleanup plan data */
  cleanupPlan: ReturnType<typeof useKLCleanupPlan>['data'];
  /** Routing plan data */
  routingPlan: ReturnType<typeof useKLRoutingPlan>['data'];
  /** Staged file info */
  stagedFile: { file: File; fileName: string } | null;
  /** Session transcript entries */
  transcript: KLTranscriptEntry[];
  /** Pending questions from the AI */
  pendingQuestions: PendingQuestion[];
  /** Whether WebSocket is connected */
  isConnected: boolean;
  /** Loading states */
  isLoading: {
    creating: boolean;
    uploading: boolean;
    cleanup: boolean;
    routing: boolean;
    executing: boolean;
  };
  /** Error message if any */
  error: string | null;
  /** Available actions */
  actions: WorkflowActions;
}

// ============================================================================
// Hook Implementation
// ============================================================================

export function useSessionWorkflow(): UseSessionWorkflowResult {
  const queryClient = useQueryClient();

  // Store state
  const {
    currentSessionId,
    setCurrentSessionId,
    stagedUpload,
    stageUpload,
    clearStagedUpload,
    sessionTranscript,
    addTranscriptEntry,
    clearTranscript,
    draftUserMessage,
    setDraftUserMessage,
    resetSession,
  } = useKnowledgeLibraryStore();

  // Local state
  const [workflowState, setWorkflowState] = useState<WorkflowState>('idle');
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pendingQuestions, setPendingQuestions] = useState<PendingQuestion[]>([]);

  // Mutations
  const createSessionMutation = useKLCreateSession();
  const uploadSourceMutation = useKLUploadSource();
  const approveCleanupMutation = useKLApproveCleanupPlan(currentSessionId ?? '');
  const approveRoutingMutation = useKLApproveRoutingPlan(currentSessionId ?? '');
  const executeSessionMutation = useKLExecuteSession(currentSessionId ?? '');
  const deleteSessionMutation = useKLDeleteSession();

  // Queries
  const sessionQuery = useKLSession(currentSessionId ?? undefined);
  const cleanupPlanQuery = useKLCleanupPlan(currentSessionId ?? undefined);
  const routingPlanQuery = useKLRoutingPlan(currentSessionId ?? undefined);

  // WebSocket ref
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const connectionIdRef = useRef(0);
  const openPromiseRef = useRef<Promise<void> | null>(null);
  const activeSessionIdRef = useRef<string | null>(null);
  const latestSessionIdRef = useRef<string | null>(currentSessionId ?? null);
  const workflowStateRef = useRef<WorkflowState>(workflowState);
  const shouldReconnectRef = useRef(false);

  useEffect(() => {
    latestSessionIdRef.current = currentSessionId ?? null;
  }, [currentSessionId]);

  useEffect(() => {
    workflowStateRef.current = workflowState;
  }, [workflowState]);

  // ============================================================================
  // WebSocket Management
  // ============================================================================

  const handleStreamEvent = useCallback(
    (event: KLStreamEvent) => {
      const { event_type, data } = event;

      // Add message to transcript if present
      if (data.message) {
        addTranscriptEntry({
          id: `${event_type}-${Date.now()}`,
          role: event_type === 'error' ? 'system' : 'assistant',
          content: data.message,
          timestamp: event.timestamp ?? new Date().toISOString(),
          level: event_type === 'error' ? 'error' : 'info',
        });
      }

      // Handle specific event types
      switch (event_type) {
        case 'cleanup_started':
          setWorkflowState('cleanup_generating');
          break;

        case 'cleanup_ready':
          setWorkflowState('cleanup_review');
          // Refresh cleanup plan
          queryClient.invalidateQueries({
            queryKey: queryKeys.knowledgeLibrary.cleanupPlan(currentSessionId ?? ''),
          });
          queryClient.invalidateQueries({
            queryKey: queryKeys.knowledgeLibrary.session(currentSessionId ?? ''),
          });
          break;

        case 'routing_started':
          setWorkflowState('routing_generating');
          break;

        case 'routing_ready':
          setWorkflowState('routing_review');
          // Refresh routing plan
          queryClient.invalidateQueries({
            queryKey: queryKeys.knowledgeLibrary.routingPlan(currentSessionId ?? ''),
          });
          queryClient.invalidateQueries({
            queryKey: queryKeys.knowledgeLibrary.session(currentSessionId ?? ''),
          });
          break;

        case 'question':
          // AI is asking a question
          if (data.id && data.question) {
            const questionId = data.id;
            const questionText = data.question;
            setPendingQuestions((prev) => [
              ...prev,
              {
                id: questionId,
                question: questionText,
                createdAt: data.created_at ?? new Date().toISOString(),
              },
            ]);
          }
          break;

        case 'error':
          setError(data.message ?? 'An error occurred');
          setWorkflowState('error');
          break;

        default:
          // Handle progress and other events
          break;
      }
    },
    [addTranscriptEntry, currentSessionId, queryClient]
  );

  const clearReconnectTimeout = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
  }, []);

  const closeWebSocketConnection = useCallback(
    (allowReconnect: boolean) => {
      shouldReconnectRef.current = allowReconnect;
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      openPromiseRef.current = null;
      activeSessionIdRef.current = null;
      clearReconnectTimeout();
    },
    [clearReconnectTimeout]
  );

  const handleWebSocketMessage = useCallback(
    (event: MessageEvent) => {
      try {
        const streamEvent: KLStreamEvent = JSON.parse(event.data);
        handleStreamEvent(streamEvent);
      } catch (err) {
        console.error('Failed to parse WebSocket message:', err);
      }
    },
    [handleStreamEvent]
  );

  const scheduleReconnect = useCallback(
    (sessionId: string, reconnect: () => void) => {
      if (
        !shouldReconnectSession({
          allowReconnect: shouldReconnectRef.current,
          sessionId,
          latestSessionId: latestSessionIdRef.current,
          workflowState: workflowStateRef.current,
        })
      ) {
        return;
      }
      clearReconnectTimeout();
      reconnectTimeoutRef.current = setTimeout(reconnect, 3000);
    },
    [clearReconnectTimeout]
  );

  const createOpenPromise = useCallback(
    (
      ws: WebSocket,
      sessionId: string,
      connectionId: number,
      reconnect: () => void
    ): Promise<void> => {
      let didOpen = false;
      let settled = false;
      let timeoutId: ReturnType<typeof setTimeout> | null = null;

      const settleOnce = (fn: () => void) => {
        if (settled) return;
        settled = true;
        if (timeoutId) {
          clearTimeout(timeoutId);
        }
        openPromiseRef.current = null;
        fn();
      };

      return new Promise((resolve, reject) => {
        timeoutId = setTimeout(() => {
          if (connectionId !== connectionIdRef.current) return;
          settleOnce(() => reject(new Error('WebSocket connection timed out')));
        }, WEBSOCKET_OPEN_TIMEOUT_MS);

        ws.onopen = () => {
          if (connectionId !== connectionIdRef.current) return;
          didOpen = true;
          setIsConnected(true);
          addTranscriptEntry({
            id: `system-${Date.now()}`,
            role: 'system',
            content: 'Connected to session stream',
            timestamp: new Date().toISOString(),
            level: 'info',
          });
          settleOnce(resolve);
        };

        ws.onmessage = handleWebSocketMessage;

        ws.onerror = (event) => {
          if (connectionId !== connectionIdRef.current) return;
          console.error('WebSocket error:', event);
          setError('Connection error occurred');
          if (!didOpen) {
            settleOnce(() => reject(new Error('WebSocket connection failed')));
          }
        };

        ws.onclose = () => {
          if (connectionId !== connectionIdRef.current) return;
          setIsConnected(false);
          wsRef.current = null;
          activeSessionIdRef.current = null;
          if (!didOpen) {
            settleOnce(() => reject(new Error('WebSocket closed before opening')));
          }
          scheduleReconnect(sessionId, reconnect);
        };
      });
    },
    [addTranscriptEntry, handleWebSocketMessage, scheduleReconnect]
  );

  const getOpenPromise = (sessionId: string): Promise<void> | null => {
    if (!wsRef.current || activeSessionIdRef.current !== sessionId) return null;
    if (wsRef.current.readyState === WebSocket.OPEN) {
      return Promise.resolve();
    }
    return openPromiseRef.current;
  };

  const connectWebSocket = useCallback(
    (sessionId: string): Promise<void> => {
      if (!sessionId) {
        return Promise.reject(new Error('Missing session id for WebSocket connection'));
      }

      const existingPromise = getOpenPromise(sessionId);
      if (existingPromise) {
        return existingPromise;
      }

      connectionIdRef.current += 1;
      const connectionId = connectionIdRef.current;
      closeWebSocketConnection(true);

      const wsUrl = knowledgeLibraryApi.getSessionStreamUrl(sessionId);
      const ws = new WebSocket(wsUrl);
      activeSessionIdRef.current = sessionId;

      const reconnect = () => {
        void connectWebSocket(sessionId).catch((err) => {
          setError(err instanceof Error ? err.message : 'Failed to reconnect to session stream');
        });
      };

      const openPromise = createOpenPromise(ws, sessionId, connectionId, reconnect);
      openPromiseRef.current = openPromise;
      wsRef.current = ws;

      return openPromise;
    },
    [closeWebSocketConnection, createOpenPromise]
  );

  const sendWebSocketCommand = useCallback(
    (command: KLStreamCommand, payload?: Record<string, unknown>) => {
      if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
        console.warn('WebSocket not connected, cannot send command');
        return;
      }

      wsRef.current.send(
        JSON.stringify({
          command,
          ...payload,
        })
      );
    },
    []
  );

  // ============================================================================
  // Workflow State Derivation
  // ============================================================================

  // Derive workflow state from session phase
  useEffect(() => {
    if (!currentSessionId) {
      setWorkflowState(stagedUpload ? 'file_staged' : 'idle');
      return;
    }

    const phase = sessionQuery.data?.phase as KLSessionPhase | undefined;
    if (!phase) return;

    switch (phase) {
      case 'initialized':
      case 'parsing':
        setWorkflowState('creating_session');
        break;
      case 'cleanup_plan_ready':
        setWorkflowState('cleanup_review');
        break;
      case 'routing_plan_ready':
        setWorkflowState('routing_review');
        break;
      case 'awaiting_approval':
      case 'ready_to_execute':
        setWorkflowState('ready_to_execute');
        break;
      case 'executing':
      case 'verifying':
        setWorkflowState('executing');
        break;
      case 'completed':
        setWorkflowState('completed');
        break;
      case 'error':
        setWorkflowState('error');
        break;
    }
  }, [currentSessionId, sessionQuery.data?.phase, stagedUpload]);

  // Connect WebSocket when session is created
  useEffect(() => {
    if (currentSessionId && !wsRef.current) {
      void connectWebSocket(currentSessionId).catch((err) => {
        setError(err instanceof Error ? err.message : 'Failed to connect to session stream');
      });
    }

    return () => {
      clearReconnectTimeout();
    };
  }, [currentSessionId, connectWebSocket, clearReconnectTimeout]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      closeWebSocketConnection(false);
    };
  }, [closeWebSocketConnection]);

  // ============================================================================
  // Actions
  // ============================================================================

  const stageFile = useCallback(
    (file: File) => {
      stageUpload(file);
      setWorkflowState('file_staged');
      setError(null);
    },
    [stageUpload]
  );

  const clearStagedFile = useCallback(() => {
    clearStagedUpload();
    setWorkflowState('idle');
  }, [clearStagedUpload]);

  const selectSession = useCallback(
    (sessionId: string) => {
      if (!sessionId || sessionId === currentSessionId) return;

      closeWebSocketConnection(false);

      resetSession();
      setError(null);
      setPendingQuestions([]);
      setWorkflowState('cleanup_generating');
      setCurrentSessionId(sessionId);
    },
    [currentSessionId, resetSession, setCurrentSessionId, closeWebSocketConnection]
  );

  const startSession = useCallback(async () => {
    if (!stagedUpload) {
      setError('No file staged for upload');
      return;
    }

    try {
      setWorkflowState('creating_session');
      setError(null);

      // Create session
      const session = await createSessionMutation.mutateAsync({});
      setCurrentSessionId(session.id);

      // Upload file
      await uploadSourceMutation.mutateAsync({ sessionId: session.id, file: stagedUpload.file });
      clearStagedUpload();

      // Connect WebSocket
      await connectWebSocket(session.id);

      // Trigger cleanup generation
      sendWebSocketCommand('generate_cleanup');

      addTranscriptEntry({
        id: `upload-${Date.now()}`,
        role: 'system',
        content: `Uploaded "${stagedUpload.fileName}" - analyzing content...`,
        timestamp: new Date().toISOString(),
        level: 'info',
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start session');
      setWorkflowState('file_staged');
    }
  }, [
    stagedUpload,
    createSessionMutation,
    uploadSourceMutation,
    setCurrentSessionId,
    clearStagedUpload,
    connectWebSocket,
    sendWebSocketCommand,
    addTranscriptEntry,
  ]);

  const sendMessage = useCallback(
    (message: string) => {
      if (!message.trim()) return;

      // Add to transcript immediately (optimistic)
      addTranscriptEntry({
        id: `user-${Date.now()}`,
        role: 'user',
        content: message,
        timestamp: new Date().toISOString(),
      });

      // Send via WebSocket
      sendWebSocketCommand('user_message', { message });
      setDraftUserMessage('');
    },
    [addTranscriptEntry, sendWebSocketCommand, setDraftUserMessage]
  );

  const answerQuestion = useCallback(
    (questionId: string, answer: string) => {
      if (!answer.trim()) return;

      // Add to transcript
      addTranscriptEntry({
        id: `answer-${Date.now()}`,
        role: 'user',
        content: `Answer: ${answer}`,
        timestamp: new Date().toISOString(),
      });

      // Send via WebSocket
      sendWebSocketCommand('answer', { question_id: questionId, answer });

      // Remove from pending
      setPendingQuestions((prev) => {
        const next = prev.filter((q) => q.id !== questionId);
        if (next.length === 0) {
          const command = getAutoGenerationCommand(workflowState);
          if (command) {
            sendWebSocketCommand(command);
            setWorkflowState(
              command === 'generate_cleanup' ? 'cleanup_generating' : 'routing_generating'
            );
            addTranscriptEntry({
              id: `auto-${Date.now()}`,
              role: 'system',
              content:
                command === 'generate_cleanup'
                  ? 'All questions answered. Regenerating cleanup plan...'
                  : 'All questions answered. Regenerating routing plan...',
              timestamp: new Date().toISOString(),
              level: 'info',
            });
          }
        }
        return next;
      });
    },
    [addTranscriptEntry, sendWebSocketCommand, workflowState]
  );

  const approveCleanup = useCallback(async () => {
    if (!currentSessionId) return;

    try {
      await approveCleanupMutation.mutateAsync();
      setWorkflowState('routing_generating');

      // Trigger routing generation
      sendWebSocketCommand('generate_routing');

      addTranscriptEntry({
        id: `cleanup-approved-${Date.now()}`,
        role: 'system',
        content: 'Cleanup plan approved. Generating routing suggestions...',
        timestamp: new Date().toISOString(),
        level: 'info',
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to approve cleanup');
    }
  }, [currentSessionId, approveCleanupMutation, sendWebSocketCommand, addTranscriptEntry]);

  const approveRouting = useCallback(async () => {
    if (!currentSessionId) return;

    try {
      await approveRoutingMutation.mutateAsync();
      setWorkflowState('ready_to_execute');

      addTranscriptEntry({
        id: `routing-approved-${Date.now()}`,
        role: 'system',
        content: 'Routing plan approved. Ready to execute.',
        timestamp: new Date().toISOString(),
        level: 'info',
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to approve routing');
    }
  }, [currentSessionId, approveRoutingMutation, addTranscriptEntry]);

  const execute = useCallback(async () => {
    if (!currentSessionId) return;

    try {
      setWorkflowState('executing');

      addTranscriptEntry({
        id: `executing-${Date.now()}`,
        role: 'system',
        content: 'Executing session - writing blocks to library...',
        timestamp: new Date().toISOString(),
        level: 'info',
      });

      const result = await executeSessionMutation.mutateAsync();

      addTranscriptEntry({
        id: `executed-${Date.now()}`,
        role: 'system',
        content: `Execution complete! ${result.blocks_written}/${result.total_blocks} blocks written.`,
        timestamp: new Date().toISOString(),
        level: 'info',
      });

      setWorkflowState('completed');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Execution failed');
      setWorkflowState('error');
    }
  }, [currentSessionId, executeSessionMutation, addTranscriptEntry]);

  const cancelSession = useCallback(async () => {
    if (currentSessionId) {
      try {
        await deleteSessionMutation.mutateAsync(currentSessionId);
      } catch (err) {
        console.error('Failed to delete session:', err);
      }
    }

    // Close WebSocket
    closeWebSocketConnection(false);

    // Reset state
    resetSession();
    setWorkflowState('idle');
    setError(null);
    setPendingQuestions([]);
    setIsConnected(false);
  }, [currentSessionId, deleteSessionMutation, resetSession, closeWebSocketConnection]);

  const reset = useCallback(() => {
    // Close WebSocket
    closeWebSocketConnection(false);

    // Reset state
    resetSession();
    setWorkflowState('idle');
    setError(null);
    setPendingQuestions([]);
    setIsConnected(false);
  }, [resetSession, closeWebSocketConnection]);

  // ============================================================================
  // Return Value
  // ============================================================================

  return {
    workflowState,
    sessionId: currentSessionId,
    session: sessionQuery.data,
    cleanupPlan: cleanupPlanQuery.data,
    routingPlan: routingPlanQuery.data,
    stagedFile: stagedUpload,
    transcript: sessionTranscript,
    pendingQuestions,
    isConnected,
    isLoading: {
      creating: createSessionMutation.isPending,
      uploading: uploadSourceMutation.isPending,
      cleanup: approveCleanupMutation.isPending,
      routing: approveRoutingMutation.isPending,
      executing: executeSessionMutation.isPending,
    },
    error,
    actions: {
      stageFile,
      clearStagedFile,
      startSession,
      sendMessage,
      answerQuestion,
      approveCleanup,
      approveRouting,
      execute,
      cancelSession,
      selectSession,
      reset,
    },
  };
}
