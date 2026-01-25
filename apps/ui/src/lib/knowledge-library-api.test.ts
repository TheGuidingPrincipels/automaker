import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { knowledgeLibraryApi } from './knowledge-library-api';

const originalFetch = globalThis.fetch;

describe('knowledgeLibraryApi', () => {
  beforeEach(() => {
    const mockResponse = {
      ok: true,
      status: 200,
      statusText: 'OK',
      json: async () => ({ content: 'ok', path: 'tech/auth.md' }),
    } as Response;

    globalThis.fetch = vi.fn().mockResolvedValue(mockResponse);
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it('strips leading slashes from file paths when requesting content', async () => {
    await knowledgeLibraryApi.getFileContent('/tech/auth.md');

    const fetchMock = globalThis.fetch as ReturnType<typeof vi.fn>;
    const [url] = fetchMock.mock.calls[0] ?? [];

    expect(url).toBe('http://localhost:8001/api/library/files/tech/auth.md/content');
  });
});
