/**
 * Knowledge Library Session Stream Hook
 *
 * Manages WebSocket connection for real-time updates during Knowledge Library
 * session processing (cleanup planning, routing planning, etc.)
 *
 * Features:
 * - Automatic reconnection with exponential backoff
 * - Event accumulation for transcript display
 * - Question tracking for interactive Q&A flow
 * - Non-fatal disconnect handling (shows "disconnected" without global error)
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { knowledgeLibraryApi } from '@/lib/knowledge-library-api';
import type { KLTranscriptEntry } from '@/store/knowledge-library-store';
import type {
  KLStreamEvent,
  KLStreamCommand,
  KLStreamCommandRequest,
} from '@automaker/types';

// Re-export for consumers that import from this module
export type { KLTranscriptEntry };

/** Pending question from the backend */
export interface KLPendingQuestion {
  questionId: string;
  content: string;
  timestamp: string;
}

/** Hook return value */
export interface UseKLSessionStreamResult {
  /** Whether the WebSocket is connected */
  isConnected: boolean;
  /** Whether the stream is connecting (initial or reconnecting) */
  isConnecting: boolean;
  /** Accumulated events for transcript display */
  events: KLStreamEvent[];
  /** Formatted transcript entries */
  transcript: KLTranscriptEntry[];
  /** Pending questions from the backend */
  pendingQuestions: KLPendingQuestion[];
  /** Send a command to the WebSocket */
  send: (command: KLStreamCommand, options?: Partial<KLStreamCommandRequest>) => void;
  /** Send a user guidance message */
  sendUserMessage: (message: string) => void;
  /** Answer a pending question */
  answerQuestion: (questionId: string, answer: string) => void;
  /** Clear transcript (keeps connection) */
  clearTranscript: () => void;
  /** Manually reconnect */
  reconnect: () => void;
  /** Disconnect the stream */
  disconnect: () => void;
}

// ============================================================================
// Configuration
// ============================================================================

/** Initial delay before first reconnect attempt (1 second) */
const RECONNECT_INITIAL_DELAY = 1000;
/** Maximum delay between reconnect attempts (30 seconds) */
const RECONNECT_MAX_DELAY = 30000;
/** Exponential backoff multiplier for reconnection delays */
const RECONNECT_MULTIPLIER = 1.5;
/** Keep-alive ping interval (25 seconds, under typical 30s server timeout) */
const PING_INTERVAL = 25000;

/** Generate unique ID for transcript entries */
function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
}

export const resolveEventMessage = (event: KLStreamEvent): string | null => {
  if (event.data.message) return event.data.message;
  if (event.event_type === 'question' && event.data.question) {
    return event.data.question;
  }
  return null;
};

export const resolveQuestionPayload = (event: KLStreamEvent): KLPendingQuestion | null => {
  if (event.event_type !== 'question') return null;
  const questionId = event.data.question_id ?? event.data.id;
  if (!questionId) return null;
  const content = event.data.message ?? event.data.question ?? '';
  const timestamp = event.data.created_at ?? event.timestamp ?? new Date().toISOString();
  return {
    questionId,
    content,
    timestamp,
  };
};

export const buildAnswerPayload = (
  questionId: string,
  answer: string
): Pick<KLStreamCommandRequest, 'question_id' | 'answer'> => ({
  question_id: questionId,
  answer,
});

type ReconnectGuard = {
  enabled: boolean;
  sessionId: string | null | undefined;
  isMounted: boolean;
  allowReconnect: boolean;
  isCurrentConnection: boolean;
};

export const shouldScheduleReconnect = ({
  enabled,
  sessionId,
  isMounted,
  allowReconnect,
  isCurrentConnection,
}: ReconnectGuard): boolean =>
  isMounted && allowReconnect && isCurrentConnection && enabled && !!sessionId;

// ============================================================================
// Hook Implementation
// ============================================================================

/**
 * Manage WebSocket stream for a Knowledge Library session
 *
 * @param sessionId - The session ID to stream (null/undefined to disable)
 * @param enabled - Whether the stream should be active (default: true)
 */
export function useKLSessionStream(
  sessionId: string | null | undefined,
  enabled = true
): UseKLSessionStreamResult {
  // Connection state
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);

  // Event/transcript state
  const [events, setEvents] = useState<KLStreamEvent[]>([]);
  const [transcript, setTranscript] = useState<KLTranscriptEntry[]>([]);
  const [pendingQuestions, setPendingQuestions] = useState<KLPendingQuestion[]>([]);

  // Refs for WebSocket and reconnection
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const pingIntervalRef = useRef<number | null>(null);
  const reconnectDelayRef = useRef(RECONNECT_INITIAL_DELAY);
  const mountedRef = useRef(true);
  const shouldReconnectRef = useRef(true);
  const connectionIdRef = useRef(0);

  // Convert event to transcript entry
  const eventToTranscript = useCallback(
    (event: KLStreamEvent): KLTranscriptEntry | null => {
      const message = resolveEventMessage(event);
      if (!message) return null;

      let role: KLTranscriptEntry['role'] = 'system';
      let level: KLTranscriptEntry['level'] = 'info';

      // Determine role and level based on event type
      switch (event.event_type) {
        case 'error':
          level = 'error';
          break;
        case 'user_message':
          role = 'user';
          break;
        case 'question':
          role = 'assistant';
          break;
        case 'cleanup_ready':
        case 'routing_ready':
          role = 'assistant';
          break;
        case 'progress':
        case 'cleanup_started':
        case 'routing_started':
        case 'candidate_search':
          role = 'system';
          break;
        default:
          role = 'system';
      }

      return {
        id: generateId(),
        role,
        content: message,
        timestamp: event.timestamp || new Date().toISOString(),
        eventType: event.event_type,
        level,
      };
    },
    []
  );

  // Handle incoming event
  const handleEvent = useCallback(
    (event: KLStreamEvent) => {
      if (!mountedRef.current) return;

      // Add to events
      setEvents((prev) => [...prev, event]);

      // Convert to transcript entry
      const entry = eventToTranscript(event);
      if (entry) {
        setTranscript((prev) => [...prev, entry]);
      }

      // Track questions
      const questionPayload = resolveQuestionPayload(event);
      if (questionPayload) {
        setPendingQuestions((prev) => [
          ...prev,
          questionPayload,
        ]);
      }
    },
    [eventToTranscript]
  );

  // Cleanup function
  const cleanup = useCallback(() => {
    shouldReconnectRef.current = false;
    if (reconnectTimeoutRef.current) {
      window.clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (pingIntervalRef.current) {
      window.clearInterval(pingIntervalRef.current);
      pingIntervalRef.current = null;
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setIsConnected(false);
    setIsConnecting(false);
  }, []);

  // Connect function
  const connect = useCallback(() => {
    if (!sessionId || !enabled || !mountedRef.current) return;

    shouldReconnectRef.current = true;
    const connectionId = connectionIdRef.current + 1;
    connectionIdRef.current = connectionId;

    // Clean up existing connection
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    setIsConnecting(true);

    const stream = knowledgeLibraryApi.openSessionStream(sessionId, {
      onOpen: () => {
        if (!mountedRef.current || connectionId !== connectionIdRef.current) return;
        setIsConnected(true);
        setIsConnecting(false);
        reconnectDelayRef.current = RECONNECT_INITIAL_DELAY;

        // Start ping interval
        pingIntervalRef.current = window.setInterval(() => {
          if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({ command: 'ping' }));
          }
        }, PING_INTERVAL);
      },

      onClose: () => {
        if (!mountedRef.current || connectionId !== connectionIdRef.current) return;
        setIsConnected(false);
        setIsConnecting(false);

        // Clear ping interval
        if (pingIntervalRef.current) {
          window.clearInterval(pingIntervalRef.current);
          pingIntervalRef.current = null;
        }

        // Schedule reconnect if still enabled
        if (
          shouldScheduleReconnect({
            enabled,
            sessionId,
            isMounted: mountedRef.current,
            allowReconnect: shouldReconnectRef.current,
            isCurrentConnection: connectionId === connectionIdRef.current,
          })
        ) {
          reconnectTimeoutRef.current = window.setTimeout(() => {
            reconnectDelayRef.current = Math.min(
              reconnectDelayRef.current * RECONNECT_MULTIPLIER,
              RECONNECT_MAX_DELAY
            );
            connect();
          }, reconnectDelayRef.current);
        }
      },

      onError: () => {
        // onClose will handle reconnection
      },

      onEvent: (event) => {
        if (connectionId !== connectionIdRef.current) return;
        handleEvent(event);
      },
    });

    wsRef.current = stream.ws;
  }, [sessionId, enabled, handleEvent]);

  // Send command
  const send = useCallback(
    (command: KLStreamCommand, options?: Partial<KLStreamCommandRequest>) => {
      if (wsRef.current?.readyState !== WebSocket.OPEN) {
        if (import.meta.env.DEV) {
          console.warn('[KL] Cannot send - WebSocket not open');
        }
        return;
      }
      wsRef.current.send(JSON.stringify({ command, ...options }));
    },
    []
  );

  // Send user message
  const sendUserMessage = useCallback(
    (message: string) => {
      // Optimistically add to transcript
      setTranscript((prev) => [
        ...prev,
        {
          id: generateId(),
          role: 'user',
          content: message,
          timestamp: new Date().toISOString(),
          level: 'info',
        },
      ]);

      // Send over WebSocket
      send('user_message', { message });
    },
    [send]
  );

  // Answer question
  const answerQuestion = useCallback(
    (questionId: string, answer: string) => {
      // Remove from pending questions
      setPendingQuestions((prev) => prev.filter((q) => q.questionId !== questionId));

      // Add answer to transcript
      setTranscript((prev) => [
        ...prev,
        {
          id: generateId(),
          role: 'user',
          content: answer,
          timestamp: new Date().toISOString(),
          level: 'info',
        },
      ]);

      // Send answer
      send('answer', buildAnswerPayload(questionId, answer));
    },
    [send]
  );

  // Clear transcript
  const clearTranscript = useCallback(() => {
    setEvents([]);
    setTranscript([]);
    setPendingQuestions([]);
  }, []);

  // Manual reconnect
  const reconnect = useCallback(() => {
    cleanup();
    reconnectDelayRef.current = RECONNECT_INITIAL_DELAY;
    connect();
  }, [cleanup, connect]);

  // Disconnect
  const disconnect = useCallback(() => {
    cleanup();
  }, [cleanup]);

  // Effect: Connect when sessionId changes
  useEffect(() => {
    mountedRef.current = true;

    if (sessionId && enabled) {
      connect();
    }

    return () => {
      mountedRef.current = false;
      cleanup();
    };
  }, [sessionId, enabled, connect, cleanup]);

  return {
    isConnected,
    isConnecting,
    events,
    transcript,
    pendingQuestions,
    send,
    sendUserMessage,
    answerQuestion,
    clearTranscript,
    reconnect,
    disconnect,
  };
}
