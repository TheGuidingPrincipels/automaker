# OAuth Authentication Investigation - 2026-01-27

## Problem Statement

The AI Library's Knowledge Library feature shows "AI Analysis Unavailable" with error:

```
Command failed with exit code 1 (exit code: 1) Error output: Check stderr output for details
```

Meanwhile, the main Automaker application works perfectly with OAuth authentication (shows "OAuth authentication active" in settings).

## Environment

- User has Claude Max subscription ($200/month)
- Automaker agents work perfectly with OAuth
- `CLAUDE_CODE_OAUTH_TOKEN` is set in `~/.zshrc`
- `ANTHROPIC_API_KEY` is also set in `~/.zshrc`
- Claude CLI version: 2.1.19

## Key Files Involved

- `/Users/ruben/.zshrc` - Contains both `ANTHROPIC_API_KEY` and `CLAUDE_CODE_OAUTH_TOKEN`
- `2.ai-library/src/sdk/auth.py` - OAuth token loading logic
- `2.ai-library/src/sdk/client.py` - Claude Code SDK client
- `2.ai-library/start-with-automaker.sh` - Startup script (unsets ANTHROPIC_API_KEY)
- `2.ai-library/start-api.sh` - Alternative startup script
- `apps/server/src/providers/claude-provider.ts` - How Automaker handles auth (for reference)

## Root Cause Analysis

### Finding 1: Token Naming Confusion

There are THREE different auth-related environment variables:

1. `ANTHROPIC_API_KEY` - Standard API key (pay-per-use)
2. `ANTHROPIC_AUTH_TOKEN` - Used by SDK for explicit OAuth token
3. `CLAUDE_CODE_OAUTH_TOKEN` - Alternative name for OAuth token

### Finding 2: How Automaker Works (Correctly)

In `apps/server/src/providers/claude-provider.ts` lines 199-204:

```typescript
} else if (process.env.CLAUDE_CODE_OAUTH_TOKEN) {
  // DO NOT map to ANTHROPIC_AUTH_TOKEN - that's for direct API auth
  // The CLI will use its own OAuth flow
  logger.debug('[buildEnv] Using CLAUDE_CODE_OAUTH_TOKEN (CLI will handle OAuth)');
}
```

Automaker does NOT set `ANTHROPIC_AUTH_TOKEN` when `CLAUDE_CODE_OAUTH_TOKEN` is present. It lets the CLI handle OAuth internally.

### Finding 3: How AI Library Was Broken

In `2.ai-library/src/sdk/auth.py` (original code):

```python
token = os.getenv("CLAUDE_CODE_OAUTH_TOKEN")
if token:
    # Also set ANTHROPIC_AUTH_TOKEN so SDK can find it
    os.environ["ANTHROPIC_AUTH_TOKEN"] = token  # <-- THIS CAUSED THE PROBLEM
    return token
```

Setting `ANTHROPIC_AUTH_TOKEN` explicitly OVERRIDES the CLI's internal OAuth mechanism.

### Finding 4: The "Credit Balance Too Low" Error

When we explicitly set `ANTHROPIC_AUTH_TOKEN` to the OAuth token value, the CLI exits with:

```
Credit balance is too low
```

This happens even with a fresh token obtained from `claude login`.

### Finding 5: CLI Works Without Explicit Token

When running the CLI directly with:

- `CLAUDE_CODE_OAUTH_TOKEN` set
- `ANTHROPIC_AUTH_TOKEN` NOT set
- `ANTHROPIC_API_KEY` NOT set

The CLI works perfectly and responds.

---

## Approaches Tried

### Approach 1: Refresh OAuth Token ❌ Did Not Fix

1. User ran `claude login` to get a fresh token
2. Updated `~/.zshrc` with new token:
   ```bash
   export CLAUDE_CODE_OAUTH_TOKEN="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"
   ```
3. Result: Still got "Credit balance is too low" when token was used via `ANTHROPIC_AUTH_TOKEN`

### Approach 2: Match Automaker's Behavior ❌ Did Not Fix (Not Fully Tested)

Modified `auth.py` to NOT set `ANTHROPIC_AUTH_TOKEN`:

```python
token = os.getenv("CLAUDE_CODE_OAUTH_TOKEN")
if token:
    logger.debug(
        "CLAUDE_CODE_OAUTH_TOKEN is set - CLI will use internal OAuth. "
        "Not setting ANTHROPIC_AUTH_TOKEN to avoid overriding CLI auth."
    )
    # Return a marker that auth is available, but don't modify env
    return "__CLI_HANDLES_OAUTH__"
```

Modified `client.py` to accept this marker:

```python
has_auth = (
    os.getenv("ANTHROPIC_AUTH_TOKEN")
    or os.getenv("CLAUDE_CODE_OAUTH_TOKEN")
    or self._auth_token == "__CLI_HANDLES_OAUTH__"
)
```

### Approach 3: Test in Clean Environment ✅ WORKED

Running in a completely clean bash environment:

```bash
/bin/bash --noprofile --norc -c '
export CLAUDE_CODE_OAUTH_TOKEN="sk-ant-oat01-..."
export PATH="/Users/ruben/.npm-global/bin:/usr/local/bin:/usr/bin:/bin"
unset ANTHROPIC_AUTH_TOKEN
unset ANTHROPIC_API_KEY
...
'
```

Result: **SDK query returned Success: True** and got response "WORKING"

---

## Current State of Code Changes

### File: `~/.zshrc`

- Updated `CLAUDE_CODE_OAUTH_TOKEN` to new token (line 19)
- Added comment about refresh date

### File: `2.ai-library/src/sdk/auth.py`

- Modified `load_oauth_token()` to return `"__CLI_HANDLES_OAUTH__"` marker when `CLAUDE_CODE_OAUTH_TOKEN` is set
- Does NOT set `ANTHROPIC_AUTH_TOKEN` in this case

### File: `2.ai-library/src/sdk/client.py`

- Modified auth check to accept `CLAUDE_CODE_OAUTH_TOKEN` or the marker

### File: `2.ai-library/start-with-automaker.sh`

- Updated logging to show which OAuth source is being used
- Still unsets `ANTHROPIC_API_KEY`

---

## What Still Doesn't Work

Even after these changes, when running the AI Library normally (not in a clean bash environment), it still fails. The suspected issue is that the Python process inherits environment variables from the current shell session, which has both:

- `ANTHROPIC_API_KEY` (from zshrc)
- `CLAUDE_CODE_OAUTH_TOKEN` (from zshrc)

The startup script runs `unset ANTHROPIC_API_KEY`, but this might not be propagating correctly to the Python subprocess, OR there's another issue with how the SDK subprocess inherits environment.

---

## Key Discoveries

### 1. SDK Transport Mechanism

The Claude Code SDK (Python) uses `SubprocessCLITransport` which:

- Runs the `claude` CLI as a subprocess
- Passes all environment variables via `os.environ`
- Uses `--output-format stream-json` flag

Location: `.venv/lib/python3.13/site-packages/claude_code_sdk/_internal/transport/subprocess_cli.py`

### 2. Environment Variable Inheritance

In `subprocess_cli.py` lines 183-187:

```python
process_env = {
    **os.environ,
    **self._options.env,  # User-provided env vars
    "CLAUDE_CODE_ENTRYPOINT": "sdk-py",
}
```

The SDK passes ALL of `os.environ` to the subprocess.

### 3. Credentials File Locations Checked

The `auth.py` checks these locations for credentials:

1. `DATA_DIR/credentials.json`
2. `AUTOMAKER_DATA_DIR/credentials.json`
3. `./data/credentials.json`
4. `~/.automaker/credentials.json`

None of these files exist.

### 4. Claude CLI Credentials Location

The Claude CLI stores its internal credentials in:

- `~/.config/claude-code/auth.json` (doesn't exist on this system)
- Or internally in the Claude desktop app at `~/Library/Application Support/Claude/config.json` (has `oauth:tokenCache` but it's encrypted)

---

## Next Steps to Try

1. **Verify startup script actually unsets env vars** - Add debug logging to confirm `ANTHROPIC_API_KEY` is unset before Python starts

2. **Check if Python SDK needs special env handling** - Maybe need to explicitly filter out `ANTHROPIC_API_KEY` in the SDK client before calling the CLI

3. **Test the actual startup flow** - Run `./start-with-automaker.sh` and check the logs

4. **Create credentials.json** - Write the OAuth token to `data/credentials.json` in the format the auth.py expects

5. **Check SDK version compatibility** - The Python `claude_code_sdk` might have specific requirements

---

## Environment Variable Reference

### What Should Be Set

- `CLAUDE_CODE_OAUTH_TOKEN` - The OAuth token from `claude login`

### What Should NOT Be Set (for OAuth to work)

- `ANTHROPIC_AUTH_TOKEN` - Setting this overrides CLI's internal OAuth
- `ANTHROPIC_API_KEY` - Setting this causes CLI to use API key instead of OAuth

### Startup Script Behavior

- `start-with-automaker.sh` runs `unset ANTHROPIC_API_KEY` at line 154
- `start-api.sh` runs `unset ANTHROPIC_API_KEY` at line 29

---

## Test Commands That Worked

### Direct CLI (works):

```bash
source ~/.zshrc && unset ANTHROPIC_AUTH_TOKEN && unset ANTHROPIC_API_KEY && claude --print "Hello"
```

### Clean Bash + SDK (works):

```bash
/bin/bash --noprofile --norc -c '
export CLAUDE_CODE_OAUTH_TOKEN="sk-ant-oat01-..."
export PATH="/Users/ruben/.npm-global/bin:/usr/local/bin:/usr/bin:/bin"
unset ANTHROPIC_AUTH_TOKEN
unset ANTHROPIC_API_KEY
cd /Users/ruben/Documents/GitHub/automaker/2.ai-library
source .venv/bin/activate
python3 -c "... SDK test code ..."
'
```

### What Fails:

Running from a normal zsh session where both `ANTHROPIC_API_KEY` and `CLAUDE_CODE_OAUTH_TOKEN` are exported, even after sourcing the venv and trying to unset vars.

---

## Files Modified (To Revert If Needed)

1. `~/.zshrc` - Line 19 (CLAUDE_CODE_OAUTH_TOKEN value)
2. `2.ai-library/src/sdk/auth.py` - `load_oauth_token()` function
3. `2.ai-library/src/sdk/client.py` - Auth check in `_query()` method
4. `2.ai-library/start-with-automaker.sh` - OAuth detection logging

---

## References

- [Managing API key environment variables in Claude Code](https://support.claude.com/en/articles/12304248-managing-api-key-environment-variables-in-claude-code)
- [GitHub Issue #6536: SDK OAuth token usage](https://github.com/anthropics/claude-code/issues/6536)
- [GitHub Issue #7100: Headless/Remote Authentication](https://github.com/anthropics/claude-code/issues/7100)
- [GitHub Issue #7855: Env vars interfering with local interactive mode](https://github.com/anthropics/claude-code/issues/7855)
