/**
 * Database test utilities
 * Provides helpers for testing with Prisma and SQLite
 *
 * These utilities support the Phase 1 User Foundation testing requirements:
 * - Setting up isolated test databases
 * - Cleaning up test data between tests
 * - Providing test database connections
 */

import { vi } from 'vitest';
import path from 'path';
import fs from 'fs/promises';

/**
 * Test database configuration
 */
export const TEST_DATA_DIR = '/tmp/test-data';
export const TEST_DB_PATH = path.join(TEST_DATA_DIR, 'test-automaker.db');
export const TEST_DATABASE_URL = `file:${TEST_DB_PATH}`;

/**
 * Ensure the test data directory exists
 */
export async function ensureTestDataDir(): Promise<void> {
  await fs.mkdir(TEST_DATA_DIR, { recursive: true });
}

/**
 * Clean up test database file
 * Call this in afterEach or afterAll to ensure test isolation
 */
export async function cleanupTestDatabase(): Promise<void> {
  try {
    await fs.unlink(TEST_DB_PATH);
  } catch (error: any) {
    // Ignore if file doesn't exist
    if (error.code !== 'ENOENT') {
      throw error;
    }
  }
}

/**
 * Clean up entire test data directory
 */
export async function cleanupTestDataDir(): Promise<void> {
  try {
    await fs.rm(TEST_DATA_DIR, { recursive: true, force: true });
  } catch (error: any) {
    // Ignore errors during cleanup
    if (error.code !== 'ENOENT') {
      console.warn('Warning: Failed to clean up test data directory:', error.message);
    }
  }
}

/**
 * Create a unique test database path for parallel test execution
 */
export function createUniqueTestDbPath(): string {
  const uniqueId = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
  return path.join(TEST_DATA_DIR, `test-automaker-${uniqueId}.db`);
}

/**
 * Create a unique database URL for parallel test execution
 */
export function createUniqueTestDbUrl(): string {
  return `file:${createUniqueTestDbPath()}`;
}

/**
 * Mock database module for unit tests that don't need a real database
 * Use this when you want to isolate tests from the actual database layer
 */
export function mockDatabaseModule() {
  return {
    getDataDir: vi.fn().mockReturnValue(TEST_DATA_DIR),
    getDatabasePath: vi.fn().mockReturnValue(TEST_DB_PATH),
    getDatabaseUrl: vi.fn().mockReturnValue(TEST_DATABASE_URL),
    initializeDatabase: vi.fn().mockResolvedValue({
      $connect: vi.fn(),
      $disconnect: vi.fn(),
      user: {
        findUnique: vi.fn(),
        findFirst: vi.fn(),
        findMany: vi.fn(),
        create: vi.fn(),
        update: vi.fn(),
        delete: vi.fn(),
        upsert: vi.fn(),
      },
    }),
    getPrisma: vi.fn(),
    closeDatabase: vi.fn().mockResolvedValue(undefined),
  };
}

/**
 * Test sessions file path
 */
export const TEST_SESSIONS_PATH = path.join(TEST_DATA_DIR, '.sessions');

/**
 * Clean up test sessions file
 */
export async function cleanupTestSessions(): Promise<void> {
  try {
    await fs.unlink(TEST_SESSIONS_PATH);
  } catch (error: any) {
    if (error.code !== 'ENOENT') {
      throw error;
    }
  }
}

/**
 * Write test sessions data for session persistence testing
 */
export async function writeTestSessions(
  sessions: Map<string, { userId?: string; createdAt: number; expiresAt: number }>
): Promise<void> {
  await ensureTestDataDir();
  // Match the same on-disk format as src/lib/auth.ts:
  // JSON.stringify(Array.from(validSessions.entries()))
  const sessionsArray = Array.from(sessions.entries());
  await fs.writeFile(TEST_SESSIONS_PATH, JSON.stringify(sessionsArray), 'utf-8');
}

/**
 * Read test sessions data
 */
export async function readTestSessions(): Promise<
  Map<string, { userId?: string; createdAt: number; expiresAt: number }>
> {
  try {
    const data = await fs.readFile(TEST_SESSIONS_PATH, 'utf-8');
    const parsed: unknown = JSON.parse(data);
    if (!Array.isArray(parsed)) {
      throw new TypeError('Invalid .sessions format: expected an array of [token, session] tuples');
    }
    return new Map(
      parsed as Array<[string, { userId?: string; createdAt: number; expiresAt: number }]>
    );
  } catch (error: any) {
    if (error.code === 'ENOENT') {
      return new Map();
    }
    throw error;
  }
}
