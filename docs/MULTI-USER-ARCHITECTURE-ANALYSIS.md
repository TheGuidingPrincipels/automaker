# Multi-User Architecture & Scaling Analysis

> Technical Analysis Document v1.0
> Last Updated: January 2026

## Executive Summary

This document analyzes the feasibility and recommended approach for converting Automaker from a single-user application to a multi-user system supporting 3+ team members with shared knowledge capabilities.

### Key Findings

| Question                                  | Answer                            |
| ----------------------------------------- | --------------------------------- |
| **How hard to implement multi-user?**     | Medium-Hard (~60-90 hours)        |
| **Best architecture?**                    | Single server with user profiles  |
| **Can 3 users run overnight batch jobs?** | Yes, comfortably on 32GB server   |
| **Is shared knowledge possible?**         | Yes, already designed for it      |
| **Recommended server**                    | Hetzner CPX41 (16 vCPU, 32GB RAM) |
| **Monthly cost**                          | ~72 EUR (~$78 USD)                |

### Recommendation

**Single server with multi-user profiles** is recommended over separate instances because:

1. Knowledge sharing is native (no sync complexity)
2. Resource usage is lower than expected
3. Simpler to implement and maintain
4. Easy to migrate to multi-instance later if needed

---

## Table of Contents

1. [Resource Consumption Analysis](#resource-consumption-analysis)
2. [Architecture Options](#architecture-options)
3. [Shared Knowledge Requirements](#shared-knowledge-requirements)
4. [Implementation Complexity](#implementation-complexity)
5. [Overnight Batch Processing](#overnight-batch-processing)
6. [Cost Analysis](#cost-analysis)
7. [Recommended Approach](#recommended-approach)
8. [Implementation Roadmap](#implementation-roadmap)

---

## Resource Consumption Analysis

### Key Discovery: Lightweight Architecture

Investigation revealed that Automaker's agent system is more lightweight than initially assumed:

| Misconception                         | Reality                                              |
| ------------------------------------- | ---------------------------------------------------- |
| "Each agent spawns a Node.js process" | Agents run **in-process** via Claude SDK async calls |
| "Heavy CPU usage during agent runs"   | CPU is **I/O bound** (waiting for API responses)     |
| "Memory scales linearly with agents"  | Partially true - depends on conversation history     |

### Resource Profile Per User

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    RESOURCE PROFILE PER USER                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  BASE FOOTPRINT (always running):                                           │
│  ├── Node.js Runtime .............. 100-200 MB                             │
│  ├── Express + WebSocket .......... 50-100 MB                              │
│  └── Idle Server .................. ~250-300 MB total                      │
│                                                                             │
│  PER ACTIVE AGENT (additive):                                               │
│  ├── Claude SDK context ........... 200-500 MB                             │
│  ├── Conversation history ......... 50-100 MB (grows over time)            │
│  ├── Git worktree ................. 100-300 MB (file buffers)              │
│  └── Per-agent total .............. ~400-900 MB                            │
│                                                                             │
│  PEAK USAGE (large context, images):                                        │
│  └── Up to 2-4 GB per agent                                                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Memory Consumption Breakdown

| Component            | Base           | Per Active Agent  | Peak        |
| -------------------- | -------------- | ----------------- | ----------- |
| Node.js Runtime      | 100-200 MB     | -                 | -           |
| Express + WebSocket  | 50-100 MB      | -                 | -           |
| Agent SDK Core       | 50-150 MB      | +200-500 MB       | +1-2 GB     |
| Git Worktree         | -              | +100-300 MB       | +500 MB     |
| Conversation History | -              | +50-100 MB        | +500 MB     |
| File Buffers         | -              | +50-200 MB        | +1 GB       |
| **TOTAL**            | **200-450 MB** | **+400-1,100 MB** | **+3-4 GB** |

### CPU Usage Patterns

| Phase              | CPU Usage | Duration       | Pattern                         |
| ------------------ | --------- | -------------- | ------------------------------- |
| Idle               | 0-5%      | Most of time   | Event loop waiting              |
| API Call           | 5-10%     | 2-10 seconds   | HTTP request/response           |
| Streaming Response | 10-30%    | 20-120 seconds | WebSocket parsing               |
| Git Operations     | 30-80%    | 5-30 seconds   | `git diff`, `git apply`         |
| File Processing    | 50-90%    | Variable       | Image resizing, context loading |

**Key Insight**: CPU is burst-heavy, not sustained. Most time is spent waiting for Claude API responses.

### Actual Bottleneck: API Rate Limits

The **Anthropic API rate limit** is the actual bottleneck, not local resources:

- Auto-mode self-pauses after 3 consecutive failures (including rate limits)
- Local resources are rarely the limiting factor

---

## Architecture Options

### Option A: Single Large Server (Recommended)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                  SINGLE SERVER ARCHITECTURE                                  │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    ONE AUTOMAKER INSTANCE                           │   │
│  │                                                                     │   │
│  │   User A ─────┐                                                     │   │
│  │               │      ┌─────────────────────┐                        │   │
│  │   User B ─────┼─────►│  Shared Process     │                        │   │
│  │               │      │  (Express + Node)    │                        │   │
│  │   User C ─────┘      │  8-16 GB RAM        │                        │   │
│  │                      └──────────┬──────────┘                        │   │
│  │                                 │                                   │   │
│  │              ┌──────────────────┼──────────────────┐               │   │
│  │              ▼                  ▼                  ▼               │   │
│  │         [User A Data]     [User B Data]     [User C Data]         │   │
│  │         (credentials)     (credentials)     (credentials)         │   │
│  │                                                                     │   │
│  │              └──────────────────┬──────────────────┘               │   │
│  │                                 ▼                                   │   │
│  │                     [Shared Knowledge/Team Data]                   │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  Server: Hetzner CPX41 (16 vCPU, 32GB RAM) = ~72 EUR/month                 │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Pros:**

- Knowledge sharing is native (same database, same files)
- Simpler deployment (one docker-compose)
- Lower operational overhead
- No sync complexity

**Cons:**

- One crash affects all users
- Resource contention possible (mitigated by limits)
- Git worktree conflicts on same project branch
- Harder to scale beyond 5-7 users

### Option B: Multiple Instances + Shared Storage

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                 MULTI-INSTANCE ARCHITECTURE                                  │
│                                                                             │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐                    │
│  │   User A     │   │   User B     │   │   User C     │                    │
│  │   Instance   │   │   Instance   │   │   Instance   │                    │
│  │   CPX21      │   │   CPX21      │   │   CPX21      │                    │
│  │   8GB RAM    │   │   8GB RAM    │   │   8GB RAM    │                    │
│  └──────┬───────┘   └──────┬───────┘   └──────┬───────┘                    │
│         │                  │                  │                            │
│         └──────────────────┼──────────────────┘                            │
│                            │                                               │
│                            ▼                                               │
│         ┌─────────────────────────────────────────────┐                   │
│         │        SHARED INFRASTRUCTURE                 │                   │
│         │  ┌─────────────────┐  ┌─────────────────┐   │                   │
│         │  │   PostgreSQL    │  │  NFS Storage    │   │                   │
│         │  │   + Redis       │  │  (Team Data)    │   │                   │
│         │  └─────────────────┘  └─────────────────┘   │                   │
│         └─────────────────────────────────────────────┘                   │
│                                                                             │
│  Cost: 3×CPX21 + PostgreSQL + Storage = ~47-57 EUR/month                   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Pros:**

- Complete resource isolation
- One crash doesn't affect others
- Git worktree conflicts eliminated
- Linear scaling path

**Cons:**

- Knowledge sync requires additional infrastructure (NFS, Redis pub/sub)
- More complex deployment and maintenance
- Higher operational overhead
- ~25-35 additional implementation hours

### Architecture Comparison Matrix

| Criterion            | Single Server      | Multi-Instance  | Winner |
| -------------------- | ------------------ | --------------- | ------ |
| Initial Cost         | ~72 EUR            | ~52 EUR         | Multi  |
| Knowledge Sharing    | Native             | Complex         | Single |
| Implementation Time  | 60-90 hours        | 85-125 hours    | Single |
| Failure Isolation    | All users affected | 1 user affected | Multi  |
| Resource Contention  | Possible           | None            | Multi  |
| Operational Overhead | Low                | Medium          | Single |
| Scaling Path         | Limited            | Linear          | Multi  |

---

## Shared Knowledge Requirements

### Your Requirements

1. Shared knowledge base accessible by all users
2. Agent learnings stored centrally
3. Real-time sync when one user adds knowledge
4. MCP tool access for agents

### Current State

The investigation found that **TeamStorage is already designed for sharing**:

```
team/
├── knowledge/
│   ├── blueprints/     ← All users see same blueprints
│   ├── entries/        ← All users see same knowledge entries
│   └── learnings/      ← All agents contribute learnings here
├── agents/             ← Shared custom agents
└── systems/            ← Shared multi-agent systems
```

### Implementation Comparison

| Feature             | Single Server        | Multi-Instance         |
| ------------------- | -------------------- | ---------------------- |
| Knowledge Hub sync  | Free (same files)    | Needs NFS + Redis      |
| Agent learnings     | Free (same storage)  | Needs shared storage   |
| Real-time updates   | WebSocket broadcasts | Redis pub/sub required |
| MCP access          | Direct file access   | Network mount required |
| Implementation time | 10-15 hours          | 25-35 hours            |

---

## Implementation Complexity

### Components Requiring Changes

| Component                         | Difficulty | Hours       | Notes                        |
| --------------------------------- | ---------- | ----------- | ---------------------------- |
| User types & store                | Easy       | 3h          | New `libs/types/src/user.ts` |
| User service (SQLite)             | Medium     | 8h          | CRUD, lookup by email        |
| Session → User binding            | Medium     | 6h          | Modify `auth.ts`             |
| Per-user credentials              | Medium     | 8h          | Encrypted storage, AES-256   |
| Provider auth per-user            | Medium     | 6h          | Pass keys to subprocesses    |
| Google OAuth                      | Hard       | 12h         | Passport.js integration      |
| Login UI updates                  | Medium     | 6h          | OAuth button, user profile   |
| Knowledge Hub sync                | Medium     | 10h         | Connect frontend to API      |
| **Total (Single Server)**         |            | **~60h**    | Minimum viable               |
| **Additional for Multi-Instance** |            | **+25-35h** | NFS, Redis, sync             |

### Files Requiring Modification

**Core Authentication:**

- `apps/server/src/lib/auth.ts` - Add userId to sessions
- `apps/server/src/routes/auth/index.ts` - OAuth routes
- `apps/server/src/services/settings-service.ts` - Per-user credentials

**Frontend:**

- `apps/ui/src/store/auth-store.ts` - User state
- `apps/ui/src/components/views/login-view.tsx` - OAuth UI

**New Files:**

- `libs/types/src/user.ts` - User type definitions
- `apps/server/src/services/user-service.ts` - User CRUD
- Database schema (SQLite/PostgreSQL)

---

## Overnight Batch Processing

### Scenario Analysis

**3 users, each running auto-mode with 10 features overnight:**

| Configuration                 | Concurrent Agents | Memory Usage | Safe? |
| ----------------------------- | ----------------- | ------------ | ----- |
| Default (maxConcurrency=1)    | 3 total           | ~3-4 GB      | Yes   |
| Moderate (maxConcurrency=2)   | 6 total           | ~6-8 GB      | Yes   |
| Aggressive (maxConcurrency=3) | 9 total           | ~12-18 GB    | Yes   |

### Safe Limits by Server Size

| Server | RAM               | Max Concurrent Agents | Recommendation          |
| ------ | ----------------- | --------------------- | ----------------------- |
| CPX21  | 8 GB              | 3-4                   | 1 user only             |
| CPX31  | 16 GB             | 6-8                   | 2-3 users, conservative |
| CPX41  | 32 GB             | 12-15                 | 3 users, comfortable    |
| CCX33  | 32 GB (dedicated) | 15-18                 | 3 users, aggressive     |

### Memory Budget for 32GB Server

```
Memory Allocation (CPX41 - 32GB):
├── OS & base services .......... 2 GB
├── Node.js server .............. 1 GB
├── PostgreSQL .................. 2 GB
├── User A (2 concurrent agents). 2 GB
├── User B (2 concurrent agents). 2 GB
├── User C (2 concurrent agents). 2 GB
├── Peak overhead ............... 5 GB
├── Safety headroom ............. 16 GB
└── TOTAL ....................... 32 GB ✓
```

### Critical Safeguards

1. **API Rate Limiting**: Built-in (auto-pauses after 3 failures)
2. **Memory Monitoring**: Add endpoint check + alerting
3. **Worktree Cleanup**: Add auto-cleanup after feature merge
4. **Disk Space Monitoring**: Add alerts for low disk

### Recommended Resource Limits

```typescript
// Per-user resource limits
const USER_RESOURCE_LIMITS = {
  maxConcurrentFeatures: 3, // Per user limit
  maxMemoryMB: 8000, // 8GB per user
  maxWorktrees: 10, // Prevent disk exhaustion
};

// Global limits
const GLOBAL_LIMITS = {
  maxTotalConcurrentFeatures: 8, // Total across all users
  memoryWarningThreshold: 0.8, // Alert at 80% memory
  diskWarningThreshold: 0.85, // Alert at 85% disk
};
```

---

## Cost Analysis

### Option A: Single Server (Recommended)

| Component | Specification                        | Monthly Cost |
| --------- | ------------------------------------ | ------------ |
| Server    | CPX41 (16 vCPU, 32GB RAM, 360GB SSD) | 71.70 EUR    |
| Backup    | Included snapshots                   | 0 EUR        |
| **Total** |                                      | **~72 EUR**  |

### Option B: Multi-Instance

| Component     | Specification              | Monthly Cost |
| ------------- | -------------------------- | ------------ |
| User Servers  | 3× CPX21 (4 vCPU, 8GB RAM) | 32.70 EUR    |
| Database      | CPX11 (2 vCPU, 4GB RAM)    | 5.39 EUR     |
| Storage       | BX11 (100GB NFS)           | 3.81 EUR     |
| Load Balancer | Hetzner LB                 | 5.83 EUR     |
| **Total**     |                            | **~48 EUR**  |

### Cost Comparison

| Team Size | Single Server | Multi-Instance | Knowledge Sync Overhead |
| --------- | ------------- | -------------- | ----------------------- |
| 3 users   | 72 EUR        | 48 EUR         | +25-35h implementation  |
| 5 users   | 72 EUR        | 68 EUR         | Same infrastructure     |
| 10 users  | 134 EUR       | 124 EUR        | Scale storage/DB        |

**Note**: Multi-instance is cheaper but requires more implementation effort for knowledge synchronization.

---

## Recommended Approach

### Phase 1: Single Server (Month 1-3)

**Why start here:**

1. Knowledge sharing is automatic (primary requirement)
2. Sufficient resources for 3 users
3. Faster implementation (~60h vs ~95h)
4. Lower operational complexity

**Server**: Hetzner CPX41 (16 vCPU, 32GB RAM) = 72 EUR/month

### Phase 2: Add Resource Monitoring (Month 2-3)

- Memory usage alerts
- Disk space monitoring
- Per-user resource tracking
- Worktree auto-cleanup

### Phase 3: Evaluate Split (Month 4-6)

**Triggers to switch to multi-instance:**

- Memory consistently > 70% for extended periods
- Users complaining about slowdowns
- Team growing beyond 5 users
- Geographic distribution requirements

**Migration is straightforward** because:

- PostgreSQL already in place (from multi-user auth)
- TeamStorage designed for database migration
- Clear data isolation boundaries

---

## Implementation Roadmap

### Week 1-2: Foundation

- [ ] Create User types (`libs/types/src/user.ts`)
- [ ] Add SQLite with Prisma (users, credentials tables)
- [ ] Modify `auth.ts` to bind sessions to user IDs
- [ ] Create UserService for CRUD operations

### Week 3: Per-User Credentials

- [ ] Implement AES-256 encryption for API keys
- [ ] Create per-user credential storage
- [ ] Modify provider auth to use user-specific keys
- [ ] Update Settings UI for "My API Keys"

### Week 4: Knowledge Hub Sync

- [ ] Connect Knowledge Hub frontend to API
- [ ] Add WebSocket events for knowledge changes
- [ ] Implement query invalidation hooks
- [ ] Add createdBy/updatedBy attribution

### Week 5: Authentication UI

- [ ] Add Google OAuth (passport-google-oauth20)
- [ ] Update login page with OAuth button
- [ ] Add user profile display
- [ ] Implement session management

### Week 6: Deploy & Monitor

- [ ] Deploy to Hetzner CPX41
- [ ] Configure SSL (Traefik/Caddy)
- [ ] Set up monitoring (memory, disk, API usage)
- [ ] Configure backup automation

---

## Security Considerations

### Per-User Credential Encryption

```typescript
// AES-256-CBC encryption for API keys
import crypto from 'crypto';

const algorithm = 'aes-256-cbc';
const key = Buffer.from(process.env.ENCRYPTION_KEY, 'hex'); // 32 bytes

function encrypt(text: string): { encrypted: string; iv: string } {
  const iv = crypto.randomBytes(16);
  const cipher = crypto.createCipheriv(algorithm, key, iv);
  let encrypted = cipher.update(text, 'utf8', 'hex');
  encrypted += cipher.final('hex');
  return { encrypted, iv: iv.toString('hex') };
}
```

### Database Schema

```sql
CREATE TABLE users (
  id TEXT PRIMARY KEY,
  email TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  avatar_url TEXT,
  auth_provider TEXT NOT NULL, -- 'google' | 'email'
  password_hash TEXT,          -- Only for email auth
  created_at TEXT NOT NULL,
  last_login_at TEXT
);

CREATE TABLE user_credentials (
  user_id TEXT PRIMARY KEY REFERENCES users(id),
  anthropic_encrypted TEXT,
  openai_encrypted TEXT,
  encryption_iv TEXT,
  updated_at TEXT NOT NULL
);
```

---

## Monitoring & Alerting

### Health Check Endpoints

```
GET /api/health/detailed

Response:
{
  "memory": {
    "heapUsed": 524288000,
    "heapTotal": 1073741824,
    "rss": 786432000
  },
  "uptime": 86400,
  "activeAgents": 3,
  "activeWorktrees": 5
}
```

### Alert Thresholds

| Metric              | Warning | Critical |
| ------------------- | ------- | -------- |
| Memory Usage        | 70%     | 85%      |
| Disk Usage          | 75%     | 90%      |
| Active Agents       | 10      | 15       |
| API Failures (5min) | 5       | 10       |

---

## Appendix: File Locations

### Backend Files

| File                                            | Purpose               |
| ----------------------------------------------- | --------------------- |
| `apps/server/src/lib/auth.ts`                   | Core authentication   |
| `apps/server/src/services/auto-mode-service.ts` | Batch execution       |
| `apps/server/src/services/agent-service.ts`     | Agent management      |
| `apps/server/src/lib/team-storage.ts`           | Shared data storage   |
| `apps/server/src/services/knowledge-service.ts` | Knowledge Hub backend |

### Frontend Files

| File                                               | Purpose          |
| -------------------------------------------------- | ---------------- |
| `apps/ui/src/store/auth-store.ts`                  | Auth state       |
| `apps/ui/src/components/views/login-view.tsx`      | Login UI         |
| `apps/ui/src/components/views/knowledge-hub-page/` | Knowledge Hub UI |

### Configuration

| File                       | Purpose               |
| -------------------------- | --------------------- |
| `docker-compose.yml`       | Production deployment |
| `Dockerfile`               | Container build       |
| `apps/server/.env.example` | Environment variables |

---

## Decision Log

| Date     | Decision                          | Rationale                                    |
| -------- | --------------------------------- | -------------------------------------------- |
| Jan 2026 | Single server over multi-instance | Knowledge sharing priority, lower complexity |
| Jan 2026 | SQLite over PostgreSQL initially  | Simpler for 3 users, can migrate later       |
| Jan 2026 | Google OAuth + email/password     | Flexibility for team members                 |
| Jan 2026 | Hetzner CPX41                     | Best price/performance for 32GB RAM          |

---

## References

- [AUTHENTICATION-SYSTEM.md](./AUTHENTICATION-SYSTEM.md) - Current auth implementation details
- [possible-improvements/002-multi-user-authentication-system.md](../possible-improvements/002-multi-user-authentication-system.md) - Existing multi-user plan
- [Hetzner Cloud Pricing](https://www.hetzner.com/cloud) - Server costs
- [Claude Agent SDK Documentation](https://docs.anthropic.com/claude/docs/agent-sdk) - Resource usage patterns
