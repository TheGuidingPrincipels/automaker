# Phase 4: OAuth Authentication

> **Status**: Planning
> **Estimated Duration**: 1 week
> **Prerequisites**: Phase 1 (User Foundation)
> **Blocks**: Phase 5 (Deploy)

## Objective

Add Google OAuth as an alternative to email/password authentication. After this phase:

- Users can sign in with their Google account
- New users are auto-created on first OAuth login
- Existing users can link their Google account
- User profiles show name and avatar from Google

## What This Phase DOES

- Implements Google OAuth 2.0 flow
- Creates OAuth callback route
- Auto-creates users from OAuth profile
- Updates login UI with "Sign in with Google" button
- Adds user profile display in header

## What This Phase DOES NOT Do

| Excluded Feature                   | Handled In |
| ---------------------------------- | ---------- |
| User registration (email/password) | Phase 1    |
| Per-user credentials               | Phase 2    |
| Knowledge Hub sync                 | Phase 3    |
| GitHub OAuth                       | Future     |
| Microsoft OAuth                    | Future     |

---

## Technical Specification

### 1. Database Schema Addition

**File to Modify**: `apps/server/prisma/schema.prisma`

```prisma
model User {
  id            String    @id @default(uuid())
  email         String    @unique
  passwordHash  String?   // NULLABLE for OAuth-only users
  name          String
  avatarUrl     String?   // ADD - from OAuth profile
  googleId      String?   @unique  // ADD - Google OAuth ID
  createdAt     DateTime  @default(now())
  updatedAt     DateTime  @updatedAt
  lastLoginAt   DateTime?

  sessions      Session[]
  credentials   UserCredentials?

  @@map("users")
}
```

### 2. Google OAuth Configuration

**Environment Variables** (add to `.env.example`):

```bash
# Google OAuth (get from Google Cloud Console)
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_CALLBACK_URL=http://localhost:3008/api/auth/google/callback
```

**Google Cloud Console Setup**:

1. Go to https://console.cloud.google.com/
2. Create new project or select existing
3. Enable "Google+ API" and "Google Identity"
4. Create OAuth 2.0 credentials
5. Add authorized redirect URI: `http://localhost:3008/api/auth/google/callback`
6. For production, add: `https://your-domain.com/api/auth/google/callback`

### 3. OAuth Types

**File to Modify**: `libs/types/src/user.ts`

```typescript
export type AuthProvider = 'password' | 'google' | 'github';

export interface User {
  id: string;
  email: string;
  name: string;
  avatarUrl?: string;
  authProvider?: AuthProvider; // ADD
  googleId?: string; // ADD
  createdAt: string;
  updatedAt: string;
  lastLoginAt?: string;
}

export interface OAuthProfile {
  provider: AuthProvider;
  id: string;
  email: string;
  name: string;
  avatarUrl?: string;
}
```

### 4. OAuth Service

**File to Create**: `apps/server/src/services/oauth-service.ts`

```typescript
import { getPrisma } from '../lib/database';
import type { PublicUser, OAuthProfile } from '@automaker/types';
import { createSession } from '../lib/auth';

export class OAuthService {
  /**
   * Find or create user from OAuth profile
   * Returns user and session token
   */
  async handleOAuthLogin(profile: OAuthProfile): Promise<{
    user: PublicUser;
    token: string;
    isNewUser: boolean;
  }> {
    const prisma = getPrisma();

    // Try to find existing user by OAuth provider ID
    let user = await this.findUserByOAuthId(profile.provider, profile.id);
    let isNewUser = false;

    if (!user) {
      // Try to find by email (link OAuth to existing account)
      user = await prisma.user.findUnique({
        where: { email: profile.email.toLowerCase() },
      });

      if (user) {
        // Link OAuth to existing user
        await this.linkOAuthToUser(user.id, profile);
      } else {
        // Create new user from OAuth profile
        user = await this.createUserFromOAuth(profile);
        isNewUser = true;
      }
    }

    // Update last login
    await prisma.user.update({
      where: { id: user.id },
      data: {
        lastLoginAt: new Date(),
        avatarUrl: profile.avatarUrl || user.avatarUrl,
        name: profile.name || user.name,
      },
    });

    // Create session
    const token = await createSession(user.id);

    return {
      user: this.toPublicUser(user),
      token,
      isNewUser,
    };
  }

  /**
   * Find user by OAuth provider ID
   */
  private async findUserByOAuthId(provider: string, providerId: string): Promise<User | null> {
    const prisma = getPrisma();

    if (provider === 'google') {
      return prisma.user.findUnique({
        where: { googleId: providerId },
      });
    }

    // Add more providers here as needed
    return null;
  }

  /**
   * Link OAuth profile to existing user
   */
  private async linkOAuthToUser(userId: string, profile: OAuthProfile): Promise<void> {
    const prisma = getPrisma();

    if (profile.provider === 'google') {
      await prisma.user.update({
        where: { id: userId },
        data: { googleId: profile.id },
      });
    }
  }

  /**
   * Create new user from OAuth profile
   */
  private async createUserFromOAuth(profile: OAuthProfile): Promise<User> {
    const prisma = getPrisma();

    return prisma.user.create({
      data: {
        email: profile.email.toLowerCase(),
        name: profile.name,
        avatarUrl: profile.avatarUrl,
        passwordHash: null, // OAuth-only user
        googleId: profile.provider === 'google' ? profile.id : null,
      },
    });
  }

  private toPublicUser(user: User): PublicUser {
    return {
      id: user.id,
      email: user.email,
      name: user.name,
      avatarUrl: user.avatarUrl,
    };
  }
}

// Singleton
let oauthService: OAuthService | null = null;

export function getOAuthService(): OAuthService {
  if (!oauthService) {
    oauthService = new OAuthService();
  }
  return oauthService;
}
```

### 5. Google OAuth Routes

**File to Create**: `apps/server/src/routes/auth/oauth.ts`

```typescript
import { Router, Request, Response } from 'express';
import { OAuth2Client } from 'google-auth-library';
import { getOAuthService } from '../../services/oauth-service';
import { SESSION_COOKIE_NAME, getSessionCookieOptions } from '../../lib/auth';

const router = Router();

// Initialize Google OAuth client
function getGoogleClient(): OAuth2Client {
  const clientId = process.env.GOOGLE_CLIENT_ID;
  const clientSecret = process.env.GOOGLE_CLIENT_SECRET;
  const callbackUrl =
    process.env.GOOGLE_CALLBACK_URL || 'http://localhost:3008/api/auth/google/callback';

  if (!clientId || !clientSecret) {
    throw new Error('Google OAuth not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.');
  }

  return new OAuth2Client(clientId, clientSecret, callbackUrl);
}

/**
 * GET /api/auth/google
 * Initiates Google OAuth flow - redirects to Google
 */
router.get('/google', (req: Request, res: Response) => {
  try {
    const client = getGoogleClient();

    // Generate auth URL
    const authUrl = client.generateAuthUrl({
      access_type: 'offline',
      scope: [
        'https://www.googleapis.com/auth/userinfo.email',
        'https://www.googleapis.com/auth/userinfo.profile',
      ],
      // State parameter for CSRF protection
      state: Buffer.from(
        JSON.stringify({
          returnTo: req.query.returnTo || '/',
          timestamp: Date.now(),
        })
      ).toString('base64'),
    });

    res.redirect(authUrl);
  } catch (error) {
    console.error('Google OAuth init error:', error);
    res.redirect('/login?error=oauth_not_configured');
  }
});

/**
 * GET /api/auth/google/callback
 * Handles Google OAuth callback
 */
router.get('/google/callback', async (req: Request, res: Response) => {
  const { code, state, error } = req.query;

  // Handle OAuth errors
  if (error) {
    console.error('Google OAuth error:', error);
    return res.redirect('/login?error=oauth_denied');
  }

  if (!code || typeof code !== 'string') {
    return res.redirect('/login?error=oauth_no_code');
  }

  try {
    const client = getGoogleClient();

    // Exchange code for tokens
    const { tokens } = await client.getToken(code);
    client.setCredentials(tokens);

    // Get user info
    const userInfoResponse = await client.request({
      url: 'https://www.googleapis.com/oauth2/v2/userinfo',
    });

    const userInfo = userInfoResponse.data as {
      id: string;
      email: string;
      name: string;
      picture?: string;
    };

    // Handle login/registration
    const oauthService = getOAuthService();
    const { user, token, isNewUser } = await oauthService.handleOAuthLogin({
      provider: 'google',
      id: userInfo.id,
      email: userInfo.email,
      name: userInfo.name,
      avatarUrl: userInfo.picture,
    });

    // Set session cookie
    res.cookie(SESSION_COOKIE_NAME, token, getSessionCookieOptions());

    // Parse return URL from state
    let returnTo = '/';
    if (state && typeof state === 'string') {
      try {
        const stateData = JSON.parse(Buffer.from(state, 'base64').toString());
        returnTo = stateData.returnTo || '/';
      } catch {
        // Ignore state parse errors
      }
    }

    // Redirect to app (or setup if new user)
    if (isNewUser) {
      res.redirect('/setup');
    } else {
      res.redirect(returnTo);
    }
  } catch (error) {
    console.error('Google OAuth callback error:', error);
    res.redirect('/login?error=oauth_failed');
  }
});

/**
 * GET /api/auth/google/status
 * Check if Google OAuth is configured
 */
router.get('/google/status', (req: Request, res: Response) => {
  const configured = !!(process.env.GOOGLE_CLIENT_ID && process.env.GOOGLE_CLIENT_SECRET);

  res.json({ configured });
});

export function createGoogleOAuthRoutes() {
  return router;
}
```

**Register routes** in `apps/server/src/index.ts`:

```typescript
import { createGoogleOAuthRoutes } from './routes/auth/oauth';

// Register OAuth routes (public, no auth middleware)
app.use('/api/auth', createGoogleOAuthRoutes());
```

### 6. Package Dependencies

**Add to `apps/server/package.json`**:

```json
{
  "dependencies": {
    "google-auth-library": "^9.x"
  }
}
```

### 7. Frontend OAuth Button Component

**File to Create**: `apps/ui/src/components/auth/oauth-buttons.tsx`

```tsx
import { useState, useEffect } from 'react';

interface OAuthButtonsProps {
  onError?: (error: string) => void;
}

export function OAuthButtons({ onError }: OAuthButtonsProps) {
  const [googleEnabled, setGoogleEnabled] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check which OAuth providers are configured
    async function checkOAuthStatus() {
      try {
        const res = await fetch('/api/auth/google/status');
        const { configured } = await res.json();
        setGoogleEnabled(configured);
      } catch {
        // OAuth not available
      } finally {
        setLoading(false);
      }
    }
    checkOAuthStatus();
  }, []);

  if (loading) {
    return null;
  }

  if (!googleEnabled) {
    return null;
  }

  function handleGoogleLogin() {
    // Redirect to Google OAuth
    window.location.href = '/api/auth/google';
  }

  return (
    <div className="space-y-3">
      <div className="relative">
        <div className="absolute inset-0 flex items-center">
          <span className="w-full border-t" />
        </div>
        <div className="relative flex justify-center text-xs uppercase">
          <span className="bg-background px-2 text-muted-foreground">Or continue with</span>
        </div>
      </div>

      <div className="grid gap-2">
        {googleEnabled && (
          <button
            type="button"
            onClick={handleGoogleLogin}
            className="flex items-center justify-center gap-2 rounded-md border border-input bg-background px-4 py-2 text-sm font-medium hover:bg-accent hover:text-accent-foreground"
          >
            <GoogleIcon className="h-4 w-4" />
            Sign in with Google
          </button>
        )}
      </div>
    </div>
  );
}

function GoogleIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24">
      <path
        fill="currentColor"
        d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
      />
      <path
        fill="currentColor"
        d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
      />
      <path
        fill="currentColor"
        d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
      />
      <path
        fill="currentColor"
        d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
      />
    </svg>
  );
}
```

### 8. Update Login View

**File to Modify**: `apps/ui/src/components/views/login-view.tsx`

Add OAuth buttons below the login form:

```tsx
import { OAuthButtons } from '../auth/oauth-buttons';

// In the render, after the email/password form:
<div className="space-y-4">
  {/* Email/password form */}
  <form onSubmit={handleSubmit}>{/* ... existing form fields ... */}</form>

  {/* OAuth buttons */}
  <OAuthButtons onError={(error) => setError(error)} />
</div>;
```

### 9. OAuth Callback Route

**File to Create**: `apps/ui/src/routes/auth.callback.tsx`

```tsx
import { useEffect } from 'react';
import { useNavigate, useSearchParams } from '@tanstack/react-router';
import { useAuthStore } from '../store/auth-store';

/**
 * OAuth callback handler
 * This page is shown briefly during OAuth redirect flow
 */
export function AuthCallbackPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const setAuthState = useAuthStore((s) => s.setAuthState);

  useEffect(() => {
    const error = searchParams.get('error');

    if (error) {
      // Redirect to login with error
      navigate({ to: '/login', search: { error } });
      return;
    }

    // OAuth succeeded - session cookie should be set
    // Verify auth and redirect to app
    async function verifyAndRedirect() {
      try {
        const res = await fetch('/api/auth/me', { credentials: 'include' });
        if (res.ok) {
          const { user } = await res.json();
          setAuthState({
            isAuthenticated: true,
            authChecked: true,
            user,
          });
          navigate({ to: '/' });
        } else {
          navigate({ to: '/login', search: { error: 'auth_failed' } });
        }
      } catch {
        navigate({ to: '/login', search: { error: 'auth_failed' } });
      }
    }

    verifyAndRedirect();
  }, [searchParams, navigate, setAuthState]);

  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="text-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto" />
        <p className="mt-4 text-muted-foreground">Completing sign in...</p>
      </div>
    </div>
  );
}
```

Register route in router config.

### 10. User Profile in Header

**File to Modify**: `apps/ui/src/components/layout/header.tsx` (or equivalent)

```tsx
import { useAuthStore } from '../../store/auth-store';

function UserMenu() {
  const user = useAuthStore((s) => s.user);

  if (!user) return null;

  return (
    <div className="flex items-center gap-2">
      {user.avatarUrl ? (
        <img src={user.avatarUrl} alt={user.name} className="h-8 w-8 rounded-full" />
      ) : (
        <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center">
          <span className="text-sm font-medium">{user.name.charAt(0).toUpperCase()}</span>
        </div>
      )}
      <span className="text-sm font-medium">{user.name}</span>
    </div>
  );
}
```

---

## Testing Checklist

### Unit Tests

- [ ] `OAuthService.handleOAuthLogin()` creates new user
- [ ] `OAuthService.handleOAuthLogin()` links to existing user by email
- [ ] `OAuthService.handleOAuthLogin()` finds user by Google ID
- [ ] OAuth-only users have null passwordHash

### Integration Tests

- [ ] GET `/api/auth/google` redirects to Google
- [ ] GET `/api/auth/google/callback` handles valid code
- [ ] GET `/api/auth/google/callback` handles errors
- [ ] Session cookie set after OAuth success

### E2E Tests

- [ ] Click "Sign in with Google" redirects to Google
- [ ] Complete OAuth flow creates session
- [ ] User avatar appears in header
- [ ] OAuth user can access all features

---

## Rollback Plan

1. Remove OAuth routes from server
2. Remove OAuthButtons component
3. Remove OAuth callback route
4. Remove googleId field from schema (migration down)
5. Revert login-view to remove OAuth buttons

---

## Success Criteria

Phase 4 is complete when:

1. "Sign in with Google" button appears on login page
2. Clicking button initiates Google OAuth flow
3. New users are created from Google profile
4. Existing users can link Google account
5. User avatar/name from Google displayed in app

---

## Notes for Phase 5 (Deploy)

### Production OAuth Setup

1. Add production callback URL in Google Cloud Console
2. Set environment variables on server:
   - `GOOGLE_CLIENT_ID`
   - `GOOGLE_CLIENT_SECRET`
   - `GOOGLE_CALLBACK_URL=https://your-domain.com/api/auth/google/callback`

### Security Considerations

- Verify OAuth state parameter to prevent CSRF
- Use HTTPS in production (OAuth requires it)
- Store only necessary profile data

### Future OAuth Providers

To add GitHub OAuth:

1. Add `githubId` to User schema
2. Create GitHub OAuth routes (same pattern)
3. Add GitHub button to OAuthButtons component
