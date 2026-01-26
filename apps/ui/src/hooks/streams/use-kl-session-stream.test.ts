import { describe, expect, it } from 'vitest';
import type { KLStreamEvent } from '@automaker/types';

import {
  buildAnswerPayload,
  resolveEventMessage,
  resolveQuestionPayload,
  shouldScheduleReconnect,
} from './use-kl-session-stream';

describe('useKLSessionStream helpers', () => {
  it('extracts question payload from backend fields', () => {
    const event = {
      event_type: 'question',
      session_id: 'session-1',
      data: {
        id: 'question-1',
        question: 'Where should this go?',
        created_at: '2024-01-01T00:00:00Z',
      },
    } as KLStreamEvent;

    expect(resolveQuestionPayload(event)).toEqual({
      questionId: 'question-1',
      content: 'Where should this go?',
      timestamp: '2024-01-01T00:00:00Z',
    });
  });

  it('falls back to legacy question fields', () => {
    const event = {
      event_type: 'question',
      session_id: 'session-1',
      timestamp: '2024-02-01T00:00:00Z',
      data: {
        question_id: 'question-legacy',
        message: 'Legacy prompt?',
      },
    } as KLStreamEvent;

    expect(resolveQuestionPayload(event)).toEqual({
      questionId: 'question-legacy',
      content: 'Legacy prompt?',
      timestamp: '2024-02-01T00:00:00Z',
    });
  });

  it('uses question text when building transcript messages', () => {
    const event = {
      event_type: 'question',
      session_id: 'session-1',
      data: {
        id: 'question-2',
        question: 'Need confirmation',
      },
    } as KLStreamEvent;

    expect(resolveEventMessage(event)).toBe('Need confirmation');
  });

  it('builds answer payload with answer field', () => {
    expect(buildAnswerPayload('question-3', 'Yes')).toEqual({
      question_id: 'question-3',
      answer: 'Yes',
    });
  });

  it('disallows reconnect when explicitly disabled', () => {
    expect(
      shouldScheduleReconnect({
        enabled: true,
        sessionId: 'session-1',
        isMounted: true,
        allowReconnect: false,
        isCurrentConnection: true,
      })
    ).toBe(false);
  });
});
