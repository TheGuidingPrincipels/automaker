# Claude SDK OAuth Authentication

How to use OAuth tokens instead of API keys when calling Claude via the SDK.

## Problem

When `ANTHROPIC_API_KEY` exists in the environment (e.g., from `~/.zshrc`), the Claude CLI prioritizes it over OAuth authentication. This triggers pay-per-use billing even when the user has a Claude Max subscription.

**Symptom**: "Credit balance is too low" errors despite valid subscription.

## Solution: Environment Filtering

Override the subprocess environment to explicitly clear `ANTHROPIC_API_KEY` and pass through OAuth tokens.

### Python SDK Implementation

```python
def _build_sdk_env(self) -> Dict[str, str]:
    """Build environment prioritizing OAuth over API key auth."""
    env: Dict[str, str] = {}

    # Pass OAuth token (CLI handles OAuth internally)
    oauth_token = os.getenv("CLAUDE_CODE_OAUTH_TOKEN")
    if oauth_token:
        env["CLAUDE_CODE_OAUTH_TOKEN"] = oauth_token

    # Pass explicit auth token if set
    auth_token = os.getenv("ANTHROPIC_AUTH_TOKEN")
    if auth_token:
        env["ANTHROPIC_AUTH_TOKEN"] = auth_token

    # CRITICAL: Clear API key to prevent it overriding OAuth
    env["ANTHROPIC_API_KEY"] = ""

    # Pass essential system variables
    for var in ["PATH", "HOME", "SHELL", "TERM", "USER", "LANG", "LC_ALL",
                "TMPDIR", "XDG_CONFIG_HOME", "XDG_DATA_HOME"]:
        value = os.environ.get(var)
        if value:
            env[var] = value

    return env

# Usage with ClaudeCodeOptions
options = ClaudeCodeOptions(
    system_prompt=system_prompt,
    max_turns=max_turns,
    model=model,
    env=self._build_sdk_env(),  # Pass filtered environment
)
```

### TypeScript Implementation (Automaker Reference)

```typescript
// From claude-provider.ts
const buildEnv = (): Record<string, string> => {
  const env: Record<string, string> = {};

  // Pass OAuth token
  if (process.env.CLAUDE_CODE_OAUTH_TOKEN) {
    env['CLAUDE_CODE_OAUTH_TOKEN'] = process.env.CLAUDE_CODE_OAUTH_TOKEN;
  }

  // CRITICAL: Clear API key
  env['ANTHROPIC_API_KEY'] = '';

  // Pass system variables
  ['PATH', 'HOME', 'SHELL', 'TERM', 'USER'].forEach((v) => {
    if (process.env[v]) env[v] = process.env[v]!;
  });

  return env;
};
```

## How It Works

1. **SDK Transport Layer**: The Python SDK merges environments at `subprocess_cli.py:182-187`:

   ```python
   process_env = {
       **os.environ,          # Inherited (includes ANTHROPIC_API_KEY)
       **self._options.env,   # User overrides (our filtered env)
       "CLAUDE_CODE_ENTRYPOINT": "sdk-py",
   }
   ```

2. **Override Mechanism**: Setting `ANTHROPIC_API_KEY=""` in `options.env` overrides the inherited value.

3. **CLI Auth Priority**: Claude CLI treats empty string as "not set", falling back to OAuth via `CLAUDE_CODE_OAUTH_TOKEN`.

## Auth Token Sources

| Variable                  | Source           | Notes                             |
| ------------------------- | ---------------- | --------------------------------- |
| `CLAUDE_CODE_OAUTH_TOKEN` | `claude login`   | CLI manages OAuth flow internally |
| `ANTHROPIC_AUTH_TOKEN`    | Manual/Automaker | Explicit token override           |
| `ANTHROPIC_API_KEY`       | Pay-per-use      | Must be cleared for OAuth         |

## Verification

```python
# Check environment filtering
client = ClaudeCodeClient()
sdk_env = client._build_sdk_env()

assert sdk_env.get("ANTHROPIC_API_KEY") == ""  # Cleared
assert sdk_env.get("CLAUDE_CODE_OAUTH_TOKEN")  # Present if logged in
assert sdk_env.get("PATH")  # System vars passed
```

## Key Points

- Always explicitly set `ANTHROPIC_API_KEY=""` (not `None` or missing)
- Pass `CLAUDE_CODE_OAUTH_TOKEN` if available
- Include essential system variables for subprocess to function
- The `env` parameter in `ClaudeCodeOptions` overrides inherited environment
