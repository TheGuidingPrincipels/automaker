import { describe, expect, it } from 'vitest';

import type { WorkflowState } from './use-session-workflow';
import { getAutoGenerationCommand, shouldReconnectSession } from './use-session-workflow';

describe('use-session-workflow helpers', () => {
  it('returns generate_cleanup during cleanup phases', () => {
    expect(getAutoGenerationCommand('cleanup_generating')).toBe('generate_cleanup');
    expect(getAutoGenerationCommand('cleanup_review')).toBe('generate_cleanup');
  });

  it('returns generate_routing during routing phases', () => {
    expect(getAutoGenerationCommand('routing_generating')).toBe('generate_routing');
    expect(getAutoGenerationCommand('routing_review')).toBe('generate_routing');
  });

  it('returns null when no auto-generation is needed', () => {
    const states: WorkflowState[] = [
      'idle',
      'file_staged',
      'creating_session',
      'ready_to_execute',
      'executing',
      'completed',
      'error',
    ];

    for (const state of states) {
      expect(getAutoGenerationCommand(state)).toBeNull();
    }
  });

  it('blocks reconnect when not allowed', () => {
    expect(
      shouldReconnectSession({
        allowReconnect: false,
        sessionId: 'session-1',
        latestSessionId: 'session-1',
        workflowState: 'cleanup_generating',
      })
    ).toBe(false);
  });

  it('blocks reconnect on session mismatch', () => {
    expect(
      shouldReconnectSession({
        allowReconnect: true,
        sessionId: 'session-1',
        latestSessionId: 'session-2',
        workflowState: 'cleanup_generating',
      })
    ).toBe(false);
  });

  it('blocks reconnect after terminal workflow states', () => {
    expect(
      shouldReconnectSession({
        allowReconnect: true,
        sessionId: 'session-1',
        latestSessionId: 'session-1',
        workflowState: 'completed',
      })
    ).toBe(false);

    expect(
      shouldReconnectSession({
        allowReconnect: true,
        sessionId: 'session-1',
        latestSessionId: 'session-1',
        workflowState: 'error',
      })
    ).toBe(false);
  });

  it('allows reconnect when session is current and active', () => {
    expect(
      shouldReconnectSession({
        allowReconnect: true,
        sessionId: 'session-1',
        latestSessionId: 'session-1',
        workflowState: 'cleanup_generating',
      })
    ).toBe(true);
  });
});
