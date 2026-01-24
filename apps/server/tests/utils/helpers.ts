/**
 * Test helper functions
 */

import type { PublicUser } from '@automaker/types';

/**
 * Collect all values from an async generator
 */
export async function collectAsyncGenerator<T>(gen: AsyncGenerator<T>): Promise<T[]> {
  const results: T[] = [];
  for await (const item of gen) {
    results.push(item);
  }
  return results;
}

/**
 * Wait for a condition to be true
 */
export async function waitFor(
  condition: () => boolean,
  timeout = 1000,
  interval = 10
): Promise<void> {
  const start = Date.now();
  while (!condition()) {
    if (Date.now() - start > timeout) {
      throw new Error('Timeout waiting for condition');
    }
    await new Promise((resolve) => setTimeout(resolve, interval));
  }
}

/**
 * Create a temporary directory for tests
 */
export function createTempDir(): string {
  return `/tmp/test-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

/**
 * Generate a unique email for testing
 */
export function generateTestEmail(prefix: string = 'test'): string {
  const uniqueId = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
  return `${prefix}-${uniqueId}@example.com`;
}

/**
 * Generate a unique user ID for testing
 */
export function generateTestUserId(): string {
  return `user-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

/**
 * Generate a secure-looking test password
 */
export function generateTestPassword(): string {
  return `TestPass${Date.now()}!`;
}

/**
 * Verify password meets minimum requirements
 * (for testing password validation logic)
 */
export function isValidPassword(password: string, minLength: number = 8): boolean {
  return password.length >= minLength;
}

/**
 * Normalize email for comparison (trim and lowercase)
 *
 * @note This is a basic normalization helper for MATCHING TEST DATA only.
 * It is NOT robust enough for production validation or sanitization.
 */
export function normalizeEmail(email: string): string {
  return email.trim().toLowerCase();
}

/**
 * Check if an object looks like a valid PublicUser
 *
 * @warning This type guard checks specific fields manually and must be
 * kept in sync with the PublicUser interface in @automaker/types.
 * If the PublicUser type acquires new required fields, this helper
 * must be updated to check for them.
 */
export function isValidPublicUser(obj: unknown): obj is PublicUser {
  if (!obj || typeof obj !== 'object') return false;
  const user = obj as Record<string, unknown>;
  return (
    typeof user.id === 'string' && typeof user.email === 'string' && typeof user.name === 'string'
  );
}

/**
 * Wait for async operation with timeout
 */
export async function withTimeout<T>(
  promise: Promise<T>,
  timeoutMs: number,
  timeoutMessage: string = 'Operation timed out'
): Promise<T> {
  let timeoutHandle: NodeJS.Timeout | undefined;

  const timeoutPromise = new Promise<never>((_, reject) => {
    timeoutHandle = setTimeout(() => reject(new Error(timeoutMessage)), timeoutMs);
  });

  try {
    return await Promise.race([promise, timeoutPromise]);
  } finally {
    if (timeoutHandle) {
      clearTimeout(timeoutHandle);
    }
  }
}
