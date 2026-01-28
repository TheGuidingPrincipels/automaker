import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import fs from 'fs/promises';

import {
  TEST_DATA_DIR,
  TEST_SESSIONS_PATH,
  cleanupTestSessions,
  ensureTestDataDir,
  readTestSessions,
  writeTestSessions,
} from '../../utils/database.js';

describe('tests/utils/database sessions helpers', () => {
  const originalDataDir = process.env.DATA_DIR;

  beforeEach(async () => {
    // Set DATA_DIR to test data directory so auth.ts loadSessions() reads from the right place
    process.env.DATA_DIR = TEST_DATA_DIR;
    await cleanupTestSessions();
  });

  afterEach(async () => {
    await cleanupTestSessions();
    // Restore original DATA_DIR
    if (originalDataDir === undefined) {
      delete process.env.DATA_DIR;
    } else {
      process.env.DATA_DIR = originalDataDir;
    }
  });

  it('writes .sessions using auth.ts on-disk format (array of [token, session] tuples)', async () => {
    const now = Date.now();
    const sessions = new Map([
      [
        'token-1',
        {
          createdAt: now,
          expiresAt: now + 60_000,
        },
      ],
    ]);

    await writeTestSessions(sessions);

    const raw = await fs.readFile(TEST_SESSIONS_PATH, 'utf-8');
    const parsed = JSON.parse(raw);

    expect(Array.isArray(parsed)).toBe(true);
    expect(parsed).toEqual([['token-1', { createdAt: now, expiresAt: now + 60_000 }]]);
  });

  it('produces a .sessions file loadable by auth.ts loadSessions()', async () => {
    const now = Date.now();
    const token = 'token-loadable';

    await writeTestSessions(
      new Map([
        [
          token,
          {
            createdAt: now,
            expiresAt: now + 60_000,
          },
        ],
      ])
    );

    vi.resetModules();
    const { validateSession } = await import('@/lib/auth.js');

    expect(validateSession(token)).toBe(true);
  });

  it('reads sessions written in auth.ts format', async () => {
    await ensureTestDataDir();

    const now = Date.now();
    const diskSessions = [['token-2', { createdAt: now, expiresAt: now + 60_000 }]];
    await fs.writeFile(TEST_SESSIONS_PATH, JSON.stringify(diskSessions), 'utf-8');

    const sessions = await readTestSessions();
    expect(Array.from(sessions.entries())).toEqual(diskSessions);
  });
});
