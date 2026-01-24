# Phase 1: User Foundation

> **Status**: Planning (Revised to match current repo)
> **Estimated Duration**: 1–2 weeks
> **Prerequisites**: None
> **Blocks**: Phases 2, 3, 4

## Objective

Establish the foundational user identity system that all other phases depend on, **without breaking the current “API key → session cookie/token” auth model** that Automaker uses today.

After this phase:

- Users can register and log in with **email/password**
- All authenticated requests have **user context** (`req.user`)
- Sessions are **bound to user IDs** (including a `system` user for legacy/Electron flows)
- User data is stored in a **SQLite database** (Prisma)
- Existing functionality continues to work (API key login, Electron mode, existing UI bootstrap)

## Current System Reality (must stay compatible)

These are the key current behaviors this phase must align with:

- Server auth supports **API key** (`X-API-Key`) and **session token/cookie** (`X-Session-Token`, `automaker_session`) (`apps/server/src/lib/auth.ts`).
- Sessions are persisted to `{DATA_DIR}/.sessions` for survival across restarts.
- `/api/auth/*` routes are mounted **before** the global `authMiddleware` (`apps/server/src/index.ts`).
- The UI login flow is an API-key-based state machine (`apps/ui/src/components/views/login-view.tsx`) calling `login(apiKey)` (`apps/ui/src/lib/http-api-client.ts`) and bootstrap auth uses `verifySession()` (`apps/ui/src/routes/__root.tsx`).
- The codebase is **ESM/NodeNext**: local imports must use `.js` extensions in TS/ESM output.

## Locked Decisions (to make this phase 100% executable)

These decisions remove ambiguity for implementation and downstream phases:

1. **Keep legacy API key auth** (Electron + existing web flow) and map it to a real user:
   - API key authentication corresponds to the **System user** (`user.id === 'system'`).
2. **Add email/password auth** (new web-mode primary path):
   - `/api/auth/register` and `/api/auth/login` support email/password.
   - UI defaults to email/password mode, but keeps an explicit “Legacy API key” option.
3. **Self-signup is disabled by default in production**:
   - `AUTOMAKER_ALLOW_SELF_SIGNUP=true` must be set to allow `/register` on a deployed/shared server.
   - In development, you may enable it by default (recommended).
4. **Session persistence remains file-backed in Phase 1**:
   - Keep `{DATA_DIR}/.sessions` as the source of truth to preserve restart behavior.
   - Extend the stored session payload to include `userId`.
   - Do **not** introduce a DB-backed sessions table in Phase 1.
5. **`req.user` is populated before handlers run**:
   - The auth middleware must `await` the DB lookup and attach `req.user` before calling `next()`.
   - No “fire-and-forget” user hydration.
6. **Prepare for OAuth in Phase 4 now**:
   - `User.passwordHash` must be nullable to support OAuth-only accounts.

## Technical Specification

### 1. Database (Prisma + SQLite)

**Why Prisma here?** Phase 2/4 already plan Prisma schema changes; Phase 1 establishes the initial schema/migrations.

**Prisma schema location (monorepo-aligned)**:

- **Create**: `apps/server/prisma/schema.prisma`

**SQLite DB file location**:

- `{DATA_DIR}/automaker.db`
- Reminder: when running `npm run dev:server` the working directory is typically `apps/server`, so the default `{DATA_DIR}` is `apps/server/data` unless overridden.

**Schema v1 (Phase 1)**

```prisma
datasource db {
  provider = "sqlite"
  url      = env("DATABASE_URL")
}

generator client {
  provider = "prisma-client-js"
}

model User {
  /// Use a stable id string. `system` is reserved for legacy/Electron auth.
  id           String   @id @default(uuid())
  email        String   @unique
  /// Nullable for OAuth-only accounts (Phase 4)
  passwordHash String?
  name         String

  createdAt    DateTime @default(now())
  updatedAt    DateTime @updatedAt
  lastLoginAt  DateTime?

  @@map("users")
}
```

### 2. Shared Types (DTOs only; no Express types in @automaker/types)

**Create**: `libs/types/src/user.ts`

```ts
export type UserId = string;

export interface PublicUser {
  id: UserId;
  email: string;
  name: string;
}

export interface RegisterUserInput {
  email: string;
  password: string;
  name: string;
}

export interface LoginWithEmailInput {
  email: string;
  password: string;
}

export type LoginResult =
  | { success: true; user: PublicUser; token: string }
  | { success: false; error: string };
```

**Modify**: `libs/types/src/index.ts`

- Add: `export * from './user.js';` (note the `.js` extension)

### 3. Server: Database bootstrap

**Create**: `apps/server/src/lib/database.ts`

Key requirements:

- **Async-only** filesystem usage (no `fs.*Sync`)
- Use PrismaClient runtime URL override via `datasourceUrl` (supported in Prisma ≥ 5.2; Prisma v6 docs confirm).
- Fail fast with a clear error if DB cannot be opened.

Implementation shape:

```ts
import { PrismaClient } from '@prisma/client';
import path from 'path';
import fs from 'fs/promises';

let prisma: PrismaClient | null = null;

export const getDataDir = (): string => process.env.DATA_DIR || './data';

export const getDatabasePath = (): string => path.join(getDataDir(), 'automaker.db');

export const getDatabaseUrl = (): string => `file:${getDatabasePath()}`;

export const initializeDatabase = async (): Promise<PrismaClient> => {
  if (prisma) return prisma;
  await fs.mkdir(getDataDir(), { recursive: true });

  prisma = new PrismaClient({
    datasourceUrl: getDatabaseUrl(),
    log: process.env.NODE_ENV === 'development' ? ['error', 'warn'] : ['error'],
  });

  await prisma.$connect();
  return prisma;
};

export const getPrisma = (): PrismaClient => {
  if (!prisma) throw new Error('Database not initialized');
  return prisma;
};

export const closeDatabase = async (): Promise<void> => {
  if (!prisma) return;
  await prisma.$disconnect();
  prisma = null;
};
```

### 4. Server: Express request typing (server-local)

Do **not** export `AuthenticatedRequest` from `@automaker/types`.

**Create**: `apps/server/src/types/express.d.ts`

```ts
import 'express-serve-static-core';
import type { PublicUser } from '@automaker/types';

declare module 'express-serve-static-core' {
  interface Request {
    user?: PublicUser;
    userId?: string;
  }
}
```

### 5. Server: User service

**Create**: `apps/server/src/services/user-service.ts`

Requirements:

- Normalize email (`trim().toLowerCase()`)
- Validate password length (recommend `>= 12` for production; allow `>= 8` minimum if you prefer)
- Hash with bcrypt (rounds: `12`)
- Support OAuth-only users by allowing `passwordHash === null`
- Provide `ensureSystemUser()` for backward compatibility

Methods:

- `ensureSystemUser(): Promise<void>`
- `createUser(input: RegisterUserInput): Promise<PublicUser>`
- `authenticateUser(input: LoginWithEmailInput): Promise<PublicUser | null>`
- `getPublicUserById(id: string): Promise<PublicUser | null>`

### 6. Server: Auth + sessions (bind to users, keep file persistence)

**Modify**: `apps/server/src/lib/auth.ts`

#### 6.1 Session payload format (backward compatible)

Current persisted sessions are:

```ts
Map<string, { createdAt: number; expiresAt: number }>;
```

New persisted sessions become:

```ts
interface SessionData {
  userId: string;
  createdAt: number;
  expiresAt: number;
}
```

Backward compatibility rule:

- If an old session entry is loaded (no `userId`), treat it as `{ userId: 'system', ... }` and re-save in the new format.

#### 6.2 Async-only auth initialization

Replace module-load `ensureApiKey()` + `loadSessions()` with an explicit initializer:

**Add**: `export const initializeAuth = async (): Promise<void> => { ... }`

- Ensures API key exists (env → file → generate+write)
- Loads sessions from `{DATA_DIR}/.sessions`
- Must be called once during server bootstrap **before** `logAuthInfo()` and before listening.

#### 6.3 Session creation + validation API (required for downstream phases)

Update session APIs:

- `createSession(userId: string): Promise<string>`
- `validateSession(token: string): { valid: boolean; userId?: string; errorType?: 'invalid_session' | 'expired_session' }`
- `invalidateSession(token: string): Promise<void>`

#### 6.4 Auth context + middleware behavior

Update `checkAuthentication(...)` to return:

- `authenticated: true | false`
- `method: 'api_key' | 'session' | 'none'`
- `userId` when authenticated (`'system'` for API key auth; real userId for sessions)
- `errorType` for failure reporting

Update `authMiddleware` to:

- Be `async`
- On success:
  - set `req.userId = userId`
  - load `req.user` via `UserService.getPublicUserById(userId)` and **await** it
  - if the user is missing (e.g., DB wiped), respond `401` and invalidate the session token if applicable

### 7. Server: Auth routes (add register/email login; keep legacy API key login)

**Modify**: `apps/server/src/routes/auth/index.ts`

To keep unit tests consistent with existing route patterns, split into handler files:

- **Create**:
  - `apps/server/src/routes/auth/routes/register.ts`
  - `apps/server/src/routes/auth/routes/login.ts`
  - `apps/server/src/routes/auth/routes/me.ts`
  - (optionally keep `status.ts`, `token.ts`, `logout.ts` as separate handlers too)

#### 7.1 POST `/api/auth/register`

Body: `{ email, password, name }`

Behavior:

- If `process.env.AUTOMAKER_ALLOW_SELF_SIGNUP !== 'true'` and `NODE_ENV === 'production'`:
  - `403 { success:false, error:'Self-signup disabled' }`
- Validate inputs; return `400` for missing/invalid
- Create user (fails with `409` if email exists)
- Create session bound to the new user
- Set cookie (`automaker_session`) and return token for header-based auth

Response (success):

```json
{ "success": true, "user": { "id": "...", "email": "...", "name": "..." }, "token": "..." }
```

#### 7.2 POST `/api/auth/login`

Support two mutually exclusive payloads:

1. Legacy API key login (existing behavior):

```json
{ "apiKey": "..." }
```

- Validate API key
- Create session for `userId='system'`
- Return `{ success:true, token }` (optionally also return `user` for system)

2. Email/password login:

```json
{ "email": "...", "password": "..." }
```

- Authenticate
- Create session for that user
- Return `{ success:true, user, token }`

Rate limiting:

- Keep existing per-IP limiter, but apply to **both** API key and email/password login attempts (separately tracked counters recommended).

#### 7.3 GET `/api/auth/me`

Implementation detail:

- Because `/api/auth` is mounted before global auth middleware, the route must protect itself:
  - `router.get('/me', authMiddleware, handler)`

Response:

```json
{ "success": true, "user": { "id": "...", "email": "...", "name": "..." } }
```

### 8. Server bootstrap sequence (must be deterministic)

**Modify**: `apps/server/src/index.ts`

Required ordering:

1. Load env (`dotenv/config`) (already)
2. Set/normalize `DATA_DIR` (already)
3. `await initializeAuth()` (new)
4. `await initializeDatabase()` (new)
5. `await userService.ensureSystemUser()` (new)
6. `logAuthInfo()` (existing, but must run after initializeAuth)
7. Start HTTP server listening

Notes:

- Agent service initialization and other non-auth critical services can still run in the background as today, but Phase 1 auth/user flows must not.

### 9. UI: Auth store (add user)

**Modify**: `apps/ui/src/store/auth-store.ts`

- Add `user: PublicUser | null`
- Add actions: `setUser(user)` and ensure `resetAuth()` clears user.

### 10. UI: HTTP client (add register/email login/me)

**Modify**: `apps/ui/src/lib/http-api-client.ts`

- Add:
  - `registerWithEmail(email, password, name): Promise<LoginResult>`
  - `loginWithEmail(email, password): Promise<LoginResult>`
  - `getCurrentUser(): Promise<{ success: true; user: PublicUser } | null>`
- On successful login/register, call `setSessionToken(token)` (same behavior as API key login today).

### 11. UI: Login view (support both modes)

**Modify**: `apps/ui/src/components/views/login-view.tsx`

Requirements:

- Keep the existing reducer-based flow, but add a mode switch:
  - **Email/Password** (default)
  - **Legacy API key**
- Email/password mode supports:
  - Login and register (toggle)
  - Shows validation errors inline
- On success:
  - `useAuthStore.setAuthState({ isAuthenticated:true, authChecked:true })`
  - `useAuthStore.setUser(user)` (when available)

### 12. UI: Bootstrap user hydration (persist across refresh)

**Modify**: `apps/ui/src/routes/__root.tsx`

- After a valid session is verified and settings are loaded, call `getCurrentUser()` and populate `useAuthStore.user`.

### 13. UI: Show user info somewhere real (minimal Phase 1 UX)

**Modify**: `apps/ui/src/components/views/settings-view/account/account-section.tsx`

- Display the current user’s `name` + `email` (if present) above the logout button.
- This satisfies “UI can display current user identity” without needing a new header design.

## Dependencies / Commands (workspace-aligned)

From repo root:

- Install (pin exact versions; keep `prisma` and `@prisma/client` versions identical):
  - `npm i -w apps/server prisma @prisma/client bcrypt`
  - `npm i -D -w apps/server @types/bcrypt`
- Initialize Prisma (run from `apps/server` so files land in the right workspace):
  - `cd apps/server && npx prisma init --datasource-provider sqlite`
  - Move/ensure schema path is `apps/server/prisma/schema.prisma`
- Create migration:
  - `cd apps/server && DATABASE_URL="file:./data/automaker.db" npx prisma migrate dev --name init_users`

## Testing Checklist (aligned with existing vitest patterns)

### Update existing tests

- [ ] Update `apps/server/tests/unit/lib/auth.test.ts` for:
  - `createSession(userId)`
  - `validateSession()` return shape
  - Backward-compatible `.sessions` load behavior (old format → system user)

### New unit tests

- [ ] `apps/server/tests/unit/services/user-service.test.ts`:
  - create user (hash stored, public user returned)
  - duplicate email rejected (409 path via route handler)
  - authenticate success/failure
  - OAuth-only user (`passwordHash=null`) cannot email/password login

### Route handler tests (recommended structure)

- [ ] `apps/server/tests/unit/routes/auth/register.test.ts`
- [ ] `apps/server/tests/unit/routes/auth/login.test.ts`
- [ ] `apps/server/tests/unit/routes/auth/me.test.ts`

Test approach:

- For **unit** route tests, mock `UserService` + auth/session helpers (same pattern as other route tests).
- Add a small **integration** test later only if needed; keep Phase 1 fast and deterministic.

### UI/E2E

- [ ] User can register (dev) and then login
- [ ] Two different browsers can be logged in as two different users
- [ ] Settings > Account shows current user identity
- [ ] Logout clears auth + user state
- [ ] Legacy API key login still works (web mode compatibility)

## Rollback Plan

1. Remove Prisma artifacts:
   - Delete `apps/server/prisma/`
   - Remove Prisma dependencies from `apps/server/package.json`
2. Delete DB file:
   - Delete `{DATA_DIR}/automaker.db`
3. Revert `apps/server/src/lib/auth.ts` session payload changes
4. Revert UI changes:
   - `apps/ui/src/store/auth-store.ts`
   - `apps/ui/src/components/views/login-view.tsx`
   - `apps/ui/src/lib/http-api-client.ts`

## Success Criteria

Phase 1 is complete when:

1. User can register (when allowed) and log in with email/password
2. Existing API key login still works (and maps to `system` user)
3. Sessions survive server restart and remain bound to a userId
4. All authenticated API requests have `req.user` populated
5. UI shows the current user identity (at least in Settings > Account)
6. Two users can be logged in simultaneously in different browsers

## Notes for Downstream Phases

### Phase 2 (Per-User Credentials)

- Use `req.user.id` to scope per-user credential storage.
- Treat `req.user.id === 'system'` as “global/system credentials”.

### Phase 3 (Knowledge Hub Sync)

- Use `req.user.id` for attribution fields (`createdBy`, `updatedBy`).
- If WebSockets need identity, extend WS connection tokens to include `userId` (Phase 1 can store it; Phase 3 can consume it).

### Phase 4 (OAuth)

- OAuth users will have `passwordHash = null`.
- OAuth login must create sessions via `createSession(userId)` just like email/password.
