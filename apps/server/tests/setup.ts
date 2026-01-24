/**
 * Vitest global setup file
 * Runs before each test file
 *
 * This file serves as the test configuration (equivalent to pytest's conftest.py)
 * providing shared fixtures, mocks, and utilities for all tests.
 */

import { vi, beforeEach, afterEach } from 'vitest';

// Set test environment variables
process.env.NODE_ENV = 'test';
process.env.DATA_DIR = '/tmp/test-data';
// Database URL for tests - uses a test-specific SQLite database
process.env.DATABASE_URL = 'file:/tmp/test-data/test-automaker.db';
// Disable self-signup restrictions in tests
process.env.AUTOMAKER_ALLOW_SELF_SIGNUP = 'true';

// Reset all mocks before each test
beforeEach(() => {
  vi.clearAllMocks();
});

// Clean up after each test
afterEach(() => {
  vi.restoreAllMocks();
});
