import { describe, expect, it } from 'vitest';

import { KnowledgeLibraryError } from '@/lib/knowledge-library-api';
import { getKLHealthRefetchIntervalMs, isKLRoutingPlanPhase } from './use-knowledge-library';

describe('getKLHealthRefetchIntervalMs', () => {
  it('polls slowly when the service is healthy', () => {
    expect(
      getKLHealthRefetchIntervalMs({
        queryStatus: 'success',
        dataStatus: 'healthy',
        error: null,
      })
    ).toBe(30000);
  });

  it('polls quickly when the query is in error, even if cached data is healthy', () => {
    expect(
      getKLHealthRefetchIntervalMs({
        queryStatus: 'error',
        dataStatus: 'healthy',
        error: new KnowledgeLibraryError('offline', { isOfflineError: true }),
      })
    ).toBe(5000);
  });
});

describe('isKLRoutingPlanPhase', () => {
  it('returns false when the phase is unknown', () => {
    expect(isKLRoutingPlanPhase(undefined)).toBe(false);
  });

  it('returns false for cleanup phases', () => {
    expect(isKLRoutingPlanPhase('cleanup_plan_ready')).toBe(false);
    expect(isKLRoutingPlanPhase('parsing')).toBe(false);
  });

  it('returns true for routing and later phases', () => {
    expect(isKLRoutingPlanPhase('routing_plan_ready')).toBe(true);
    expect(isKLRoutingPlanPhase('awaiting_approval')).toBe(true);
    expect(isKLRoutingPlanPhase('completed')).toBe(true);
  });
});
