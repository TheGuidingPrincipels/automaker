# AI-Library Agent Guide

## Repo Layout

- `src/` → application code
  - `src/extraction/` → markdown parsing + canonicalization + checksums
  - `src/sdk/` → Claude Code SDK wrapper (`ClaudeCodeClient`)
  - `src/session/` → session lifecycle + persistence
  - `src/execution/` → verified writer + markers
  - `src/models/` → Pydantic models (plans, blocks, sessions)
- `tests/` → pytest suite (prefers TDD; add regressions here)
- `data/` → local Cipher MCP server state (ignored; never commit)

## Commands

- Tests: `.venv/bin/pytest -q`
- Lint: `.venv/bin/ruff check .`

## Local/Generated Artifacts

- `data/` is reserved for local Cipher MCP artifacts (e.g. `cipher-sessions.db*`) and is fully ignored via `.gitignore`.
- `.venv/`, `.pytest_cache/`, `__pycache__/` are ignored.

## Key Invariants

- No content loss: plans must account for every block.
- Code blocks are byte-strict (fenced + indented).

## Working Rules (keep these tight)

- No silent fallbacks that mask errors.
- No modifying tests to “make them pass” (fix code instead).
- Use async file operations (AnyIO) for filesystem work.
- Verify external library APIs via Context7 before implementing new integrations.

## Where to Look First

- Parsing/canonicalization: `src/extraction/parser.py`, `src/extraction/canonicalize.py`
- SDK behaviors: `src/sdk/client.py`, `src/sdk/prompts/`
- Workflow orchestration: `src/session/manager.py`
- Verified writes/markers: `src/execution/writer.py`, `src/execution/markers.py`
