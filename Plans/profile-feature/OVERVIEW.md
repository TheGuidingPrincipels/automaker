# Multi-User Profile Feature - Implementation Overview

> **Status**: Planning
> **Created**: January 2026
> **Target**: 3-user team with shared knowledge, individual API keys

## Executive Summary

This document provides the master plan for implementing multi-user profile support in Automaker. The goal is to enable 3 team members to use the same Automaker instance simultaneously, each with their own API keys/auth tokens, while sharing a common knowledge base.

## Table of Contents

1. [Goals & Requirements](#goals--requirements)
2. [Architecture Decision](#architecture-decision)
3. [Current System State](#current-system-state)
4. [Implementation Phases](#implementation-phases)
5. [Phase Dependencies](#phase-dependencies)
6. [File Modification Map](#file-modification-map)
7. [Testing Strategy](#testing-strategy)
8. [Rollback Strategy](#rollback-strategy)

---

## Goals & Requirements

### Primary Goals

| Goal                                                 | Priority | Phase  |
| ---------------------------------------------------- | -------- | ------ |
| Multiple users can log in with unique identities     | Critical | 1      |
| Each user has their own API keys (Anthropic, OpenAI) | Critical | 2      |
| Knowledge Hub is synchronized across all users       | High     | 3      |
| Agents can store/retrieve shared learnings           | High     | 3      |
| Google OAuth or email/password authentication        | Medium   | 4      |
| Feature locking/warnings for concurrent edits        | Low      | Future |

### Non-Goals (Out of Scope)

- Per-user project isolation (users share same projects)
- Multi-tenant organization support (single team only)
- Fine-grained permissions (all users are equal)
- Real-time collaborative editing (async is sufficient)

### Success Criteria

1. 3 users can be logged in simultaneously
2. User A's API key is not visible to User B
3. Knowledge created by User A appears for User B within 5 seconds
4. System handles 3 concurrent agent runs without degradation

---

## Architecture Decision

### Chosen Approach: Single Server with User Profiles

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AUTOMAKER SERVER (Single Instance)                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    AUTHENTICATION LAYER (Phase 1+4)                   │  │
│  │  - User registration/login (email+password initially)                 │  │
│  │  - Session tokens bound to user IDs                                   │  │
│  │  - Google OAuth (Phase 4)                                             │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌────────────────────────┐        ┌────────────────────────────────────┐  │
│  │   PER-USER DATA        │        │       SHARED DATA                   │  │
│  │   (Phase 2)            │        │       (Phase 3)                     │  │
│  ├────────────────────────┤        ├────────────────────────────────────┤  │
│  │ • API Keys (encrypted) │        │ • Knowledge Hub (blueprints,       │  │
│  │ • Auth Tokens          │        │   entries, learnings)              │  │
│  │ • User Preferences     │        │ • Custom Agents                    │  │
│  │ • Agent Sessions       │        │ • Systems                          │  │
│  │                        │        │ • Project Features                 │  │
│  └────────────────────────┘        └────────────────────────────────────┘  │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                         STORAGE LAYER                                 │  │
│  │  SQLite Database (users, credentials, sessions, audit_log)            │  │
│  │  File System (team storage, project files, images)                    │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Why Single Server Over Separate Instances

| Factor                 | Single Server          | Separate VMs          |
| ---------------------- | ---------------------- | --------------------- |
| Knowledge Sharing      | Native (same database) | Complex sync required |
| Implementation Time    | ~60-70 hours           | ~95-110 hours         |
| Monthly Cost (Hetzner) | ~72 EUR                | ~48 EUR               |
| Operational Complexity | Low                    | Medium                |

**Decision**: Knowledge sharing is the primary requirement, making single server the clear choice.

---

## Current System State

### Authentication (What Exists)

- Single API key per server instance (auto-generated)
- Session tokens stored in `Map<string, { createdAt, expiresAt }>`
- No user identity - sessions authenticate requests, not users
- Electron mode uses `X-API-Key` header
- Web mode uses `automaker_session` cookie

### Credential Flow (How Agents Get API Keys)

```
credentials.json → SettingsService.getCredentials() → ExecuteOptions.credentials → Provider.buildEnv() → Claude SDK
```

**Critical Finding**: Credentials are resolved at execution time, not environment startup. This makes per-user credentials feasible without process isolation.

### Storage (Current Structure)

```
DATA_DIR/
├── settings.json           # Global settings (SHARED)
├── credentials.json        # API keys (SHARED - must change)
├── .api-key               # Server auth key
├── .sessions              # Session tokens (no user binding)
├── sessions-metadata.json # Agent session list
├── agent-sessions/        # Conversation histories
└── team/                  # Shared team resources (KEEP SHARED)
    ├── agents/
    ├── systems/
    └── knowledge/
```

### Key Files to Understand

| File                                           | Purpose             | Multi-User Impact      |
| ---------------------------------------------- | ------------------- | ---------------------- |
| `apps/server/src/lib/auth.ts`                  | Session management  | Add userId to sessions |
| `apps/server/src/services/settings-service.ts` | Credentials storage | Per-user credentials   |
| `apps/server/src/providers/claude-provider.ts` | API key resolution  | Use user's credentials |
| `apps/server/src/services/agent-service.ts`    | Agent execution     | Pass userId through    |
| `apps/ui/src/store/auth-store.ts`              | Frontend auth state | Add user object        |

---

## Implementation Phases

### Phase Overview

| Phase | Name                 | Duration  | Dependencies | Output                                           |
| ----- | -------------------- | --------- | ------------ | ------------------------------------------------ |
| **1** | User Foundation      | 1-2 weeks | None         | Users can register/login, sessions tied to users |
| **2** | Per-User Credentials | 1 week    | Phase 1      | Each user manages own API keys                   |
| **3** | Knowledge Hub Sync   | 1 week    | Phase 1      | Real-time sync of shared knowledge               |
| **4** | OAuth Authentication | 1 week    | Phase 1      | Google sign-in option                            |
| **5** | Polish & Deploy      | 1 week    | Phases 1-4   | Production-ready on Hetzner                      |

### Phase Documents

Each phase has its own detailed document:

- [PHASE-1-USER-FOUNDATION.md](./PHASE-1-USER-FOUNDATION.md) - User types, SQLite, session binding
- [PHASE-2-PER-USER-CREDENTIALS.md](./PHASE-2-PER-USER-CREDENTIALS.md) - Encrypted credential storage
- [PHASE-3-KNOWLEDGE-HUB-SYNC.md](./PHASE-3-KNOWLEDGE-HUB-SYNC.md) - WebSocket sync, attribution
- [PHASE-4-OAUTH-AUTHENTICATION.md](./PHASE-4-OAUTH-AUTHENTICATION.md) - Google OAuth integration
- [PHASE-5-DEPLOY.md](./PHASE-5-DEPLOY.md) - Hetzner deployment, monitoring

---

## Phase Dependencies

```
                    ┌─────────────────┐
                    │   PHASE 1       │
                    │ User Foundation │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
              ▼              ▼              ▼
    ┌─────────────────┐ ┌─────────────┐ ┌─────────────────┐
    │    PHASE 2      │ │   PHASE 3   │ │    PHASE 4      │
    │ Per-User Creds  │ │ Knowledge   │ │     OAuth       │
    └────────┬────────┘ │    Sync     │ └────────┬────────┘
             │          └──────┬──────┘          │
             │                 │                 │
             └─────────────────┼─────────────────┘
                               │
                               ▼
                    ┌─────────────────┐
                    │    PHASE 5      │
                    │     Deploy      │
                    └─────────────────┘
```

### Dependency Rules

- **Phase 1 MUST complete before any other phase**
- Phases 2, 3, 4 can run in parallel after Phase 1
- Phase 5 requires all previous phases complete

---

## File Modification Map

### Phase 1 - User Foundation

**New Files:**

```
libs/types/src/user.ts                    # User type definitions
apps/server/src/services/user-service.ts  # User CRUD operations
apps/server/src/lib/database.ts           # SQLite connection
prisma/schema.prisma                      # Database schema
```

**Modified Files:**

```
apps/server/src/lib/auth.ts               # Add userId to sessions
apps/server/src/routes/auth/index.ts      # Registration endpoint
apps/server/src/index.ts                  # Database initialization
apps/ui/src/store/auth-store.ts           # Add user state
apps/ui/src/components/views/login-view.tsx # Registration form
libs/types/src/index.ts                   # Export user types
```

### Phase 2 - Per-User Credentials

**New Files:**

```
apps/server/src/lib/encryption.ts         # AES-256 encryption
apps/server/src/services/credential-service.ts # Per-user credentials
```

**Modified Files:**

```
apps/server/src/services/settings-service.ts   # getCredentials(userId)
apps/server/src/services/agent-service.ts      # Pass userId to providers
apps/server/src/services/auto-mode-service.ts  # Pass userId through
apps/server/src/providers/claude-provider.ts   # Resolve user credentials
apps/ui/src/components/views/settings-view/api-keys/ # My API Keys UI
```

### Phase 3 - Knowledge Hub Sync

**New Files:**

```
apps/ui/src/hooks/queries/use-knowledge.ts     # Query hooks
apps/ui/src/hooks/mutations/use-knowledge-mutations.ts
```

**Modified Files:**

```
libs/types/src/event.ts                        # Knowledge events
apps/server/src/services/knowledge-service.ts  # Emit events
apps/server/src/lib/team-storage.ts           # Add createdBy
apps/ui/src/components/views/knowledge-hub-page/  # Replace mock data
apps/ui/src/components/views/knowledge-section-page/ # Connect to API
apps/ui/src/lib/query-keys.ts                 # Knowledge query keys
```

### Phase 4 - OAuth Authentication

**New Files:**

```
apps/server/src/routes/auth/oauth.ts      # OAuth routes
apps/ui/src/routes/auth.callback.tsx      # OAuth callback page
apps/ui/src/components/auth/oauth-buttons.tsx
```

**Modified Files:**

```
apps/server/src/index.ts                  # Register OAuth routes
apps/ui/src/components/views/login-view.tsx # Add OAuth buttons
package.json                              # Add passport dependencies
```

---

## Testing Strategy

### Phase 1 Tests

- [ ] User registration creates user in database
- [ ] Login returns session with userId
- [ ] Authenticated requests have `req.user` populated
- [ ] Expired sessions are rejected

### Phase 2 Tests

- [ ] User A's API key stored encrypted
- [ ] User B cannot see User A's credentials
- [ ] Agent runs use requesting user's API key
- [ ] Missing user credentials fall back to global

### Phase 3 Tests

- [ ] Knowledge created by User A visible to User B
- [ ] WebSocket broadcasts knowledge changes
- [ ] createdBy attribution shows correct user

### Phase 4 Tests

- [ ] Google OAuth flow completes successfully
- [ ] OAuth creates new user on first login
- [ ] OAuth links to existing user by email

### Integration Tests

- [ ] 3 concurrent users logged in
- [ ] Each user runs feature with own API key
- [ ] Knowledge changes sync between all users

---

## Rollback Strategy

### Database Rollback

```bash
# Each phase creates migration files
# Rollback with:
npx prisma migrate reset --skip-seed
```

### Feature Flags

```typescript
// Environment-based feature flags
const MULTI_USER_ENABLED = process.env.AUTOMAKER_MULTI_USER === 'true';
const OAUTH_ENABLED = process.env.AUTOMAKER_OAUTH === 'true';
```

### Backward Compatibility

1. **Single-user mode**: System works without any users (legacy mode)
2. **Default user**: Existing data assigned to "system" user
3. **Credential fallback**: If user has no credentials, use global

---

## Resource Estimates

### Development Time

| Phase     | Optimistic | Expected | Pessimistic |
| --------- | ---------- | -------- | ----------- |
| Phase 1   | 15h        | 20h      | 30h         |
| Phase 2   | 10h        | 15h      | 20h         |
| Phase 3   | 8h         | 12h      | 18h         |
| Phase 4   | 10h        | 15h      | 20h         |
| Phase 5   | 5h         | 8h       | 12h         |
| **Total** | **48h**    | **70h**  | **100h**    |

### Server Resources (Hetzner CPX41)

- 16 vCPU, 32GB RAM, 360GB SSD
- ~72 EUR/month
- Supports 3 users with concurrent agent runs

---

## Open Questions Log

Track questions that arise during implementation:

| Date | Question                                        | Status | Resolution |
| ---- | ----------------------------------------------- | ------ | ---------- |
| -    | Should OAuth sessions have different lifetimes? | Open   | -          |
| -    | How to handle credential migration from global? | Open   | -          |
| -    | Should features track which user created them?  | Open   | -          |

---

## Version History

| Version | Date     | Changes                   |
| ------- | -------- | ------------------------- |
| 1.0     | Jan 2026 | Initial planning document |

---

## How to Use This Document

1. **Before starting a phase**: Read the overview and the specific phase document
2. **During implementation**: Check file modification map for affected files
3. **After completing a phase**: Run tests, update this document with lessons learned
4. **If blocked**: Check Open Questions Log, add new questions

## Related Documents

- [AUTHENTICATION-SYSTEM.md](../../docs/AUTHENTICATION-SYSTEM.md) - Current auth implementation
- [MULTI-USER-ARCHITECTURE-ANALYSIS.md](../../docs/MULTI-USER-ARCHITECTURE-ANALYSIS.md) - Detailed analysis
- [possible-improvements/002-multi-user-authentication-system.md](../../possible-improvements/002-multi-user-authentication-system.md) - Original improvement proposal
