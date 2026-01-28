import { beforeEach, describe, expect, it, vi } from 'vitest';

const { useQueryMock } = vi.hoisted(() => ({
  useQueryMock: vi.fn((options: unknown) => options),
}));

vi.mock('@tanstack/react-query', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@tanstack/react-query')>();
  return {
    ...actual,
    useQuery: useQueryMock,
  };
});

import { useKLRoutingPlan } from './use-knowledge-library';

describe('useKLRoutingPlan', () => {
  beforeEach(() => {
    useQueryMock.mockClear();
  });

  it('enables the query when called without sessionPhase', () => {
    const result = useKLRoutingPlan('session-1');
    expect(useQueryMock).toHaveBeenCalledTimes(1);
    expect(result).toMatchObject({ enabled: true });
  });

  it('disables the query when a sessionPhase argument is provided but not routing-ready yet', () => {
    const result = useKLRoutingPlan('session-1', undefined);
    expect(useQueryMock).toHaveBeenCalledTimes(1);
    expect(result).toMatchObject({ enabled: false });
  });

  it('enables the query when the session is in a routing plan phase', () => {
    const result = useKLRoutingPlan('session-1', 'routing_plan_ready');
    expect(useQueryMock).toHaveBeenCalledTimes(1);
    expect(result).toMatchObject({ enabled: true });
  });

  it('disables the query when there is no sessionId', () => {
    const result = useKLRoutingPlan(undefined);
    expect(useQueryMock).toHaveBeenCalledTimes(1);
    expect(result).toMatchObject({ enabled: false });
  });
});
