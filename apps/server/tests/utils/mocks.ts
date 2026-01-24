/**
 * Mock utilities for testing
 * Provides reusable mocks for common dependencies
 */

import { vi } from 'vitest';
import type { ChildProcess } from 'child_process';
import { EventEmitter } from 'events';
import type { PublicUser } from '@automaker/types';

/** 30 days in milliseconds */
const THIRTY_DAYS_MS = 30 * 24 * 60 * 60 * 1000;

/**
 * Mock Express context for authenticated request testing
 */
export interface MockExpressContext {
  req: {
    headers: Record<string, string>;
    body: Record<string, unknown>;
    params: Record<string, string>;
    query: Record<string, string>;
    cookies: Record<string, string>;
    user: PublicUser;
    userId: string;
  };
  res: {
    status: ReturnType<typeof vi.fn>;
    json: ReturnType<typeof vi.fn>;
    send: ReturnType<typeof vi.fn>;
    cookie: ReturnType<typeof vi.fn>;
    clearCookie: ReturnType<typeof vi.fn>;
  };
  next: ReturnType<typeof vi.fn>;
  user: PublicUser;
}

/**
 * Mock Express context for unauthenticated request testing
 */
export interface MockUnauthenticatedExpressContext {
  req: {
    headers: Record<string, string>;
    body: Record<string, unknown>;
    params: Record<string, string>;
    query: Record<string, string>;
    cookies: Record<string, string>;
  };
  res: {
    status: ReturnType<typeof vi.fn>;
    json: ReturnType<typeof vi.fn>;
    send: ReturnType<typeof vi.fn>;
    cookie: ReturnType<typeof vi.fn>;
    clearCookie: ReturnType<typeof vi.fn>;
  };
  next: ReturnType<typeof vi.fn>;
}

/**
 * Mock child process for subprocess testing
 */
export interface MockChildProcess extends EventEmitter {
  stdout: EventEmitter | null;
  stderr: EventEmitter | null;
  pid?: number;
  kill: ReturnType<typeof vi.fn>;
}

/**
 * Mock child_process.spawn for subprocess tests
 */
export function createMockChildProcess(options: {
  stdout?: string[];
  stderr?: string[];
  exitCode?: number | null;
  shouldError?: boolean;
}): ChildProcess {
  const { stdout = [], stderr = [], exitCode = 0, shouldError = false } = options;

  // Cast is acceptable here: we're extending EventEmitter with additional properties
  const mockProcess = new EventEmitter() as MockChildProcess;

  // Create mock stdout/stderr streams
  mockProcess.stdout = new EventEmitter();
  mockProcess.stderr = new EventEmitter();
  mockProcess.kill = vi.fn().mockReturnValue(true);

  // Simulate async output
  process.nextTick(() => {
    // Emit stdout lines
    for (const line of stdout) {
      mockProcess.stdout!.emit('data', Buffer.from(line + '\n'));
    }

    // Emit stderr lines
    for (const line of stderr) {
      mockProcess.stderr!.emit('data', Buffer.from(line + '\n'));
    }

    // Emit exit or error
    if (shouldError) {
      mockProcess.emit('error', new Error('Process error'));
    } else {
      mockProcess.emit('exit', exitCode);
    }
  });

  return mockProcess as unknown as ChildProcess;
}

/**
 * Mock fs/promises for file system tests
 */
export function createMockFs() {
  return {
    readFile: vi.fn(),
    writeFile: vi.fn(),
    mkdir: vi.fn(),
    access: vi.fn(),
    stat: vi.fn(),
  };
}

/**
 * Mock Express request/response/next for middleware tests
 */
export function createMockExpressContext(): MockUnauthenticatedExpressContext {
  const req: MockUnauthenticatedExpressContext['req'] = {
    headers: {},
    body: {},
    params: {},
    query: {},
    cookies: {},
  };

  const res: MockUnauthenticatedExpressContext['res'] = {
    status: vi.fn().mockReturnThis(),
    json: vi.fn().mockReturnThis(),
    send: vi.fn().mockReturnThis(),
    cookie: vi.fn().mockReturnThis(),
    clearCookie: vi.fn().mockReturnThis(),
  };

  const next = vi.fn();

  return { req, res, next };
}

/**
 * Mock AbortController for async operation tests
 */
export function createMockAbortController() {
  const controller = new AbortController();
  const originalAbort = controller.abort.bind(controller);
  controller.abort = vi.fn(originalAbort);
  return controller;
}

/**
 * Mock Claude SDK query function
 */
export function createMockClaudeQuery(messages: any[] = []) {
  return vi.fn(async function* ({ prompt, options }: any) {
    for (const msg of messages) {
      yield msg;
    }
  });
}

/**
 * Mock Express request with user context for authenticated request testing
 * This extends the basic mock to include user-related properties from Phase 1
 */
export function createMockAuthenticatedExpressContext(
  user?: Partial<PublicUser>
): MockExpressContext {
  const defaultUser: PublicUser = {
    id: 'test-user-id',
    email: 'test@example.com',
    name: 'Test User',
    ...user,
  };

  const req: MockExpressContext['req'] = {
    headers: {},
    body: {},
    params: {},
    query: {},
    cookies: {},
    user: defaultUser,
    userId: defaultUser.id,
  };

  const res: MockExpressContext['res'] = {
    status: vi.fn().mockReturnThis(),
    json: vi.fn().mockReturnThis(),
    send: vi.fn().mockReturnThis(),
    cookie: vi.fn().mockReturnThis(),
    clearCookie: vi.fn().mockReturnThis(),
  };

  const next = vi.fn();

  return { req, res, next, user: defaultUser };
}

/**
 * Mock Prisma client for database testing
 * Provides a mock implementation of PrismaClient for unit tests
 */
export function createMockPrismaClient() {
  const mockUser = {
    findUnique: vi.fn(),
    findFirst: vi.fn(),
    findMany: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    delete: vi.fn(),
    upsert: vi.fn(),
  };

  return {
    user: mockUser,
    $connect: vi.fn().mockResolvedValue(undefined),
    $disconnect: vi.fn().mockResolvedValue(undefined),
    $transaction: vi.fn(),
  };
}

/**
 * Mock UserService for route handler testing
 */
export function createMockUserService() {
  return {
    ensureSystemUser: vi.fn().mockResolvedValue(undefined),
    createUser: vi.fn(),
    authenticateUser: vi.fn(),
    getPublicUserById: vi.fn(),
    getUserByEmail: vi.fn(),
  };
}

/**
 * Mock bcrypt for password hashing tests
 */
export function createMockBcrypt() {
  return {
    hash: vi.fn().mockResolvedValue('mocked-hash'),
    compare: vi.fn().mockResolvedValue(true),
  };
}

/**
 * Mock session data with userId for Phase 1 auth testing
 */
export interface MockSessionData {
  userId: string;
  createdAt: number;
  expiresAt: number;
}

/**
 * Create mock session data
 * @param userId - User ID for the session
 * @param expiresInMs - Session expiration time in milliseconds
 * @param now - Optional fixed timestamp for deterministic testing (defaults to Date.now())
 */
export function createMockSessionData(
  userId: string = 'test-user-id',
  expiresInMs: number = THIRTY_DAYS_MS,
  now: number = Date.now()
): MockSessionData {
  return {
    userId,
    createdAt: now,
    expiresAt: now + expiresInMs,
  };
}

/**
 * Create legacy session data (pre-Phase 1 format for backward compatibility testing)
 * @param expiresInMs - Session expiration time in milliseconds
 * @param now - Optional fixed timestamp for deterministic testing (defaults to Date.now())
 */
export function createLegacySessionData(
  expiresInMs: number = THIRTY_DAYS_MS,
  now: number = Date.now()
): { createdAt: number; expiresAt: number } {
  return {
    createdAt: now,
    expiresAt: now + expiresInMs,
  };
}
