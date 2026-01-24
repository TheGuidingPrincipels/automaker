/**
 * User fixtures for testing
 * Provides test data for user-related tests (Phase 1: User Foundation)
 */

import type { PublicUser, RegisterUserInput, LoginWithEmailInput } from '@automaker/types';

/**
 * System user ID - used for legacy API key authentication
 */
export const SYSTEM_USER_ID = 'system';

/**
 * Test user fixtures
 */
export const testUsers = {
  /**
   * Standard test user for general testing
   */
  standard: {
    input: {
      email: 'test@example.com',
      password: 'securePassword123!',
      name: 'Test User',
    } as RegisterUserInput,
    expected: {
      email: 'test@example.com',
      name: 'Test User',
    },
  },

  /**
   * Admin test user
   */
  admin: {
    input: {
      email: 'admin@example.com',
      password: 'adminPassword456!',
      name: 'Admin User',
    } as RegisterUserInput,
    expected: {
      email: 'admin@example.com',
      name: 'Admin User',
    },
  },

  /**
   * Alternative test user for multi-user scenarios
   */
  alternate: {
    input: {
      email: 'alternate@example.com',
      password: 'alternatePass789!',
      name: 'Alternate User',
    } as RegisterUserInput,
    expected: {
      email: 'alternate@example.com',
      name: 'Alternate User',
    },
  },

  /**
   * System user (legacy API key auth)
   */
  system: {
    id: SYSTEM_USER_ID,
    email: 'system@automaker.local',
    name: 'System',
  } as PublicUser,
} as const;

/**
 * Invalid user inputs for negative testing
 */
export const invalidUserInputs = {
  /**
   * Email that's not a valid format
   */
  invalidEmail: {
    email: 'not-an-email',
    password: 'validPassword123!',
    name: 'Invalid Email User',
  } as RegisterUserInput,

  /**
   * Password that's too short
   */
  shortPassword: {
    email: 'short@example.com',
    password: 'short',
    name: 'Short Password User',
  } as RegisterUserInput,

  /**
   * Empty name
   */
  emptyName: {
    email: 'empty@example.com',
    password: 'validPassword123!',
    name: '',
  } as RegisterUserInput,

  /**
   * Missing required fields
   */
  missingFields: {
    email: '',
    password: '',
    name: '',
  } as RegisterUserInput,
} as const;

/**
 * Login credentials for testing
 */
export const loginCredentials = {
  valid: {
    email: testUsers.standard.input.email,
    password: testUsers.standard.input.password,
  } as LoginWithEmailInput,

  wrongPassword: {
    email: testUsers.standard.input.email,
    password: 'wrongPassword!',
  } as LoginWithEmailInput,

  nonExistentUser: {
    email: 'nonexistent@example.com',
    password: 'anyPassword123!',
  } as LoginWithEmailInput,
} as const;

/**
 * Create a mock PublicUser for testing
 */
export function createMockPublicUser(overrides: Partial<PublicUser> = {}): PublicUser {
  return {
    id: `user-${Date.now()}-${Math.random().toString(36).slice(2)}`,
    email: 'mock@example.com',
    name: 'Mock User',
    ...overrides,
  };
}

/**
 * Create multiple mock users for batch testing
 */
export function createMockPublicUsers(count: number): PublicUser[] {
  return Array.from({ length: count }, (_, i) =>
    createMockPublicUser({
      id: `user-${i + 1}`,
      email: `user${i + 1}@example.com`,
      name: `User ${i + 1}`,
    })
  );
}
