# Provider-Specific Auth Modes + Strict API-Key Gating (Anthropic + OpenAI/Codex)

## Why this plan exists

We want **provider-specific** “usage method” selection so users can:

- Use **Auth Token / CLI OAuth** for some providers (subscription-style flows).
- Use **API Key** for other providers (pay-per-use).
- **Store API keys even when inactive**, while making it **100% impossible** for inactive keys to be used.
- See (and switch) the current method per provider in **Settings → API Keys**.
- Ensure mode selection **survives server restarts**.
- Store keys in the server’s **`.env`** without conflicts from shell config (e.g. `.zshrc`).

This doc is written to be executable in a fresh session with minimal re-discovery.

---

## Investigation summary (current code)

### 1) “Anthropic auth mode” is currently used as a global “API keys disabled” gate

The existing auth-mode system is Anthropic-specific (`apps/server/src/lib/auth-config.ts`) but its convenience helpers (`isApiKeyAuthDisabled*`) are used to gate OpenAI/Codex behavior too:

- `apps/server/src/providers/codex-provider.ts`: `resolveOpenAiApiKey()` returns `null` when `isApiKeyAuthDisabledSync()` is true.
- `apps/server/src/routes/setup/routes/store-api-key.ts`: blocks _all_ providers before reading `req.body.provider`.
- `apps/server/src/routes/setup/routes/api-keys.ts`: reports no OpenAI key when “OAuth-only” is enabled (based on Anthropic).
- `apps/server/src/lib/codex-auth.ts`: ignores env `OPENAI_API_KEY` based on Anthropic auth mode.
- UI setup flow: Codex API-key UI is hidden based on Anthropic mode (`apps/ui/src/hooks/use-auth-config.ts`).

Result: enabling Anthropic `auth_token` unintentionally disables OpenAI API keys and changes Codex execution routing.

### 2) Auth mode persistence mismatch on restart

`initializeAuthMode()` (called at startup in `apps/server/src/index.ts`) only reads env vars and caches sync mode, but `POST /api/setup/auth-mode` persists to settings.json. After restart, providers that use the cached sync value can disagree with what the API reports from settings.

### 3) OpenAI/Codex “Auth Token” is not an env var, it’s Codex CLI OAuth

There is no `OPENAI_AUTH_TOKEN` env var in this repo. Instead, Codex CLI auth is detected via:

- `libs/platform/src/system-paths.ts:getCodexAuthIndicators()`
  - Reads `~/.codex/auth.json`
  - Looks for OAuth fields: `access_token` or `oauth_token`
  - Looks for API-key fields: `api_key` or `OPENAI_API_KEY`

So for OpenAI/Codex the “auth token method” is: **Codex CLI OAuth login** (`codex login`) backed by `~/.codex/auth.json`.

---

## Core requirements (non-negotiable)

### R1) Provider-specific mode selection

At minimum:

- Anthropic: `auth_token | api_key`
- OpenAI/Codex: `auth_token | api_key`

### R2) Store keys even when inactive

Users may save an API key while in `auth_token` mode, but it must be **inert** until mode switches to `api_key`.

### R3) 100% guarantee: inactive keys are never used

In `auth_token` mode for a provider, the provider must never use:

- The env var API key (even if inherited from `.zshrc`)
- Any stored key in settings/credentials
- Any key stored in `.env`
- Any CLI auth file API-key path (if applicable)

### R4) Visibility + easy switching

Users must see, for each provider:

- Current mode (`auth_token` or `api_key`)
- Whether the required credential is present (OAuth/CLI vs API key)
- Whether an API key is stored but inactive

### R5) Mode survives restart

Restart must not flip provider behavior back to defaults.

### R6) Keys stored in `.env` without `.zshrc` conflicts

We must define precedence so the app doesn’t “accidentally” use a shell-exported key.

---

## Recommended design

### A) Introduce provider auth modes in settings + env

Add **separate settings fields**:

- `globalSettings.anthropicAuthMode` (already exists)
- `globalSettings.openaiAuthMode` (new)

Add **separate env vars** (restart-safe + sync-friendly):

- `AUTOMAKER_ANTHROPIC_AUTH_MODE=auth_token|api_key` (already exists)
- `AUTOMAKER_OPENAI_AUTH_MODE=auth_token|api_key` (new)

Recommendation: keep env vars as the _highest-priority override_ (matches existing Anthropic behavior).

### B) Enforce “inactive means impossible to use” via multiple layers

For each provider, implement defense-in-depth:

1. **Startup env hardening**
   - If provider mode is `auth_token`, delete/blank the provider API key in `process.env`:
     - Anthropic: `ANTHROPIC_API_KEY=''` (already done)
     - OpenAI: `OPENAI_API_KEY=''` (new)
2. **Request-time resolution**
   - Provider key resolution must check provider mode first and immediately treat key as `null` when in `auth_token`.
3. **Subprocess env filtering**
   - When spawning CLIs, explicitly omit the API key env var when in `auth_token`.
4. **CLI auth-file safety (OpenAI/Codex only)**
   - In OpenAI `auth_token` mode, refuse to run if `getCodexAuthIndicators()` shows an API key is present in `~/.codex/auth.json`.
   - Decision: hard-block in this case. Rationale: if the CLI can choose an API-key path internally, the only 100% safe behavior is to **block execution** until the API-key entry is removed.

This is stricter than “prefer OAuth when both exist” but matches the “100% sure” requirement.

### C) Store keys in `.env`, but don’t trust inherited env

We already write `.env` from setup routes:

- `apps/server/src/routes/setup/common.ts:persistApiKeyToEnv()` → `process.cwd()/.env`

To avoid `.zshrc` conflicts, define precedence:

1. If `.env` contains `OPENAI_API_KEY`, treat that as the **app-managed key** (preferred).
2. Only if `.env` lacks it, optionally fall back to inherited `process.env.OPENAI_API_KEY` (must be visible in status/logs; no silent fallback).

Same for `ANTHROPIC_API_KEY`.

Implementation approach:

- Add a small “env file key resolver” that reads `.env` via `secureFs.readEnvFile()` and caches results.
- Providers should prefer the `.env` value over inherited env.

### D) Codex execution strategy (avoid losing tool support)

Recommendation (mode-aware):

- OpenAI `auth_token`:
  - Always use Codex CLI **OAuth** (require `hasOAuthToken`)
  - Never use SDK
  - Never allow CLI API-key auth-file usage (block if API key detected in auth file)
- OpenAI `api_key`:
  - If tools/MCP requested → use CLI (so tools work), passing `OPENAI_API_KEY` from `.env` into the subprocess env.
  - If no tools requested → use SDK (fast path), using `OPENAI_API_KEY` from `.env`.

This replaces the current “always SDK when any API key exists” behavior, which silently drops tool behavior.

---

## Server implementation plan (step-by-step)

### Step 1 — Types + defaults

- Add `openaiAuthMode?: 'auth_token' | 'api_key'` to `libs/types/src/settings.ts` (GlobalSettings).
- Update `DEFAULT_GLOBAL_SETTINGS` to include a default value for `openaiAuthMode`.
  - Decision: default to `auth_token` (strict; API keys only used after explicit opt-in).

### Step 2 — New provider auth config module (source of truth)

Create `apps/server/src/lib/provider-auth-config.ts` (or similar) that:

- Reads provider mode from:
  1. env var override (e.g. `AUTOMAKER_OPENAI_AUTH_MODE`)
  2. settings.json (SettingsService)
  3. defaults
- Exposes:
  - `initializeProviderAuthModes()` (startup, sync env hardening)
  - `getProviderAuthModeSync(provider)`
  - `getProviderAuthMode(provider)` (async, includes settings fallback)
  - `isApiKeyAllowedSync(provider)` / `isApiKeyAllowed(provider)`
  - `applyProviderEnvHardening(mode)` (ensures API keys are blanked in auth_token mode)

Keep `apps/server/src/lib/auth-config.ts` for Anthropic compatibility, but re-implement its internals on top of the new generic module.

### Step 3 — Persist provider auth mode to `.env` + settings

Update or add setup endpoints:

- Keep existing `GET/POST /api/setup/auth-mode` for Anthropic (backwards compat).
- Add `GET/POST /api/setup/openai-auth-mode` or a generalized route like:
  - `GET /api/setup/provider-auth-mode?provider=openai|anthropic`
  - `POST /api/setup/provider-auth-mode` with `{ provider, mode }`

When mode changes:

- Write to settings.json (`SettingsService.updateGlobalSettings`)
- Write to `.env` (new helper using `secureFs.writeEnvKey`)
  - e.g. `AUTOMAKER_OPENAI_AUTH_MODE=auth_token|api_key`

### Step 4 — Fix key storage route behavior (store but inactive)

Update `apps/server/src/routes/setup/routes/store-api-key.ts`:

- Parse `provider` first.
- Always persist to `.env`.
- Only set `process.env[ENV_KEY] = apiKey` **if** that provider’s mode is `api_key`.
- If mode is `auth_token`, set `process.env[ENV_KEY] = ''` (or delete + set empty string) and return:
  - `{ success: true, stored: true, active: false, reason: 'mode_auth_token' }`

Also update `apps/server/src/routes/setup/routes/api-keys.ts` to return per-provider status:

- `mode` per provider
- `hasKeyStored` (in `.env`)
- `isKeyActive` (mode is api_key and key exists)

### Step 5 — Update Codex provider to use OpenAI auth mode (not Anthropic)

Update `apps/server/src/providers/codex-provider.ts`:

- Replace `isApiKeyAuthDisabledSync()` usage with `isApiKeyAllowedSync('openai')` (or equivalent).
- In OpenAI `auth_token` mode:
  - `resolveOpenAiApiKey()` must always return `null`
  - `resolveCodexExecutionPlan()` must:
    - require CLI
    - require `authIndicators.hasOAuthToken`
    - if `authIndicators.hasApiKey` is true, hard-fail with a message like:
      - “OpenAI is set to Auth Token mode. Your Codex CLI auth file contains an API key; remove it or switch to API Key mode.”
- In OpenAI `api_key` mode:
  - Resolve key from `.env` (preferred) then fall back as decided.
  - Choose CLI vs SDK based on tool eligibility (see recommended strategy above).

Also update `apps/server/src/lib/codex-auth.ts` to use OpenAI auth mode for classification and to avoid calling Anthropic-only helpers.

### Step 6 — Fix sync/async mismatch on startup (restart-safe)

Startup must call a single initializer that:

- Reads env vars (already loaded by `dotenv/config` in `apps/server/src/index.ts`)
- Applies env hardening (blank provider API keys where mode is `auth_token`)
- Caches provider modes for sync getters

Because we persist modes into `.env`, startup remains synchronous (no async file I/O required).

---

## UI implementation plan

### Step 1 — Provider-specific auth toggles in Settings → API Keys

Update `apps/ui/src/components/views/settings-view/api-keys/`:

- Keep the existing Anthropic toggle but label it clearly as “Anthropic / Claude”.
- Add a new toggle for “OpenAI / Codex” (separate endpoint + state).
- For each provider:
  - Show mode badge (`Subscription (CLI OAuth)` vs `API key (pay-per-use)`)
  - Show credential status:
    - For OpenAI auth_token: Codex CLI OAuth detected? (`getCodexAuthIndicators.hasOAuthToken`)
    - For OpenAI api_key: key present in `.env` / stored
  - Show “API key stored but inactive” if mode is auth_token and key exists.

### Step 2 — Fix setup wizard Codex step gating

In `apps/ui/src/components/views/setup-view/steps/providers-setup-step.tsx`, the Codex API key accordion is currently hidden based on Anthropic mode. Change it to use **OpenAI mode**.

---

## Testing plan (TDD; don’t “fix tests to match broken code”)

### New/updated unit tests (server)

Add tests before code changes; verify they fail; then implement.

Suggested tests:

1. `CodexProvider` respects OpenAI auth mode:
   - If `openaiAuthMode=auth_token` and `OPENAI_API_KEY` is set → must NOT run SDK; must require CLI OAuth.
   - If `openaiAuthMode=api_key` and key exists → uses SDK for no-tools requests; uses CLI for tool requests.

2. `store-api-key` stores even when inactive:
   - In `openaiAuthMode=auth_token`, storing OpenAI key returns success but does not activate env key at runtime.

3. Startup persistence:
   - With `.env` containing `AUTOMAKER_OPENAI_AUTH_MODE=api_key`, sync getter returns `api_key` after init.

### UI tests (optional if suite exists)

- Ensure the OpenAI toggle and “stored but inactive” badge render correctly.

---

## Decisions confirmed

1. Default `openaiAuthMode` is `auth_token` (strict by default; API keys only after deliberate user selection).
2. In OpenAI `auth_token` mode, hard-block execution if `~/.codex/auth.json` contains an API key (only way to guarantee no API-key auth path).

## Remaining open question (optional)

1. **Fallback to inherited env keys (api_key mode only)**
   - If `.env` has no key but `process.env.OPENAI_API_KEY` exists, should we use it in `api_key` mode?
   - Recommendation: yes for Docker/CI, but it must be explicit in status/logs and `.env` must win if present.

---

## Execution recommendation (for next session)

1. Confirm the “Remaining open question” above (optional; we can default to `.env`-preferred with visible fallback).
2. Implement with TDD in this order: types → provider-auth-config → routes → providers → UI.
3. Run unit tests after each step to prevent regressions.

---

## Note on Cipher memory

Cipher retrieval failed in this environment (“API key for anthropic not found”), so this plan does not incorporate any stored architectural memories.
