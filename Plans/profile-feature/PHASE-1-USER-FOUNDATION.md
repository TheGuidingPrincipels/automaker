# Phase 1: User Foundation

> **Status**: Planning
> **Estimated Duration**: 1-2 weeks
> **Prerequisites**: None
> **Blocks**: Phases 2, 3, 4

## Objective

Establish the foundational user system that all other phases depend on. After this phase:

- Users can register and log in with email/password
- Sessions are bound to user IDs
- Authenticated requests have user context (`req.user`)
- User data is stored in SQLite database

## What This Phase DOES

- Creates User type definitions
- Sets up SQLite database with Prisma
- Implements user registration and login endpoints
- Binds session tokens to user IDs
- Adds user context to request middleware
- Updates frontend auth store with user object
- Adds basic registration/login UI

## What This Phase DOES NOT Do

| Excluded Feature               | Handled In |
| ------------------------------ | ---------- |
| Per-user API key storage       | Phase 2    |
| Per-user credential encryption | Phase 2    |
| Knowledge Hub real-time sync   | Phase 3    |
| Google/GitHub OAuth            | Phase 4    |
| User profile editing           | Phase 4    |
| Avatar upload                  | Phase 4    |

---

## Technical Specification

### 1. Database Schema

**File to Create**: `prisma/schema.prisma`

```prisma
datasource db {
  provider = "sqlite"
  url      = env("DATABASE_URL")
}

generator client {
  provider = "prisma-client-js"
}

model User {
  id            String    @id @default(uuid())
  email         String    @unique
  passwordHash  String
  name          String
  createdAt     DateTime  @default(now())
  updatedAt     DateTime  @updatedAt
  lastLoginAt   DateTime?

  sessions      Session[]

  @@map("users")
}

model Session {
  id        String   @id @default(uuid())
  token     String   @unique
  userId    String
  createdAt DateTime @default(now())
  expiresAt DateTime

  user      User     @relation(fields: [userId], references: [id], onDelete: Cascade)

  @@index([token])
  @@index([userId])
  @@map("sessions")
}
```

**Database Location**: `{DATA_DIR}/automaker.db`

### 2. User Type Definitions

**File to Create**: `libs/types/src/user.ts`

```typescript
/**
 * User entity stored in database
 */
export interface User {
  id: string;
  email: string;
  name: string;
  createdAt: string; // ISO 8601
  updatedAt: string; // ISO 8601
  lastLoginAt?: string; // ISO 8601
}

/**
 * User object returned to frontend (no sensitive data)
 */
export interface PublicUser {
  id: string;
  email: string;
  name: string;
}

/**
 * Registration request payload
 */
export interface RegisterUserInput {
  email: string;
  password: string;
  name: string;
}

/**
 * Login request payload
 */
export interface LoginInput {
  email: string;
  password: string;
}

/**
 * Login response
 */
export interface LoginResult {
  success: boolean;
  user?: PublicUser;
  token?: string;
  error?: string;
}

/**
 * Express request with user context
 */
export interface AuthenticatedRequest extends Request {
  user?: PublicUser;
}
```

**File to Modify**: `libs/types/src/index.ts`

- Add: `export * from './user';`

### 3. Database Service

**File to Create**: `apps/server/src/lib/database.ts`

```typescript
import { PrismaClient } from '@prisma/client';
import path from 'path';

let prisma: PrismaClient | null = null;

export function getDataDir(): string {
  return process.env.DATA_DIR || './data';
}

export function getDatabaseUrl(): string {
  const dataDir = getDataDir();
  return `file:${path.join(dataDir, 'automaker.db')}`;
}

export async function initializeDatabase(): Promise<PrismaClient> {
  if (prisma) return prisma;

  // Set DATABASE_URL for Prisma
  process.env.DATABASE_URL = getDatabaseUrl();

  prisma = new PrismaClient({
    log: process.env.NODE_ENV === 'development' ? ['query', 'error', 'warn'] : ['error'],
  });

  // Run migrations (in production, use prisma migrate deploy)
  // For development, this ensures schema is up to date
  await prisma.$connect();

  return prisma;
}

export function getPrisma(): PrismaClient {
  if (!prisma) {
    throw new Error('Database not initialized. Call initializeDatabase() first.');
  }
  return prisma;
}

export async function closeDatabase(): Promise<void> {
  if (prisma) {
    await prisma.$disconnect();
    prisma = null;
  }
}
```

### 4. User Service

**File to Create**: `apps/server/src/services/user-service.ts`

```typescript
import bcrypt from 'bcrypt';
import { getPrisma } from '../lib/database';
import type { User, PublicUser, RegisterUserInput } from '@automaker/types';

const BCRYPT_ROUNDS = 12;

export class UserService {
  /**
   * Create a new user with hashed password
   */
  async createUser(input: RegisterUserInput): Promise<PublicUser> {
    const prisma = getPrisma();

    // Check if email already exists
    const existing = await prisma.user.findUnique({
      where: { email: input.email.toLowerCase() },
    });

    if (existing) {
      throw new Error('Email already registered');
    }

    // Hash password
    const passwordHash = await bcrypt.hash(input.password, BCRYPT_ROUNDS);

    // Create user
    const user = await prisma.user.create({
      data: {
        email: input.email.toLowerCase(),
        passwordHash,
        name: input.name,
      },
    });

    return this.toPublicUser(user);
  }

  /**
   * Authenticate user with email/password
   */
  async authenticateUser(email: string, password: string): Promise<PublicUser | null> {
    const prisma = getPrisma();

    const user = await prisma.user.findUnique({
      where: { email: email.toLowerCase() },
    });

    if (!user) return null;

    const validPassword = await bcrypt.compare(password, user.passwordHash);
    if (!validPassword) return null;

    // Update last login time
    await prisma.user.update({
      where: { id: user.id },
      data: { lastLoginAt: new Date() },
    });

    return this.toPublicUser(user);
  }

  /**
   * Get user by ID
   */
  async getUserById(id: string): Promise<PublicUser | null> {
    const prisma = getPrisma();

    const user = await prisma.user.findUnique({
      where: { id },
    });

    return user ? this.toPublicUser(user) : null;
  }

  /**
   * Get user by email
   */
  async getUserByEmail(email: string): Promise<PublicUser | null> {
    const prisma = getPrisma();

    const user = await prisma.user.findUnique({
      where: { email: email.toLowerCase() },
    });

    return user ? this.toPublicUser(user) : null;
  }

  /**
   * Convert database user to public user (strip sensitive fields)
   */
  private toPublicUser(user: User & { passwordHash?: string }): PublicUser {
    return {
      id: user.id,
      email: user.email,
      name: user.name,
    };
  }
}

// Singleton instance
let userService: UserService | null = null;

export function getUserService(): UserService {
  if (!userService) {
    userService = new UserService();
  }
  return userService;
}
```

### 5. Session Management Changes

**File to Modify**: `apps/server/src/lib/auth.ts`

**Current Session Structure** (lines 33-37):

```typescript
// BEFORE
const validSessions = new Map<string, { createdAt: number; expiresAt: number }>();
```

**New Session Structure**:

```typescript
// AFTER
interface SessionData {
  userId: string;
  createdAt: number;
  expiresAt: number;
}

const validSessions = new Map<string, SessionData>();
```

**Changes to `createSession()`** (lines 211-220):

```typescript
// BEFORE
export async function createSession(): Promise<string> {
  const token = generateSessionToken();
  const now = Date.now();
  validSessions.set(token, {
    createdAt: now,
    expiresAt: now + SESSION_MAX_AGE_MS,
  });
  await saveSessions();
  return token;
}

// AFTER
export async function createSession(userId: string): Promise<string> {
  const prisma = getPrisma();
  const token = generateSessionToken();
  const now = new Date();
  const expiresAt = new Date(now.getTime() + SESSION_MAX_AGE_MS);

  // Store in database
  await prisma.session.create({
    data: {
      token,
      userId,
      createdAt: now,
      expiresAt,
    },
  });

  // Also cache in memory for fast validation
  validSessions.set(token, {
    userId,
    createdAt: now.getTime(),
    expiresAt: expiresAt.getTime(),
  });

  return token;
}
```

**Changes to `validateSession()`** (lines 226-238):

```typescript
// AFTER
export function validateSession(token: string): { valid: boolean; userId?: string } {
  const session = validSessions.get(token);

  if (!session) {
    return { valid: false };
  }

  if (Date.now() > session.expiresAt) {
    // Clean up expired session
    validSessions.delete(token);
    // Also delete from database (async, fire and forget)
    getPrisma()
      .session.delete({ where: { token } })
      .catch(() => {});
    return { valid: false };
  }

  return { valid: true, userId: session.userId };
}
```

**Add `getUserFromSession()`**:

```typescript
export function getUserFromSession(token: string): string | undefined {
  const result = validateSession(token);
  return result.valid ? result.userId : undefined;
}
```

### 6. Auth Middleware Changes

**File to Modify**: `apps/server/src/lib/auth.ts`

**Add to `checkAuthentication()` return type**:

```typescript
interface AuthResult {
  authenticated: boolean;
  userId?: string; // ADD THIS
  errorType?: 'no_auth' | 'invalid_session' | 'expired_session' | 'invalid_api_key';
}
```

**Update `authMiddleware()`** (lines 399-438):

```typescript
export function authMiddleware(req: AuthenticatedRequest, res: Response, next: NextFunction): void {
  const result = checkAuthentication(req.headers, req.query, req.cookies);

  if (!result.authenticated) {
    res.status(401).json({ error: 'Unauthorized', type: result.errorType });
    return;
  }

  // ATTACH USER CONTEXT TO REQUEST
  if (result.userId) {
    // Async lookup - but we have userId from session validation
    req.user = { id: result.userId } as PublicUser;

    // Optionally fetch full user (can be optimized with caching)
    getUserService()
      .getUserById(result.userId)
      .then((user) => {
        if (user) req.user = user;
      });
  }

  next();
}
```

### 7. Auth Routes Changes

**File to Modify**: `apps/server/src/routes/auth/index.ts`

**Add Registration Endpoint**:

```typescript
// POST /api/auth/register
router.post('/register', async (req: Request, res: Response) => {
  try {
    const { email, password, name } = req.body;

    // Validation
    if (!email || !password || !name) {
      return res.status(400).json({
        success: false,
        error: 'Email, password, and name are required',
      });
    }

    if (password.length < 8) {
      return res.status(400).json({
        success: false,
        error: 'Password must be at least 8 characters',
      });
    }

    const userService = getUserService();
    const user = await userService.createUser({ email, password, name });

    // Auto-login after registration
    const token = await createSession(user.id);

    // Set cookie
    res.cookie(SESSION_COOKIE_NAME, token, getSessionCookieOptions());

    return res.json({
      success: true,
      user,
      token,
    });
  } catch (error) {
    if (error.message === 'Email already registered') {
      return res.status(409).json({ success: false, error: error.message });
    }
    console.error('Registration error:', error);
    return res.status(500).json({ success: false, error: 'Registration failed' });
  }
});
```

**Update Login Endpoint** (modify existing):

```typescript
// POST /api/auth/login
router.post('/login', async (req: Request, res: Response) => {
  const { email, password, apiKey } = req.body;

  // Support both API key login (legacy) and email/password
  if (apiKey) {
    // Legacy API key login (for backward compatibility)
    if (!validateApiKey(apiKey)) {
      return res.status(401).json({ success: false, error: 'Invalid API key' });
    }
    // API key login doesn't bind to a user (system-level access)
    const token = await createSession('system');
    res.cookie(SESSION_COOKIE_NAME, token, getSessionCookieOptions());
    return res.json({ success: true, token });
  }

  // Email/password login
  if (!email || !password) {
    return res.status(400).json({
      success: false,
      error: 'Email and password are required',
    });
  }

  const userService = getUserService();
  const user = await userService.authenticateUser(email, password);

  if (!user) {
    return res.status(401).json({ success: false, error: 'Invalid credentials' });
  }

  const token = await createSession(user.id);
  res.cookie(SESSION_COOKIE_NAME, token, getSessionCookieOptions());

  return res.json({ success: true, user, token });
});
```

**Add Get Current User Endpoint**:

```typescript
// GET /api/auth/me
router.get('/me', async (req: AuthenticatedRequest, res: Response) => {
  if (!req.user) {
    return res.status(401).json({ error: 'Not authenticated' });
  }

  // Fetch fresh user data
  const userService = getUserService();
  const user = await userService.getUserById(req.user.id);

  if (!user) {
    return res.status(404).json({ error: 'User not found' });
  }

  return res.json({ user });
});
```

### 8. Server Initialization

**File to Modify**: `apps/server/src/index.ts`

**Add database initialization** (near startup):

```typescript
import { initializeDatabase, closeDatabase } from './lib/database';

// In server startup
async function startServer() {
  // Initialize database FIRST
  await initializeDatabase();
  console.log('Database initialized');

  // ... existing startup code ...
}

// In graceful shutdown
async function shutdown() {
  await closeDatabase();
  // ... existing shutdown code ...
}
```

### 9. Frontend Auth Store Changes

**File to Modify**: `apps/ui/src/store/auth-store.ts`

```typescript
import { create } from 'zustand';
import type { PublicUser } from '@automaker/types';

interface AuthState {
  authChecked: boolean;
  isAuthenticated: boolean;
  settingsLoaded: boolean;
  user: PublicUser | null; // ADD

  setAuthState: (state: Partial<AuthState>) => void;
  setUser: (user: PublicUser | null) => void; // ADD
  resetAuth: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  authChecked: false,
  isAuthenticated: false,
  settingsLoaded: false,
  user: null,

  setAuthState: (state) => set(state),

  setUser: (user) => set({ user }),

  resetAuth: () =>
    set({
      authChecked: false,
      isAuthenticated: false,
      settingsLoaded: false,
      user: null,
    }),
}));
```

### 10. Frontend Login View Changes

**File to Modify**: `apps/ui/src/components/views/login-view.tsx`

**Add state for login mode**:

```typescript
type AuthMode = 'apiKey' | 'emailPassword';

const [authMode, setAuthMode] = useState<AuthMode>('emailPassword');
const [email, setEmail] = useState('');
const [password, setPassword] = useState('');
const [name, setName] = useState('');
const [isRegistering, setIsRegistering] = useState(false);
```

**Add registration/login form** (simplified, actual implementation will be more detailed):

```tsx
{
  authMode === 'emailPassword' && (
    <form onSubmit={handleEmailPasswordSubmit}>
      {isRegistering && (
        <input
          type="text"
          placeholder="Name"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
      )}
      <input
        type="email"
        placeholder="Email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
      />
      <input
        type="password"
        placeholder="Password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
      />
      <button type="submit">{isRegistering ? 'Register' : 'Login'}</button>
      <button type="button" onClick={() => setIsRegistering(!isRegistering)}>
        {isRegistering ? 'Already have an account?' : 'Create account'}
      </button>
    </form>
  );
}
```

### 11. HTTP API Client Updates

**File to Modify**: `apps/ui/src/lib/http-api-client.ts`

**Add registration function**:

```typescript
export async function register(
  email: string,
  password: string,
  name: string
): Promise<LoginResult> {
  try {
    const response = await fetch(`${getApiBase()}/api/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ email, password, name }),
    });

    const data = await response.json();

    if (data.success && data.token) {
      setSessionToken(data.token);
    }

    return data;
  } catch (error) {
    return { success: false, error: 'Registration failed' };
  }
}

export async function loginWithEmail(email: string, password: string): Promise<LoginResult> {
  try {
    const response = await fetch(`${getApiBase()}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ email, password }),
    });

    const data = await response.json();

    if (data.success && data.token) {
      setSessionToken(data.token);
    }

    return data;
  } catch (error) {
    return { success: false, error: 'Login failed' };
  }
}

export async function getCurrentUser(): Promise<{ user: PublicUser } | null> {
  try {
    const response = await fetch(`${getApiBase()}/api/auth/me`, {
      headers: getAuthHeaders(),
      credentials: 'include',
    });

    if (!response.ok) return null;

    return await response.json();
  } catch {
    return null;
  }
}
```

---

## Package Dependencies

**Add to `apps/server/package.json`**:

```json
{
  "dependencies": {
    "@prisma/client": "^5.x",
    "bcrypt": "^5.x"
  },
  "devDependencies": {
    "prisma": "^5.x",
    "@types/bcrypt": "^5.x"
  }
}
```

---

## Migration Script

**File to Create**: `scripts/migrate-to-multi-user.ts`

```typescript
import { initializeDatabase, getPrisma } from '../apps/server/src/lib/database';

async function migrate() {
  await initializeDatabase();
  const prisma = getPrisma();

  console.log('Creating default system user...');

  // Create a "system" user for backward compatibility
  const systemUser = await prisma.user.upsert({
    where: { email: 'system@automaker.local' },
    update: {},
    create: {
      id: 'system',
      email: 'system@automaker.local',
      passwordHash: '', // Cannot login directly
      name: 'System',
    },
  });

  console.log('System user created:', systemUser.id);
  console.log('Migration complete.');
}

migrate().catch(console.error);
```

---

## Testing Checklist

### Unit Tests

- [ ] `UserService.createUser()` creates user with hashed password
- [ ] `UserService.createUser()` rejects duplicate email
- [ ] `UserService.authenticateUser()` validates correct password
- [ ] `UserService.authenticateUser()` rejects wrong password
- [ ] `createSession(userId)` creates session with user binding
- [ ] `validateSession()` returns userId for valid session
- [ ] `validateSession()` rejects expired session

### Integration Tests

- [ ] POST `/api/auth/register` creates user and returns session
- [ ] POST `/api/auth/login` with email/password returns user
- [ ] GET `/api/auth/me` returns current user
- [ ] Authenticated request has `req.user` populated
- [ ] Legacy API key login still works (backward compatibility)

### E2E Tests

- [ ] User can register via UI
- [ ] User can login via UI
- [ ] User sees their name in header after login
- [ ] Logout clears user state

---

## Rollback Plan

1. **Remove Prisma schema**: Delete `prisma/` folder
2. **Remove database file**: Delete `{DATA_DIR}/automaker.db`
3. **Revert auth.ts**: Restore original session structure
4. **Revert auth-store.ts**: Remove user field
5. **Revert login-view.tsx**: Remove email/password form

---

## Success Criteria

Phase 1 is complete when:

1. A new user can register with email/password
2. A registered user can log in
3. Authenticated requests include user context
4. Frontend displays logged-in user's name
5. All existing functionality still works (backward compatible)
6. At least 2 users can be logged in simultaneously (different browsers)

---

## Notes for Downstream Phases

### For Phase 2 (Per-User Credentials)

- Use `req.user.id` to scope credential storage
- Session userId is available from `validateSession(token).userId`

### For Phase 3 (Knowledge Hub Sync)

- Use `req.user.id` for `createdBy` attribution
- User object available on WebSocket via session lookup

### For Phase 4 (OAuth)

- OAuth users will also go through `createSession(userId)`
- User may not have password (OAuth-only accounts)
