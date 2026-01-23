# Automaker Authentication System

> Technical Documentation v1.0
> Last Updated: January 2026

## Overview

Automaker implements a sophisticated multi-provider, multi-mode authentication system designed for both security and flexibility. The system supports two runtime modes (Electron desktop and Web browser) with provider-specific authentication strategies.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Authentication Modes](#authentication-modes)
3. [Session Management](#session-management)
4. [Provider Authentication](#provider-authentication)
5. [Security Mechanisms](#security-mechanisms)
6. [API Endpoints](#api-endpoints)
7. [Frontend Integration](#frontend-integration)
8. [Configuration](#configuration)
9. [File Locations](#file-locations)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CLIENT LAYER                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐          │
│  │   Electron App  │    │   Web Browser   │    │   WebSocket     │          │
│  │  (X-API-Key)    │    │  (HTTP Cookie)  │    │   (wsToken)     │          │
│  └────────┬────────┘    └────────┬────────┘    └────────┬────────┘          │
└───────────┼──────────────────────┼──────────────────────┼───────────────────┘
            │                      │                      │
            ▼                      ▼                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           AUTH MIDDLEWARE                                    │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  authMiddleware() @ apps/server/src/lib/auth.ts:399                  │   │
│  │  - Validates X-API-Key header OR automaker_session cookie            │   │
│  │  - Bypasses: /api/auth/*, /api/health, /api/setup                    │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        PROVIDER AUTH LAYER                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────┐         ┌──────────────────────┐                  │
│  │   Anthropic/Claude   │         │    OpenAI/Codex      │                  │
│  │   - auth_token mode  │         │   - auth_token mode  │                  │
│  │   - api_key mode     │         │   - api_key mode     │                  │
│  └──────────────────────┘         └──────────────────────┘                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Core Components

| Component            | Location                                      | Purpose                      |
| -------------------- | --------------------------------------------- | ---------------------------- |
| Auth Middleware      | `apps/server/src/lib/auth.ts`                 | Session & API key validation |
| Provider Auth Config | `apps/server/src/lib/provider-auth-config.ts` | Multi-provider auth modes    |
| Auth Routes          | `apps/server/src/routes/auth/index.ts`        | Login/logout endpoints       |
| HTTP API Client      | `apps/ui/src/lib/http-api-client.ts`          | Frontend auth handling       |
| Auth Store           | `apps/ui/src/store/auth-store.ts`             | Frontend auth state          |

---

## Authentication Modes

### Server Access Authentication

The server requires authentication for API access. Two methods are supported:

#### 1. API Key Authentication (Electron/CLI)

```
Request Header: X-API-Key: <64-character-hex-string>
```

- API key auto-generated on first server start
- Stored at `{DATA_DIR}/.api-key`
- Can be overridden via `AUTOMAKER_API_KEY` env var
- Displayed in server console on startup (unless `AUTOMAKER_HIDE_API_KEY=true`)

#### 2. Session Cookie Authentication (Web Browser)

```
Cookie: automaker_session=<64-character-hex-token>
```

- Created on successful login via `/api/auth/login`
- HTTP-only, secure (in production), SameSite=Lax
- 30-day expiration
- Persisted to `{DATA_DIR}/.sessions`

### Provider Authentication Modes

Each AI provider supports two authentication modes:

| Mode         | Description              | Use Case                              |
| ------------ | ------------------------ | ------------------------------------- |
| `auth_token` | OAuth/CLI authentication | Subscription users (Claude Max, etc.) |
| `api_key`    | Direct API key           | Pay-per-use access                    |

#### auth_token Mode (Default)

- Uses CLI OAuth tokens (e.g., `claude login`, `codex login`)
- **API keys are completely ignored and blocked**
- Defense-in-depth: API key env vars cleared at 4 levels
- Ideal for subscription-based access

#### api_key Mode

- Uses traditional API keys
- Stored in `credentials.json` or environment variables
- Pay-per-use billing

### Mode Configuration Priority

```
1. Environment Variable (AUTOMAKER_ANTHROPIC_AUTH_MODE)
2. Legacy Env Var (AUTOMAKER_DISABLE_API_KEY_AUTH → maps to auth_token)
3. Settings File (anthropicAuthMode field)
4. Default: 'auth_token'
```

---

## Session Management

### Session Lifecycle

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          SESSION LIFECYCLE                                │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  1. LOGIN REQUEST                                                        │
│     POST /api/auth/login { apiKey: "..." }                              │
│     │                                                                    │
│     ▼                                                                    │
│  2. VALIDATE API KEY                                                     │
│     validateApiKey() - timing-safe comparison                            │
│     │                                                                    │
│     ▼                                                                    │
│  3. CREATE SESSION                                                       │
│     crypto.randomBytes(32).toString('hex') → 64-char token              │
│     Store: validSessions.set(token, { createdAt, expiresAt })           │
│     Persist: Write to {DATA_DIR}/.sessions                              │
│     │                                                                    │
│     ▼                                                                    │
│  4. SET COOKIE                                                           │
│     Set-Cookie: automaker_session=<token>; HttpOnly; Secure; SameSite   │
│     │                                                                    │
│     ▼                                                                    │
│  5. SUBSEQUENT REQUESTS                                                  │
│     Cookie sent automatically → validateSession()                        │
│     │                                                                    │
│     ▼                                                                    │
│  6. LOGOUT / EXPIRATION                                                  │
│     invalidateSession() → Remove from memory & disk                      │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

### Session Constants

```typescript
// apps/server/src/lib/auth.ts

const SESSION_COOKIE_NAME = 'automaker_session';
const SESSION_MAX_AGE_MS = 30 * 24 * 60 * 60 * 1000; // 30 days
const WS_TOKEN_MAX_AGE_MS = 5 * 60 * 1000; // 5 minutes

const API_KEY_FILE = path.join(DATA_DIR, '.api-key');
const SESSIONS_FILE = path.join(DATA_DIR, '.sessions');
```

### WebSocket Authentication

WebSocket connections use short-lived, single-use tokens:

```
1. GET /api/auth/token → { token: "ws-token-..." }
2. Connect: ws://host:port/?wsToken=<token>
3. Token validated and immediately deleted (single-use)
4. Token expires after 5 minutes if unused
```

---

## Provider Authentication

### Anthropic/Claude

**Files:**

- `apps/server/src/lib/auth-config.ts` - Anthropic-specific wrapper
- `apps/server/src/routes/setup/routes/auth-claude.ts` - Setup routes
- `apps/server/src/routes/setup/routes/verify-claude-auth.ts` - Verification

**Authentication Methods:**

| Method              | Detection                      | Priority |
| ------------------- | ------------------------------ | -------- |
| `oauth_token_env`   | `ANTHROPIC_AUTH_TOKEN` env var | 1        |
| `oauth_token`       | Claude CLI OAuth token         | 2        |
| `api_key_env`       | `ANTHROPIC_API_KEY` env var    | 3        |
| `api_key`           | Stored in credentials.json     | 4        |
| `cli_authenticated` | Claude Code CLI auth           | 5        |
| `none`              | No authentication found        | -        |

**Verification Flow:**

```typescript
// apps/server/src/routes/setup/routes/verify-claude-auth.ts:105-164

// Execute minimal test query using Claude Agent SDK
const agent = new Anthropic.Agent({
  model: 'claude-sonnet-4-20250514',
  maxTurns: 1,
});
await agent.run('Reply with exactly: VERIFIED');
```

### OpenAI/Codex

**Files:**

- `apps/server/src/lib/codex-auth.ts` - Codex auth checking
- `apps/server/src/routes/setup/routes/auth-codex.ts` - Setup routes
- `apps/server/src/routes/setup/routes/openai-auth-mode.ts` - Mode management

**Authentication Methods:**

| Method              | Detection                              |
| ------------------- | -------------------------------------- |
| `api_key_env`       | `OPENAI_API_KEY` env var               |
| `cli_authenticated` | Codex CLI OAuth (`~/.codex/auth.json`) |
| `none`              | No authentication found                |

**CLI Auth Check:**

```typescript
// apps/server/src/lib/codex-auth.ts:34-76

async function checkCodexAuthentication(): Promise<{
  authenticated: boolean;
  method: 'api_key_env' | 'cli_authenticated' | 'none';
}> {
  // Runs: codex login status
  // Parses output for authentication state
}
```

---

## Security Mechanisms

### 1. Timing-Safe API Key Comparison

```typescript
// apps/server/src/lib/auth.ts:283-300

function validateApiKey(providedKey: string, storedKey: string): boolean {
  const providedBuffer = Buffer.from(providedKey);
  const storedBuffer = Buffer.from(storedKey);

  if (providedBuffer.length !== storedBuffer.length) {
    return false;
  }

  return crypto.timingSafeEqual(providedBuffer, storedBuffer);
}
```

Prevents timing attacks by ensuring comparison takes constant time regardless of where mismatch occurs.

### 2. Rate Limiting

```typescript
// apps/server/src/routes/auth/index.ts:27-48

// Login rate limiting
const loginAttempts = new Map<string, { count: number; resetTime: number }>();
const RATE_LIMIT_WINDOW_MS = 60 * 1000; // 1 minute
const MAX_LOGIN_ATTEMPTS = 5;

// Cleanup expired entries every 5 minutes
setInterval(() => cleanupExpiredEntries(), 5 * 60 * 1000);
```

```typescript
// apps/server/src/lib/auth-utils.ts:226-263

class AuthRateLimiter {
  constructor(
    private maxAttempts: number = 5,
    private windowMs: number = 60000
  ) {}

  checkLimit(identifier: string): { allowed: boolean; remainingAttempts: number };
}
```

### 3. CSRF Protection

```typescript
// apps/server/src/lib/auth.ts:305-319

function getSessionCookieOptions(): CookieOptions {
  return {
    httpOnly: true, // No JavaScript access
    secure: process.env.NODE_ENV === 'production', // HTTPS only in prod
    sameSite: 'lax', // CSRF protection
    maxAge: SESSION_MAX_AGE_MS,
    path: '/',
  };
}
```

### 4. Defense-in-Depth for auth_token Mode

API keys are cleared at 4 levels when using auth_token mode:

```typescript
// apps/server/src/lib/provider-auth-config.ts:11-16

// Defense-in-depth layers for auth_token mode:
// 1. Startup: API keys cleared from process.env
// 2. Provider: buildEnv() explicitly sets env var to empty string
// 3. Subprocess: Env vars filtered based on mode
// 4. UI: Mode indicator shows active mode
```

### 5. Secure File Permissions

```typescript
// API key and session files use restricted permissions
fs.writeFileSync(API_KEY_FILE, apiKey, { mode: 0o600 });
fs.writeFileSync(SESSIONS_FILE, JSON.stringify(sessions), { mode: 0o600 });
```

### 6. Content-Type Validation

```typescript
// apps/server/src/index.ts:384

// All POST/PUT/PATCH requests require application/json
app.use((req, res, next) => {
  if (['POST', 'PUT', 'PATCH'].includes(req.method)) {
    if (!req.is('application/json')) {
      return res.status(415).json({ error: 'Content-Type must be application/json' });
    }
  }
  next();
});
```

---

## API Endpoints

### Authentication Endpoints

| Method | Endpoint           | Purpose                     | Auth Required |
| ------ | ------------------ | --------------------------- | ------------- |
| GET    | `/api/auth/status` | Check authentication status | No            |
| POST   | `/api/auth/login`  | Login with API key          | No            |
| POST   | `/api/auth/logout` | Invalidate session          | Yes           |
| GET    | `/api/auth/token`  | Get WebSocket token         | Yes           |

### Provider Auth Endpoints

| Method | Endpoint                        | Purpose                      |
| ------ | ------------------------------- | ---------------------------- |
| GET    | `/api/setup/auth-mode`          | Get Anthropic auth mode      |
| POST   | `/api/setup/auth-mode`          | Set Anthropic auth mode      |
| GET    | `/api/setup/openai-auth-mode`   | Get OpenAI auth mode         |
| POST   | `/api/setup/openai-auth-mode`   | Set OpenAI auth mode         |
| POST   | `/api/setup/verify-claude-auth` | Verify Claude authentication |
| POST   | `/api/setup/verify-codex-auth`  | Verify Codex authentication  |

### Credentials Endpoints

| Method | Endpoint                    | Purpose                |
| ------ | --------------------------- | ---------------------- |
| GET    | `/api/settings/credentials` | Get masked credentials |
| PUT    | `/api/settings/credentials` | Update credentials     |
| POST   | `/api/setup/store-api-key`  | Store API key          |
| GET    | `/api/setup/api-keys`       | Get API key status     |

### Request/Response Examples

#### Login

```http
POST /api/auth/login
Content-Type: application/json

{
  "apiKey": "abc123..."
}
```

```http
HTTP/1.1 200 OK
Set-Cookie: automaker_session=<token>; HttpOnly; Secure; SameSite=Lax; Max-Age=2592000

{
  "success": true,
  "token": "<session-token>"
}
```

#### Check Auth Status

```http
GET /api/auth/status
Cookie: automaker_session=<token>
```

```http
HTTP/1.1 200 OK

{
  "authenticated": true,
  "autoLoginApplied": false
}
```

#### Get WebSocket Token

```http
GET /api/auth/token
Cookie: automaker_session=<token>
```

```http
HTTP/1.1 200 OK

{
  "token": "ws-abc123..."
}
```

---

## Frontend Integration

### Auth Store (Zustand)

```typescript
// apps/ui/src/store/auth-store.ts

interface AuthState {
  authChecked: boolean; // Whether auth status has been determined
  isAuthenticated: boolean; // Current authentication status
  settingsLoaded: boolean; // Whether settings have been hydrated
}

const useAuthStore = create<AuthState>((set) => ({
  authChecked: false,
  isAuthenticated: false,
  settingsLoaded: false,

  setAuthState: (state: Partial<AuthState>) => set(state),
  resetAuth: () => set({ authChecked: false, isAuthenticated: false }),
}));
```

### HTTP API Client Auth Flow

```typescript
// apps/ui/src/lib/http-api-client.ts

// Token Management
let cachedSessionToken: string | null = null;
const SESSION_TOKEN_KEY = 'automaker:sessionToken';

// Initialize on module load
function initSessionToken() {
  cachedSessionToken = localStorage.getItem(SESSION_TOKEN_KEY);
}

// After successful login
function setSessionToken(token: string) {
  cachedSessionToken = token;
  localStorage.setItem(SESSION_TOKEN_KEY, token);
}

// On logout
function clearSessionToken() {
  cachedSessionToken = null;
  localStorage.removeItem(SESSION_TOKEN_KEY);
}

// Add to requests
function getAuthHeaders(): Record<string, string> {
  const headers: Record<string, string> = {};

  if (isElectron && cachedApiKey) {
    headers['X-API-Key'] = cachedApiKey;
  } else if (cachedSessionToken) {
    headers['X-Session-Token'] = cachedSessionToken;
  }

  return headers;
}
```

### Login View State Machine

```typescript
// apps/ui/src/components/views/login-view.tsx

type LoginState =
  | { status: 'checking_server'; attempt: number }
  | { status: 'server_error' }
  | { status: 'awaiting_login'; apiKey: string }
  | { status: 'logging_in' }
  | { status: 'checking_setup' }
  | { status: 'redirecting' };
```

### Protected Route Flow

```typescript
// apps/ui/src/routes/__root.tsx

// Route protection logic
if (!authChecked) {
  return <LoadingState />;
}

if (!isAuthenticated) {
  if (pathname !== '/login') {
    navigate({ to: '/logged-out' });
  }
  return;
}

if (!settingsLoaded) {
  return <LoadingState />;
}

if (!setupComplete && pathname !== '/setup') {
  navigate({ to: '/setup' });
  return;
}
```

### Global Auth Event Handling

```typescript
// apps/ui/src/routes/__root.tsx

// Listen for auth events
useEffect(() => {
  const handleLoggedOut = () => {
    setAuthState({ isAuthenticated: false });
    navigate({ to: '/logged-out' });
  };

  const handleServerOffline = () => {
    setAuthState({ isAuthenticated: false });
    navigate({ to: '/login' });
  };

  window.addEventListener('automaker:logged-out', handleLoggedOut);
  window.addEventListener('automaker:server-offline', handleServerOffline);

  return () => {
    window.removeEventListener('automaker:logged-out', handleLoggedOut);
    window.removeEventListener('automaker:server-offline', handleServerOffline);
  };
}, []);
```

---

## Configuration

### Environment Variables

| Variable                        | Description                | Default        |
| ------------------------------- | -------------------------- | -------------- |
| `AUTOMAKER_API_KEY`             | Override server API key    | Auto-generated |
| `AUTOMAKER_HIDE_API_KEY`        | Suppress API key display   | `false`        |
| `AUTOMAKER_AUTO_LOGIN`          | Auto-create session in dev | `false`        |
| `AUTOMAKER_DISABLE_AUTH`        | Disable authentication     | `false`        |
| `AUTOMAKER_ANTHROPIC_AUTH_MODE` | Anthropic auth mode        | `auth_token`   |
| `AUTOMAKER_OPENAI_AUTH_MODE`    | OpenAI auth mode           | `auth_token`   |
| `ANTHROPIC_API_KEY`             | Anthropic API key          | -              |
| `OPENAI_API_KEY`                | OpenAI API key             | -              |
| `DATA_DIR`                      | Data storage directory     | `./data`       |

### Credentials Storage Schema

```typescript
// {DATA_DIR}/credentials.json

interface Credentials {
  version: number;
  apiKeys: {
    anthropic: string; // Anthropic API key
    anthropic_oauth_token: string; // OAuth token
    google: string; // Google API key
    openai: string; // OpenAI API key
  };
}
```

### Settings Auth Fields

```typescript
// {DATA_DIR}/settings.json (partial)

interface GlobalSettings {
  // Provider auth modes
  anthropicAuthMode?: 'auth_token' | 'api_key';
  openaiAuthMode?: 'auth_token' | 'api_key';

  // Legacy (deprecated)
  disableApiKeyAuth?: boolean;

  // Custom providers
  claudeCompatibleProviders?: ClaudeCompatibleProvider[];
}
```

---

## File Locations

### Backend Files

| File                                                        | Purpose               | Key Lines |
| ----------------------------------------------------------- | --------------------- | --------- |
| `apps/server/src/lib/auth.ts`                               | Core auth functions   | 105-300   |
| `apps/server/src/lib/auth-utils.ts`                         | Auth utilities        | 23-263    |
| `apps/server/src/lib/auth-config.ts`                        | Anthropic auth config | 61-196    |
| `apps/server/src/lib/provider-auth-config.ts`               | Multi-provider config | 73-442    |
| `apps/server/src/lib/codex-auth.ts`                         | Codex auth checking   | 34-76     |
| `apps/server/src/routes/auth/index.ts`                      | Auth endpoints        | 112-266   |
| `apps/server/src/routes/setup/routes/verify-claude-auth.ts` | Claude verification   | 79-337    |
| `apps/server/src/routes/setup/routes/store-api-key.ts`      | API key storage       | 34-100    |
| `apps/server/src/services/settings-service.ts`              | Credentials I/O       | 1-150     |

### Frontend Files

| File                                          | Purpose          | Key Lines |
| --------------------------------------------- | ---------------- | --------- |
| `apps/ui/src/store/auth-store.ts`             | Auth state       | 1-34      |
| `apps/ui/src/store/setup-store.ts`            | Setup state      | 74-103    |
| `apps/ui/src/lib/http-api-client.ts`          | API client       | 176-455   |
| `apps/ui/src/components/views/login-view.tsx` | Login UI         | 1-472     |
| `apps/ui/src/hooks/use-auth-config.ts`        | Auth hooks       | 36-216    |
| `apps/ui/src/routes/__root.tsx`               | Route protection | 399-585   |

### Type Definitions

| File                         | Types                                                                |
| ---------------------------- | -------------------------------------------------------------------- |
| `libs/types/src/settings.ts` | `AnthropicAuthMode`, `OpenaiAuthMode`, `Credentials`, `ApiKeySource` |
| `libs/types/src/provider.ts` | `ProviderConfig`, `InstallationStatus`                               |

### Data Files

| File                          | Content               |
| ----------------------------- | --------------------- |
| `{DATA_DIR}/.api-key`         | Server access API key |
| `{DATA_DIR}/.sessions`        | Active session tokens |
| `{DATA_DIR}/credentials.json` | Provider API keys     |
| `{DATA_DIR}/settings.json`    | Auth mode settings    |

---

## Diagrams

### Complete Authentication Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        AUTHENTICATION FLOW                                   │
└─────────────────────────────────────────────────────────────────────────────┘

   USER                    FRONTEND                    BACKEND
    │                         │                           │
    │  1. Access App          │                           │
    ├────────────────────────>│                           │
    │                         │  2. GET /api/auth/status  │
    │                         ├──────────────────────────>│
    │                         │      { authenticated }    │
    │                         │<──────────────────────────┤
    │                         │                           │
    │  [If not authenticated] │                           │
    │                         │                           │
    │  3. Show Login Form     │                           │
    │<────────────────────────┤                           │
    │                         │                           │
    │  4. Enter API Key       │                           │
    ├────────────────────────>│                           │
    │                         │  5. POST /api/auth/login  │
    │                         ├──────────────────────────>│
    │                         │                           │
    │                         │      Rate limit check     │
    │                         │      validateApiKey()     │
    │                         │      createSession()      │
    │                         │                           │
    │                         │  Set-Cookie: session=...  │
    │                         │<──────────────────────────┤
    │                         │                           │
    │  6. Redirect to App     │                           │
    │<────────────────────────┤                           │
    │                         │                           │
    │  [Authenticated requests]                           │
    │                         │                           │
    │  7. Use Application     │  Cookie: session=...      │
    ├────────────────────────>├──────────────────────────>│
    │                         │      authMiddleware()     │
    │                         │      validateSession()    │
    │                         │<──────────────────────────┤
    │  Response               │                           │
    │<────────────────────────┤                           │
    │                         │                           │
    │  [WebSocket Connection] │                           │
    │                         │                           │
    │  8. Need WebSocket      │  9. GET /api/auth/token   │
    ├────────────────────────>├──────────────────────────>│
    │                         │      createWsToken()      │
    │                         │      (5-min TTL)          │
    │                         │<──────────────────────────┤
    │                         │                           │
    │                         │  10. WS /?wsToken=...     │
    │                         ├──────────────────────────>│
    │                         │      authenticateWs()     │
    │                         │      (single-use token)   │
    │  WebSocket Connected    │<──────────────────────────┤
    │<────────────────────────┤                           │
    │                         │                           │
```

### Provider Auth Mode Decision Tree

```
                    ┌─────────────────────────┐
                    │  Provider Auth Request  │
                    └───────────┬─────────────┘
                                │
                                ▼
                    ┌─────────────────────────┐
                    │  Check Auth Mode        │
                    │  (auth_token | api_key) │
                    └───────────┬─────────────┘
                                │
              ┌─────────────────┴─────────────────┐
              │                                   │
              ▼                                   ▼
    ┌─────────────────┐                 ┌─────────────────┐
    │  auth_token     │                 │    api_key      │
    │  (OAuth/CLI)    │                 │  (Pay-per-use)  │
    └────────┬────────┘                 └────────┬────────┘
             │                                   │
             ▼                                   ▼
    ┌─────────────────┐                 ┌─────────────────┐
    │ API keys BLOCKED│                 │ Check API Key   │
    │ at 4 levels     │                 │ Sources         │
    └────────┬────────┘                 └────────┬────────┘
             │                                   │
             ▼                                   │
    ┌─────────────────┐            ┌─────────────┴─────────────┐
    │ Check OAuth     │            │             │             │
    │ Token Sources   │            ▼             ▼             ▼
    └────────┬────────┘     ┌──────────┐  ┌──────────┐  ┌──────────┐
             │              │ Env Var  │  │ Creds    │  │ Settings │
    ┌────────┴────────┐     │ API Key  │  │ File     │  │ Profile  │
    │        │        │     └────┬─────┘  └────┬─────┘  └────┬─────┘
    ▼        ▼        ▼          │             │             │
┌──────┐ ┌──────┐ ┌──────┐       └─────────────┴─────────────┘
│ Env  │ │ CLI  │ │ File │                     │
│ Token│ │ Auth │ │ Token│                     ▼
└──────┘ └──────┘ └──────┘            ┌─────────────────┐
                                      │ Execute Request │
                                      │ with API Key    │
                                      └─────────────────┘
```

---

## Security Considerations

### Best Practices Implemented

1. **No Plaintext Password Storage**: API keys are stored but never logged
2. **Timing-Safe Comparisons**: Prevents timing attacks on key validation
3. **HTTP-Only Cookies**: JavaScript cannot access session tokens
4. **SameSite Cookie Policy**: CSRF protection
5. **Rate Limiting**: Prevents brute-force attacks
6. **Short-Lived WebSocket Tokens**: Minimize exposure window
7. **Single-Use WS Tokens**: Tokens deleted after first use
8. **Defense-in-Depth**: Multiple layers for auth_token mode

### Potential Improvements

1. Add CSRF tokens for state-changing operations
2. Implement token refresh mechanism
3. Add session revocation UI
4. Implement audit logging for auth events
5. Add MFA support for sensitive operations

---

## Troubleshooting

### Common Issues

| Issue                          | Cause                   | Solution                             |
| ------------------------------ | ----------------------- | ------------------------------------ |
| "Unauthorized" on all requests | Invalid/expired session | Re-login via `/login`                |
| API key not accepted           | Timing mismatch         | Check server console for correct key |
| WebSocket connection fails     | Expired WS token        | Tokens expire after 5 minutes        |
| Provider auth failing          | Wrong auth mode         | Check mode matches credentials type  |
| Rate limited                   | Too many login attempts | Wait 60 seconds                      |

### Debug Commands

```bash
# Check current auth mode
curl http://localhost:3008/api/setup/auth-mode

# Check API key status
curl http://localhost:3008/api/setup/api-keys

# Verify Claude auth (requires session)
curl -X POST http://localhost:3008/api/setup/verify-claude-auth \
  -H "Cookie: automaker_session=<token>"
```

---

## Changelog

- **v1.0** (January 2026): Initial documentation
  - Multi-provider authentication (Anthropic, OpenAI)
  - Dual auth modes (auth_token, api_key)
  - Session and API key authentication
  - WebSocket authentication
  - Defense-in-depth security measures
