/**
 * User Types - Types for user authentication and management
 *
 * These types define the user entity and related authentication DTOs
 * for the AutoMaker application.
 */

// ============================================================================
// User Entity
// ============================================================================

/**
 * PublicUser - User information safe to expose in API responses
 *
 * Contains non-sensitive user fields that can be returned to clients.
 */
export interface PublicUser {
  /** Unique user identifier */
  id: string;
  /** User's email address */
  email: string;
  /** User's display name */
  name: string;
}

// ============================================================================
// Authentication DTOs
// ============================================================================

/**
 * RegisterUserInput - Input for user registration
 */
export interface RegisterUserInput {
  /** User's email address */
  email: string;
  /** User's password */
  password: string;
  /** User's display name */
  name: string;
}

/**
 * LoginWithEmailInput - Input for email/password login
 */
export interface LoginWithEmailInput {
  /** User's email address */
  email: string;
  /** User's password */
  password: string;
}
