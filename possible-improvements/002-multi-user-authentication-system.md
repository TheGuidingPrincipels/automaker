# Multi-User Authentication System

**Status:** Planned
**Priority:** High
**Impact:** Enables team collaboration, user tracking, cloud deployment
**Date Added:** 2026-01-21
**Related Upstream:** Not applicable (fork-specific feature)

## Summary

Replace the current single-API-key authentication with a multi-user system supporting GitHub OAuth, per-user profiles, and activity tracking. This enables team collaboration, user-specific credentials, and proper git commit attribution.

## Current State

| Aspect            | Current                   | Target                             |
| ----------------- | ------------------------- | ---------------------------------- |
| Authentication    | Single API key per server | GitHub OAuth + JWT sessions        |
| User Identity     | None                      | User profiles with git identity    |
| API Keys          | Global Anthropic key      | Per-user API keys (encrypted)      |
| Git Attribution   | Hardcoded "Automaker"     | User-initiated with Co-Authored-By |
| Activity Tracking | None                      | Event sourcing with analytics      |
| Multi-Instance    | Not supported             | Container-per-user with shared DB  |

## Architecture

### Phase 1: Local Development (Quick Fix)

Enable `AUTOMAKER_AUTO_LOGIN=true` for frictionless local development. No code changes required.

### Phase 2: User System Foundation

```
┌─────────────────────────────────────────────────┐
│                  Frontend (UI)                  │
│  - "Login with GitHub" button                   │
│  - User profile display in header               │
│  - Per-user settings page                       │
└──────────────────────┬──────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────┐
│                  Backend (Server)               │
│  - GitHub OAuth callback                        │
│  - JWT token issuance                           │
│  - User-aware middleware                        │
│  - Per-user credential storage (encrypted)      │
└──────────────────────┬──────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────┐
│               Database (PostgreSQL)             │
│  - users table                                  │
│  - activity_events table                        │
│  - team_storage table                           │
└─────────────────────────────────────────────────┘
```

### Phase 3: Cloud Deployment (Multi-Instance)

```
┌─────────────────────────────────────────────────┐
│              Load Balancer (Nginx)              │
│         (Routes users to their instances)       │
└────────────────────┬────────────────────────────┘
                     │
         ┌───────────┼───────────┐
         │           │           │
    ┌────▼────┐ ┌────▼────┐ ┌───▼─────┐
    │ User 1  │ │ User 2  │ │ User 3  │
    │Container│ │Container│ │Container│
    │         │ │         │ │         │
    │ DATA_DIR│ │ DATA_DIR│ │ DATA_DIR│
    │ (volume)│ │ (volume)│ │ (volume)│
    └────┬────┘ └────┬────┘ └────┬────┘
         │           │           │
         └───────────┼───────────┘
                     │
              ┌──────▼──────┐
              │  PostgreSQL │
              │ (Team Data) │
              │  - Users    │
              │  - Agents   │
              │  - Systems  │
              │  - Memory   │
              └─────────────┘
```

**Why Multi-Instance (not Multi-Tenant):**

- Git worktree conflicts avoided (separate DATA_DIR per user)
- Terminal session isolation
- Resource isolation (one user's heavy operation doesn't block others)
- Matches current single-user architecture
- Easier to implement than deep multi-tenant refactoring

## Implementation Plan

### Phase 1: Quick Fix (Immediate)

**Goal:** Remove login friction for local development

- [x] Enable `AUTOMAKER_AUTO_LOGIN=true` environment variable
- [ ] Document in README/setup guide

### Phase 2: User System (2-3 weeks)

**Goal:** Add user identity and authentication

#### Week 1: Core Infrastructure

1. **Add User type** (`libs/types/src/user.ts`)

   ```typescript
   export interface User {
     id: string;
     email: string;
     name: string;
     avatarUrl?: string;
     githubId?: string;
     gitName?: string; // For git commits
     gitEmail?: string; // For git commits
     anthropicApiKey?: string; // Encrypted
     role: 'admin' | 'member';
     createdAt: string;
     lastLoginAt: string;
   }
   ```

2. **Add PostgreSQL/SQLite support**
   - Use Prisma ORM for type-safe queries
   - Schema: Users, Sessions, ActivityEvents
   - Migration path from file-based storage

3. **Implement GitHub OAuth**
   - Register OAuth app on GitHub
   - Install `passport` + `passport-github2`
   - Create `/api/auth/github` and `/api/auth/github/callback` routes
   - Issue JWT tokens on successful login

#### Week 2: Integration

4. **Update auth middleware**

   ```typescript
   // Extract user from JWT instead of single API key
   function authMiddleware(req, res, next) {
     const token = req.cookies.auth_token || req.headers.authorization?.split(' ')[1];
     const decoded = jwt.verify(token, process.env.JWT_SECRET);
     req.user = await userService.findById(decoded.userId);
     next();
   }
   ```

5. **Add per-user API keys**
   - Settings page: "My Anthropic API Key"
   - Encrypt before storage (AES-256)
   - Test key validity on save

6. **Update git attribution**
   ```typescript
   // In worktree creation/commit
   const gitEnv = {
     GIT_AUTHOR_NAME: user.gitName || user.name,
     GIT_AUTHOR_EMAIL: user.gitEmail || user.email,
     GIT_COMMITTER_NAME: user.gitName || user.name,
     GIT_COMMITTER_EMAIL: user.gitEmail || user.email,
   };
   ```

#### Week 3: UI & Polish

7. **Update frontend**
   - Add "Login with GitHub" button
   - Show logged-in user (avatar, name) in header
   - Add logout functionality
   - User settings page (git identity, API key)

8. **Populate `createdBy` fields**
   - Feature, CustomAgent, System already have `createdBy?: string`
   - Populate with `req.user.id` on creation
   - Filter by user where appropriate

### Phase 3: Activity Tracking (1-2 weeks)

**Goal:** Track who did what

1. **Activity Event Types**

   ```typescript
   type ActivityEventType =
     | 'feature.created'
     | 'feature.completed'
     | 'feature.failed'
     | 'feature.committed'
     | 'feature.merged'
     | 'agent.executed'
     | 'system.run'
     | 'user.login'
     | 'user.logout';
   ```

2. **Git Commit Attribution**

   ```bash
   # Commit message format
   feat: implement user dashboard

   Initiated-By: Ruben <ruben@example.com>
   Co-Authored-By: AutoMaker AI <ai@automaker.dev>
   ```

3. **Analytics Dashboard**
   - Features per user
   - Success/failure rate
   - Lines of code added/removed
   - Model usage per user

### Phase 4: Cloud Deployment (2-4 weeks)

**Goal:** Deploy for team access

1. **Docker Compose multi-instance**

   ```yaml
   services:
     postgres:
       image: postgres:16-alpine
     automaker-user1:
       image: automaker:latest
       environment:
         - USER_ID=user1
       volumes:
         - user1-data:/data
     automaker-user2:
       # ... similar
     nginx:
       image: nginx:alpine
       # Session-sticky routing
   ```

2. **Database migration**
   - Move TeamStorage from files to PostgreSQL
   - Add `TEAM_STORAGE_TYPE=database` option

3. **Deploy to Hetzner/DigitalOcean**
   - Single VPS (~$15-25/month for 3-5 users)
   - SSL via Let's Encrypt
   - Automated backups

## Database Schema

```sql
-- Users
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email VARCHAR(255) UNIQUE NOT NULL,
  name VARCHAR(255) NOT NULL,
  avatar_url TEXT,
  github_id VARCHAR(50) UNIQUE,
  git_name VARCHAR(255),
  git_email VARCHAR(255),
  anthropic_api_key TEXT, -- Encrypted
  role VARCHAR(20) DEFAULT 'member',
  created_at TIMESTAMP DEFAULT NOW(),
  last_login_at TIMESTAMP
);

-- Activity Events (event sourcing)
CREATE TABLE activity_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  event_type VARCHAR(50) NOT NULL,
  user_id UUID REFERENCES users(id),
  project_path TEXT,
  timestamp TIMESTAMP DEFAULT NOW(),
  metadata JSONB,
  INDEX idx_user_timestamp (user_id, timestamp)
);

-- Team Storage (replaces file-based)
CREATE TABLE team_storage (
  collection VARCHAR(50) NOT NULL,
  id VARCHAR(255) NOT NULL,
  data JSONB NOT NULL,
  created_by UUID REFERENCES users(id),
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  PRIMARY KEY (collection, id)
);
```

## Environment Variables

| Variable                     | Description                        | Default                |
| ---------------------------- | ---------------------------------- | ---------------------- |
| `AUTOMAKER_AUTO_LOGIN`       | Skip login for dev                 | `false`                |
| `AUTOMAKER_DISABLE_AUTH`     | Disable auth entirely              | `false`                |
| `GITHUB_OAUTH_CLIENT_ID`     | GitHub OAuth app ID                | Required for OAuth     |
| `GITHUB_OAUTH_CLIENT_SECRET` | GitHub OAuth secret                | Required for OAuth     |
| `JWT_SECRET`                 | Secret for JWT signing             | Required               |
| `ENCRYPTION_KEY`             | 32-byte key for API key encryption | Required               |
| `DATABASE_URL`               | PostgreSQL connection URL          | Optional (uses SQLite) |
| `TEAM_STORAGE_TYPE`          | `file` or `database`               | `file`                 |

## Cost Estimates

| Deployment                | Monthly Cost | Best For         |
| ------------------------- | ------------ | ---------------- |
| Local dev (current)       | $0           | Single developer |
| Single VPS (Hetzner)      | $15-25       | 3-5 users        |
| DigitalOcean App Platform | $75-150      | Managed hosting  |
| AWS ECS Fargate           | $150-300     | Enterprise scale |

## Security Considerations

- **API Key Encryption**: AES-256-CBC at rest
- **JWT Tokens**: RS256 signing, 30-day expiration
- **HTTP-Only Cookies**: Prevent XSS token theft
- **Rate Limiting**: 5 login attempts per minute per IP
- **GitHub OAuth**: No passwords to manage
- **GDPR Compliance**: User data export/deletion endpoints

## Files to Modify

### New Files

- `libs/types/src/user.ts` - User type definitions
- `libs/types/src/activity.ts` - Activity event types
- `apps/server/src/routes/auth/github.ts` - GitHub OAuth routes
- `apps/server/src/services/user-service.ts` - User CRUD
- `apps/server/src/services/activity-service.ts` - Activity logging
- `apps/ui/src/components/views/login-view-oauth.tsx` - OAuth login UI
- `apps/ui/src/routes/analytics.tsx` - Analytics dashboard

### Modified Files

- `apps/server/src/lib/auth.ts` - Add user-aware middleware
- `apps/server/src/routes/worktree/` - Pass user to git operations
- `apps/server/src/services/feature-loader.ts` - Populate `createdBy`
- `apps/ui/src/components/top-bar.tsx` - Show logged-in user
- `apps/ui/src/store/auth-store.ts` - Add user state

## Success Criteria

- [ ] Users can login via GitHub OAuth
- [ ] Each user has their own Anthropic API key
- [ ] Git commits show who initiated the feature
- [ ] Activity dashboard shows user metrics
- [ ] 3-5 users can work simultaneously on cloud deployment
- [ ] Team resources (agents, systems) are shared via database

## When to Implement

- **Phase 1 (Quick Fix)**: Immediate
- **Phase 2 (User System)**: When team collaboration needed
- **Phase 3 (Activity Tracking)**: After Phase 2
- **Phase 4 (Cloud Deployment)**: When remote access needed

## References

- [GitHub OAuth Documentation](https://docs.github.com/en/developers/apps/building-oauth-apps)
- [Passport.js GitHub Strategy](http://www.passportjs.org/packages/passport-github2/)
- [Prisma ORM](https://www.prisma.io/)
- [JWT Best Practices](https://datatracker.ietf.org/doc/html/rfc8725)
