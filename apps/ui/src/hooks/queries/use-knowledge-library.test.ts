import { describe, expect, it } from 'vitest';

import { KnowledgeLibraryError } from '@/lib/knowledge-library-api';
import { getKLHealthRefetchIntervalMs } from './use-knowledge-library';

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
