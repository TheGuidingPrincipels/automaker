# Multi-User Profile Feature - Progress Checklist

> Use this document to track implementation progress across all phases.
> Check items as they are completed. Update dates for significant milestones.

---

## Phase 1: User Foundation

**Status**: [ ] Not Started / [ ] In Progress / [ ] Complete
**Start Date**: \***\*\_\_\_\*\***
**End Date**: \***\*\_\_\_\*\***

### Backend

- [ ] Create `apps/server/prisma/schema.prisma` with User model (passwordHash nullable)
- [ ] Create `libs/types/src/user.ts` with User types
- [ ] Create `apps/server/src/lib/database.ts` - SQLite connection
- [ ] Create `apps/server/src/services/user-service.ts` - User CRUD
- [ ] Modify `apps/server/src/lib/auth.ts` - Bind sessions to userId (keep `.sessions` file persistence)
- [ ] Add registration endpoint to `apps/server/src/routes/auth/index.ts`
- [ ] Add `/api/auth/me` endpoint
- [ ] Initialize database in `apps/server/src/index.ts`
- [ ] Run Prisma migration (e.g. `npx prisma migrate dev --schema apps/server/prisma/schema.prisma`)

### Frontend

- [ ] Modify `apps/ui/src/store/auth-store.ts` - Add user state
- [ ] Modify `apps/ui/src/components/views/login-view.tsx` - Add registration form
- [ ] Update `apps/ui/src/lib/http-api-client.ts` - Add register/loginWithEmail functions
- [ ] Export user types from `libs/types/src/index.ts`

### Testing

- [ ] User can register with email/password
- [ ] User can login with email/password
- [ ] Session includes userId
- [ ] `req.user` populated on authenticated requests
- [ ] Legacy API key login still works

---

## Phase 2: Per-User Credentials

**Status**: [ ] Not Started / [ ] In Progress / [ ] Complete
**Start Date**: \***\*\_\_\_\*\***
**End Date**: \***\*\_\_\_\*\***

### Backend

- [ ] Create `apps/server/src/lib/encryption.ts` - AES-256 encryption
- [ ] Create `apps/server/src/services/credential-service.ts` - Per-user credentials
- [ ] Add UserCredentials model to Prisma schema
- [ ] Run `npx prisma migrate dev` for new table
- [ ] Create `apps/server/src/routes/user-credentials/index.ts` - Credential routes
- [ ] Register credential routes in server index
- [ ] Modify `apps/server/src/services/agent-service.ts` - Pass userId
- [ ] Modify `apps/server/src/services/auto-mode-service.ts` - Pass userId
- [ ] Update provider to use user credentials

### Frontend

- [ ] Create `apps/ui/src/components/views/settings-view/account/my-api-keys.tsx`
- [ ] Integrate MyApiKeys into AccountSection
- [ ] Add per-user auth mode toggle

### Configuration

- [ ] Add `AUTOMAKER_ENCRYPTION_KEY` to `.env.example`
- [ ] Document key generation in README

### Testing

- [ ] User A's API key is encrypted in database
- [ ] User B cannot see User A's credentials
- [ ] Agent runs use requesting user's API key
- [ ] Missing user credentials fall back to global

---

## Phase 3: Knowledge Hub Sync

**Status**: [ ] Not Started / [ ] In Progress / [ ] Complete
**Start Date**: \***\*\_\_\_\*\***
**End Date**: \***\*\_\_\_\*\***

### Backend

- [ ] Add knowledge event types to `libs/types/src/event.ts`
- [ ] Modify `apps/server/src/services/knowledge-service.ts` - Add EventEmitter
- [ ] Add event emission to CRUD methods
- [ ] Add `createdBy`/`updatedBy` to knowledge types
- [ ] Wire EventEmitter in server index
- [ ] Update knowledge routes to pass userId

### Frontend

- [ ] Add knowledge query keys to `apps/ui/src/lib/query-keys.ts`
- [ ] Create `apps/ui/src/hooks/queries/use-knowledge.ts` - Query hooks
- [ ] Create `apps/ui/src/hooks/mutations/use-knowledge-mutations.ts`
- [ ] Add `useKnowledgeQueryInvalidation` hook
- [ ] Update `apps/ui/src/components/views/knowledge-hub-page/index.tsx` - Remove mock data
- [ ] Update `apps/ui/src/components/views/knowledge-section-page/index.tsx` - Use API

### Testing

- [ ] Knowledge Hub shows real counts from API
- [ ] Creating knowledge updates all connected clients
- [ ] `createdBy` shows who created each entry
- [ ] Sync happens within 5 seconds

---

## Phase 4: OAuth Authentication

**Status**: [ ] Not Started / [ ] In Progress / [ ] Complete
**Start Date**: \***\*\_\_\_\*\***
**End Date**: \***\*\_\_\_\*\***

### Backend

- [ ] Add `googleId` and `avatarUrl` to User schema
- [ ] Run `npx prisma migrate dev`
- [ ] Create `apps/server/src/services/oauth-service.ts`
- [ ] Create `apps/server/src/routes/auth/oauth.ts` - Google OAuth routes
- [ ] Register OAuth routes in server
- [ ] Add `google-auth-library` dependency

### Frontend

- [ ] Create `apps/ui/src/components/auth/oauth-buttons.tsx`
- [ ] Create `apps/ui/src/routes/auth.callback.tsx`
- [ ] Update login view to include OAuth buttons
- [ ] Add user avatar display in header

### Configuration

- [ ] Add Google OAuth env vars to `.env.example`
- [ ] Document Google Cloud Console setup

### Testing

- [ ] "Sign in with Google" button appears
- [ ] OAuth flow completes successfully
- [ ] New users created from Google profile
- [ ] Existing users can link Google account
- [ ] User avatar displayed in app

---

## Phase 5: Production Deployment

**Status**: [ ] Not Started / [ ] In Progress / [ ] Complete
**Start Date**: \***\*\_\_\_\*\***
**End Date**: \***\*\_\_\_\*\***

### Infrastructure

- [ ] Create Hetzner CPX41 server
- [ ] Configure DNS records
- [ ] Install Docker and Docker Compose
- [ ] Clone repository to `/opt/automaker`

### Configuration

- [ ] Create `docker-compose.production.yml`
- [ ] Create `.env` with production values
- [ ] Generate `AUTOMAKER_ENCRYPTION_KEY`
- [ ] Configure Google OAuth callback URL
- [ ] Set up Traefik dashboard password

### Deployment

- [ ] Build Docker images
- [ ] Start containers
- [ ] Verify SSL certificate
- [ ] Run database migrations
- [ ] Create first admin user

### Operations

- [ ] Set up backup script and cron job
- [ ] Test restore procedure
- [ ] Configure monitoring script
- [ ] Set up alerting (email/Slack)
- [ ] Configure firewall (UFW)

### Testing

- [ ] System accessible via HTTPS
- [ ] All 3 team members can login
- [ ] Knowledge sync works between users
- [ ] Agents run with user's API keys
- [ ] Backups running daily

---

## Milestone Summary

| Milestone         | Target Date | Actual Date | Notes |
| ----------------- | ----------- | ----------- | ----- |
| Phase 1 Complete  |             |             |       |
| Phase 2 Complete  |             |             |       |
| Phase 3 Complete  |             |             |       |
| Phase 4 Complete  |             |             |       |
| Phase 5 Complete  |             |             |       |
| Production Launch |             |             |       |

---

## Issues Encountered

| Date | Phase | Issue | Resolution |
| ---- | ----- | ----- | ---------- |
|      |       |       |            |

---

## Lessons Learned

_Document insights gained during implementation for future reference._

---

## Change Log

| Date | Change                    | Author |
| ---- | ------------------------- | ------ |
|      | Initial checklist created |        |
