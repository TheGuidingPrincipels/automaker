# Phase 2: Per-User Credentials

> **Status**: Planning
> **Estimated Duration**: 1 week
> **Prerequisites**: Phase 1 (User Foundation)
> **Blocks**: Phase 5 (Deploy)

## Objective

Enable each user to manage their own API keys (Anthropic, OpenAI, etc.) separately. After this phase:

- User A's API key is stored encrypted and isolated from User B
- Agent runs use the requesting user's API key
- Users can set their own auth mode (OAuth vs API key)
- Missing user credentials fall back to global/system credentials

## What This Phase DOES

- Creates AES-256 encryption service for API keys
- Implements per-user credential storage (database)
- Modifies credential resolution to use user context
- Updates Settings UI with "My API Keys" section
- Passes userId through agent execution chain

## What This Phase DOES NOT Do

| Excluded Feature          | Handled In |
| ------------------------- | ---------- |
| User registration/login   | Phase 1    |
| Knowledge Hub sync        | Phase 3    |
| OAuth authentication      | Phase 4    |
| Team-shared API key pools | Future     |

---

## Technical Specification

### 1. Database Schema Addition

**File to Modify**: `apps/server/prisma/schema.prisma`

```prisma
model UserCredentials {
  id        String   @id @default(uuid())
  userId    String   @unique

  // Encrypted API keys (AES-256-CBC)
  anthropicKey          String?
  anthropicKeyIv        String?   // Initialization vector
  anthropicOAuthToken   String?
  anthropicOAuthTokenIv String?
  openaiKey             String?
  openaiKeyIv           String?
  googleKey             String?
  googleKeyIv           String?

  // Auth mode preferences per user
  anthropicAuthMode     String?   // 'auth_token' | 'api_key'
  openaiAuthMode        String?   // 'auth_token' | 'api_key'

  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt

  user      User     @relation(fields: [userId], references: [id], onDelete: Cascade)

  @@map("user_credentials")
}

// Update User model to include relation
model User {
  // ... existing fields ...
  credentials UserCredentials?
}
```

### 2. Encryption Service

**File to Create**: `apps/server/src/lib/encryption.ts`

```typescript
import crypto from 'crypto';

const ALGORITHM = 'aes-256-cbc';
const IV_LENGTH = 16;

/**
 * Get encryption key from environment or generate warning
 */
function getEncryptionKey(): Buffer {
  const key = process.env.AUTOMAKER_ENCRYPTION_KEY;

  if (!key) {
    console.warn(
      'WARNING: AUTOMAKER_ENCRYPTION_KEY not set. ' +
        "Generate one with: node -e \"console.log(require('crypto').randomBytes(32).toString('hex'))\""
    );
    // Use a derived key from a constant for development only
    // This is NOT secure for production
    return crypto.scryptSync('automaker-dev-key', 'salt', 32);
  }

  const keyBuffer = Buffer.from(key, 'hex');
  if (keyBuffer.length !== 32) {
    throw new Error('AUTOMAKER_ENCRYPTION_KEY must be 64 hex characters (32 bytes)');
  }

  return keyBuffer;
}

/**
 * Encrypt a string value
 * Returns { encrypted: string, iv: string } or null if value is empty
 */
export function encrypt(text: string): { encrypted: string; iv: string } | null {
  if (!text || text.trim() === '') {
    return null;
  }

  const key = getEncryptionKey();
  const iv = crypto.randomBytes(IV_LENGTH);
  const cipher = crypto.createCipheriv(ALGORITHM, key, iv);

  let encrypted = cipher.update(text, 'utf8', 'hex');
  encrypted += cipher.final('hex');

  return {
    encrypted,
    iv: iv.toString('hex'),
  };
}

/**
 * Decrypt a previously encrypted value
 * Returns the original string or null if decryption fails
 */
export function decrypt(encrypted: string, ivHex: string): string | null {
  if (!encrypted || !ivHex) {
    return null;
  }

  try {
    const key = getEncryptionKey();
    const iv = Buffer.from(ivHex, 'hex');
    const decipher = crypto.createDecipheriv(ALGORITHM, key, iv);

    let decrypted = decipher.update(encrypted, 'hex', 'utf8');
    decrypted += decipher.final('utf8');

    return decrypted;
  } catch (error) {
    console.error('Decryption failed:', error);
    return null;
  }
}

/**
 * Check if encryption key is properly configured
 */
export function isEncryptionConfigured(): boolean {
  return !!process.env.AUTOMAKER_ENCRYPTION_KEY;
}
```

### 3. User Credential Service

**File to Create**: `apps/server/src/services/credential-service.ts`

```typescript
import { getPrisma } from '../lib/database';
import { encrypt, decrypt } from '../lib/encryption';
import type { Credentials, AnthropicAuthMode, OpenaiAuthMode } from '@automaker/types';

export interface UserCredentialInput {
  anthropicKey?: string;
  anthropicOAuthToken?: string;
  openaiKey?: string;
  googleKey?: string;
  anthropicAuthMode?: AnthropicAuthMode;
  openaiAuthMode?: OpenaiAuthMode;
}

export class CredentialService {
  /**
   * Get credentials for a specific user
   * Falls back to global credentials if user has none
   */
  async getCredentialsForUser(userId: string | undefined): Promise<Credentials> {
    // If no user, return global credentials
    if (!userId || userId === 'system') {
      return this.getGlobalCredentials();
    }

    const prisma = getPrisma();
    const userCreds = await prisma.userCredentials.findUnique({
      where: { userId },
    });

    if (!userCreds) {
      // Fall back to global credentials
      return this.getGlobalCredentials();
    }

    // Decrypt user credentials
    const credentials: Credentials = {
      version: 1,
      apiKeys: {
        anthropic: userCreds.anthropicKey
          ? decrypt(userCreds.anthropicKey, userCreds.anthropicKeyIv!) || ''
          : '',
        anthropic_oauth_token: userCreds.anthropicOAuthToken
          ? decrypt(userCreds.anthropicOAuthToken, userCreds.anthropicOAuthTokenIv!) || ''
          : '',
        openai: userCreds.openaiKey
          ? decrypt(userCreds.openaiKey, userCreds.openaiKeyIv!) || ''
          : '',
        google: userCreds.googleKey
          ? decrypt(userCreds.googleKey, userCreds.googleKeyIv!) || ''
          : '',
      },
    };

    // If any key is missing, try to fill from global
    const global = await this.getGlobalCredentials();
    for (const key of Object.keys(credentials.apiKeys) as Array<keyof typeof credentials.apiKeys>) {
      if (!credentials.apiKeys[key]) {
        credentials.apiKeys[key] = global.apiKeys[key];
      }
    }

    return credentials;
  }

  /**
   * Update credentials for a specific user
   */
  async updateCredentialsForUser(userId: string, input: UserCredentialInput): Promise<void> {
    const prisma = getPrisma();

    const data: Record<string, string | null> = {};

    // Encrypt each provided key
    if (input.anthropicKey !== undefined) {
      const encrypted = encrypt(input.anthropicKey);
      data.anthropicKey = encrypted?.encrypted || null;
      data.anthropicKeyIv = encrypted?.iv || null;
    }

    if (input.anthropicOAuthToken !== undefined) {
      const encrypted = encrypt(input.anthropicOAuthToken);
      data.anthropicOAuthToken = encrypted?.encrypted || null;
      data.anthropicOAuthTokenIv = encrypted?.iv || null;
    }

    if (input.openaiKey !== undefined) {
      const encrypted = encrypt(input.openaiKey);
      data.openaiKey = encrypted?.encrypted || null;
      data.openaiKeyIv = encrypted?.iv || null;
    }

    if (input.googleKey !== undefined) {
      const encrypted = encrypt(input.googleKey);
      data.googleKey = encrypted?.encrypted || null;
      data.googleKeyIv = encrypted?.iv || null;
    }

    // Auth modes (not encrypted)
    if (input.anthropicAuthMode !== undefined) {
      data.anthropicAuthMode = input.anthropicAuthMode;
    }
    if (input.openaiAuthMode !== undefined) {
      data.openaiAuthMode = input.openaiAuthMode;
    }

    // Upsert user credentials
    await prisma.userCredentials.upsert({
      where: { userId },
      update: data,
      create: {
        userId,
        ...data,
      },
    });
  }

  /**
   * Get auth mode for a user + provider
   */
  async getAuthModeForUser(
    userId: string | undefined,
    provider: 'anthropic' | 'openai'
  ): Promise<'auth_token' | 'api_key'> {
    if (!userId || userId === 'system') {
      // Use global auth mode
      const globalMode =
        provider === 'anthropic'
          ? process.env.AUTOMAKER_ANTHROPIC_AUTH_MODE
          : process.env.AUTOMAKER_OPENAI_AUTH_MODE;
      return (globalMode as 'auth_token' | 'api_key') || 'auth_token';
    }

    const prisma = getPrisma();
    const userCreds = await prisma.userCredentials.findUnique({
      where: { userId },
      select: { anthropicAuthMode: true, openaiAuthMode: true },
    });

    if (!userCreds) {
      return 'auth_token'; // Default
    }

    const mode = provider === 'anthropic' ? userCreds.anthropicAuthMode : userCreds.openaiAuthMode;

    return (mode as 'auth_token' | 'api_key') || 'auth_token';
  }

  /**
   * Get masked credentials for display (show first 4 + last 4 chars)
   */
  async getMaskedCredentialsForUser(
    userId: string
  ): Promise<Record<string, { configured: boolean; masked: string }>> {
    const creds = await this.getCredentialsForUser(userId);

    const mask = (value: string): { configured: boolean; masked: string } => {
      if (!value || value.length < 10) {
        return { configured: false, masked: '' };
      }
      return {
        configured: true,
        masked: `${value.slice(0, 4)}${'*'.repeat(8)}${value.slice(-4)}`,
      };
    };

    return {
      anthropic: mask(creds.apiKeys.anthropic),
      anthropic_oauth_token: mask(creds.apiKeys.anthropic_oauth_token),
      openai: mask(creds.apiKeys.openai),
      google: mask(creds.apiKeys.google),
    };
  }

  /**
   * Get global credentials from file/env (existing behavior)
   */
  private async getGlobalCredentials(): Promise<Credentials> {
    // Import existing settings service
    const { getSettingsService } = await import('./settings-service');
    const settingsService = getSettingsService();
    return settingsService.getCredentials();
  }
}

// Singleton
let credentialService: CredentialService | null = null;

export function getCredentialService(): CredentialService {
  if (!credentialService) {
    credentialService = new CredentialService();
  }
  return credentialService;
}
```

### 4. Agent Service Changes

**File to Modify**: `apps/server/src/services/agent-service.ts`

**Add userId parameter to sendMessage()** (around line 197):

```typescript
// BEFORE
async sendMessage(params: {
  sessionId: string;
  message: string;
  model?: string;
  // ...
}): Promise<void>

// AFTER
async sendMessage(params: {
  sessionId: string;
  message: string;
  model?: string;
  userId?: string;  // ADD THIS
  // ...
}): Promise<void>
```

**Update credential resolution** (around line 279):

```typescript
// BEFORE
const credentials = await this.settingsService?.getCredentials();

// AFTER
const credentialService = getCredentialService();
const credentials = await credentialService.getCredentialsForUser(params.userId);
```

### 5. Auto-Mode Service Changes

**File to Modify**: `apps/server/src/services/auto-mode-service.ts`

**Add userId to executeFeature()** (around line 1064):

```typescript
// Add userId parameter
async executeFeature(
  projectPath: string,
  featureId: string,
  useWorktrees: boolean,
  isAutoMode: boolean,
  userId?: string  // ADD THIS
): Promise<void>
```

**Pass userId to runAgent()** (around line 3346):

```typescript
// Update runAgent call to include userId
await this.runAgent(
  workDir,
  featureId,
  prompt,
  abortController,
  projectPath,
  // ... other params ...
  userId // ADD THIS
);
```

**Update runAgent credential resolution** (around line 3504):

```typescript
// BEFORE
const credentials = await this.settingsService?.getCredentials();

// AFTER
const credentialService = getCredentialService();
const credentials = await credentialService.getCredentialsForUser(userId);
```

### 6. Route Updates

**File to Modify**: `apps/server/src/routes/agent/index.ts`

**Pass userId from request to service**:

```typescript
router.post('/send', async (req: AuthenticatedRequest, res) => {
  const { sessionId, message, model } = req.body;
  const userId = req.user?.id; // Get from auth middleware

  await agentService.sendMessage({
    sessionId,
    message,
    model,
    userId, // Pass through
    // ...
  });
});
```

**File to Modify**: `apps/server/src/routes/features/index.ts`

**Pass userId to feature execution**:

```typescript
router.post('/:featureId/execute', async (req: AuthenticatedRequest, res) => {
  const { featureId } = req.params;
  const userId = req.user?.id;

  await autoModeService.executeFeature(
    projectPath,
    featureId,
    useWorktrees,
    false, // isAutoMode
    userId // Pass through
  );
});
```

### 7. Credential Routes

**File to Create**: `apps/server/src/routes/user-credentials/index.ts`

```typescript
import { Router, Response } from 'express';
import type { AuthenticatedRequest } from '@automaker/types';
import { getCredentialService } from '../../services/credential-service';

const router = Router();

// GET /api/user/credentials - Get masked credentials for current user
router.get('/credentials', async (req: AuthenticatedRequest, res: Response) => {
  if (!req.user) {
    return res.status(401).json({ error: 'Not authenticated' });
  }

  const service = getCredentialService();
  const masked = await service.getMaskedCredentialsForUser(req.user.id);

  return res.json(masked);
});

// PUT /api/user/credentials - Update credentials for current user
router.put('/credentials', async (req: AuthenticatedRequest, res: Response) => {
  if (!req.user) {
    return res.status(401).json({ error: 'Not authenticated' });
  }

  const { anthropicKey, anthropicOAuthToken, openaiKey, googleKey } = req.body;

  const service = getCredentialService();
  await service.updateCredentialsForUser(req.user.id, {
    anthropicKey,
    anthropicOAuthToken,
    openaiKey,
    googleKey,
  });

  const masked = await service.getMaskedCredentialsForUser(req.user.id);
  return res.json({ success: true, credentials: masked });
});

// GET /api/user/auth-mode/:provider - Get auth mode for provider
router.get('/auth-mode/:provider', async (req: AuthenticatedRequest, res: Response) => {
  if (!req.user) {
    return res.status(401).json({ error: 'Not authenticated' });
  }

  const { provider } = req.params;
  if (provider !== 'anthropic' && provider !== 'openai') {
    return res.status(400).json({ error: 'Invalid provider' });
  }

  const service = getCredentialService();
  const mode = await service.getAuthModeForUser(req.user.id, provider);

  return res.json({ provider, mode });
});

// PUT /api/user/auth-mode/:provider - Set auth mode for provider
router.put('/auth-mode/:provider', async (req: AuthenticatedRequest, res: Response) => {
  if (!req.user) {
    return res.status(401).json({ error: 'Not authenticated' });
  }

  const { provider } = req.params;
  const { mode } = req.body;

  if (provider !== 'anthropic' && provider !== 'openai') {
    return res.status(400).json({ error: 'Invalid provider' });
  }

  if (mode !== 'auth_token' && mode !== 'api_key') {
    return res.status(400).json({ error: 'Invalid mode' });
  }

  const service = getCredentialService();
  await service.updateCredentialsForUser(req.user.id, {
    [provider === 'anthropic' ? 'anthropicAuthMode' : 'openaiAuthMode']: mode,
  });

  return res.json({ success: true, provider, mode });
});

export function createUserCredentialRoutes() {
  return router;
}
```

**Register in server** (`apps/server/src/index.ts`):

```typescript
import { createUserCredentialRoutes } from './routes/user-credentials';

// After auth middleware
app.use('/api/user', createUserCredentialRoutes());
```

### 8. Frontend Settings UI

**File to Create**: `apps/ui/src/components/views/settings-view/account/my-api-keys.tsx`

```tsx
import { useState, useEffect } from 'react';
import { useAuthStore } from '../../../../store/auth-store';

interface MaskedCredential {
  configured: boolean;
  masked: string;
}

export function MyApiKeys() {
  const user = useAuthStore((s) => s.user);
  const [credentials, setCredentials] = useState<Record<string, MaskedCredential>>({});
  const [loading, setLoading] = useState(true);
  const [editingKey, setEditingKey] = useState<string | null>(null);
  const [newKeyValue, setNewKeyValue] = useState('');

  useEffect(() => {
    fetchCredentials();
  }, []);

  async function fetchCredentials() {
    setLoading(true);
    try {
      const res = await fetch('/api/user/credentials', { credentials: 'include' });
      const data = await res.json();
      setCredentials(data);
    } catch (error) {
      console.error('Failed to fetch credentials:', error);
    } finally {
      setLoading(false);
    }
  }

  async function saveKey(keyName: string) {
    try {
      await fetch('/api/user/credentials', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ [keyName]: newKeyValue }),
      });
      setEditingKey(null);
      setNewKeyValue('');
      fetchCredentials();
    } catch (error) {
      console.error('Failed to save key:', error);
    }
  }

  if (loading) {
    return <div>Loading...</div>;
  }

  const providers = [
    { key: 'anthropicKey', label: 'Anthropic API Key' },
    { key: 'openaiKey', label: 'OpenAI API Key' },
  ];

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-medium">My API Keys</h3>
      <p className="text-sm text-muted-foreground">
        Your personal API keys. These are used when you run agents.
      </p>

      {providers.map(({ key, label }) => (
        <div key={key} className="flex items-center justify-between p-4 border rounded">
          <div>
            <div className="font-medium">{label}</div>
            <div className="text-sm text-muted-foreground">
              {credentials[key]?.configured ? credentials[key].masked : 'Not configured'}
            </div>
          </div>

          {editingKey === key ? (
            <div className="flex gap-2">
              <input
                type="password"
                value={newKeyValue}
                onChange={(e) => setNewKeyValue(e.target.value)}
                placeholder="Enter new key"
                className="border rounded px-2 py-1"
              />
              <button onClick={() => saveKey(key)}>Save</button>
              <button onClick={() => setEditingKey(null)}>Cancel</button>
            </div>
          ) : (
            <button onClick={() => setEditingKey(key)}>
              {credentials[key]?.configured ? 'Update' : 'Add'}
            </button>
          )}
        </div>
      ))}
    </div>
  );
}
```

**Integrate into Account Section** (`apps/ui/src/components/views/settings-view/account/account-section.tsx`):

```tsx
import { MyApiKeys } from './my-api-keys';

export function AccountSection() {
  return (
    <div className="space-y-8">
      {/* Existing account content */}

      <hr />

      {/* Add My API Keys section */}
      <MyApiKeys />
    </div>
  );
}
```

---

## Environment Variables

**Add to `.env.example`**:

```bash
# Encryption key for user credentials (32 bytes = 64 hex chars)
# Generate with: node -e "console.log(require('crypto').randomBytes(32).toString('hex'))"
AUTOMAKER_ENCRYPTION_KEY=
```

---

## Testing Checklist

### Unit Tests

- [ ] `encrypt()` produces different output for same input (random IV)
- [ ] `decrypt()` recovers original value
- [ ] `CredentialService.getCredentialsForUser()` returns user credentials
- [ ] `CredentialService.getCredentialsForUser()` falls back to global
- [ ] Credentials are encrypted in database

### Integration Tests

- [ ] PUT `/api/user/credentials` stores encrypted credentials
- [ ] GET `/api/user/credentials` returns masked values
- [ ] Agent execution uses user's API key
- [ ] User A's key is not visible to User B

### Security Tests

- [ ] Database contains only encrypted credential values
- [ ] API never returns raw API keys
- [ ] Missing AUTOMAKER_ENCRYPTION_KEY shows warning

---

## Rollback Plan

1. Remove `UserCredentials` model from Prisma schema
2. Remove encryption service
3. Remove credential service
4. Revert agent-service.ts credential resolution
5. Remove MyApiKeys UI component

---

## Success Criteria

Phase 2 is complete when:

1. User can add/update their own Anthropic API key
2. User's API key is stored encrypted in database
3. Agent runs use the requesting user's API key
4. User A cannot see User B's credentials
5. Missing user credentials fall back to global credentials

---

## Notes for Downstream Phases

### For Phase 3 (Knowledge Hub Sync)

- User context is now available in agent execution
- Can use `userId` for `createdBy` attribution

### For Phase 4 (OAuth)

- OAuth tokens will also be stored per-user
- `anthropicOAuthToken` field already exists

### For Phase 5 (Deploy)

- Must set `AUTOMAKER_ENCRYPTION_KEY` in production
- Consider key rotation strategy
