# Claude Code Instructions

This is the Knowledge Library System project. Follow these instructions when working on this codebase.

## Project Overview

A personal knowledge management system that:

1. Extracts content from markdown documents into semantic blocks
2. Uses AI to suggest cleanup and routing decisions
3. Writes content to organized library files with checksum verification
4. Ensures 100% information preservation

## Architecture

- **Models** (`src/models/`): Pydantic v2 data models
- **Extraction** (`src/extraction/`): Markdown parsing, canonicalization, checksums
- **Session** (`src/session/`): Session lifecycle and persistence
- **Library** (`src/library/`): Library scanning and categories
- **Execution** (`src/execution/`): File writing with markers and verification
- **SDK** (`src/sdk/`): Claude Code SDK integration

## Key Rules

1. **Never auto-discard content** - All discard decisions require explicit user approval
2. **Code blocks are byte-strict** - Fenced code blocks must match exactly
3. **Prose uses canonical checksums** - Whitespace/line wraps may change, but words must be preserved
4. **Verify all writes** - Read back and compare checksums after every write
5. **Fail fast** - Stop immediately on any integrity error

## Content Modes

- **STRICT**: Default. Preserves words/sentences. No merges/rewrites.
- **REFINEMENT**: Allows minor formatting fixes. Merges need triple-view approval.

## Testing

```bash
pytest                    # Run all tests
pytest tests/test_extraction.py  # Run specific test file
pytest -v                 # Verbose output
```

## Common Tasks

### Adding a New Model

1. Create model in `src/models/`
2. Export from `src/models/__init__.py`
3. Add tests in `tests/`

### Adding Extraction Features

1. Modify `src/extraction/parser.py` for parsing changes
2. Update `src/extraction/checksums.py` for checksum logic
3. Test with `tests/test_extraction.py`

### Modifying Session Flow

1. Update `src/session/manager.py` for workflow changes
2. Update models if needed
3. Test with `tests/test_session.py`

## File Locations

- Config: `configs/settings.yaml`
- Library index: `library/_index.yaml`
- Sessions: `sessions/` (JSON files)
- Tests: `tests/`
- Fixtures: `tests/fixtures/`
