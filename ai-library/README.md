# Knowledge Library System

**The Reliable Librarian** - A personal knowledge management system that extracts, organizes, and retrieves information from markdown documents.

## Overview

The Knowledge Library System enables users to:

1. **Input Mode**: Extract information from raw documents into organized, persistent markdown files
2. **Output Mode** (Phase 6): Query and retrieve information from the library using natural language

## Features

- **Deterministic Extraction**: Parse markdown documents into semantic content blocks
- **AI-Powered Routing**: Use Claude Code SDK to suggest optimal destinations for content
- **100% Verification**: Every write operation is verified with checksum comparison
- **User Control**: All decisions (discard, routing) require explicit user approval
- **Two Content Modes**:
  - **STRICT**: Preserve words/sentences exactly; code blocks are byte-strict
  - **REFINEMENT**: Allow minor formatting fixes with user verification

## Installation

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows

# Install dependencies
pip install -e ".[dev]"

# Run tests
pytest
```

## Project Structure

```
knowledge-library/
├── src/
│   ├── models/          # Pydantic data models
│   ├── extraction/      # Markdown parsing and checksums
│   ├── session/         # Session lifecycle management
│   ├── library/         # Library scanning and categories
│   ├── execution/       # File writing with verification
│   └── sdk/             # Claude Code SDK integration
├── library/             # Knowledge storage (markdown files)
├── sessions/            # Session state persistence
├── configs/             # Configuration files
└── tests/               # Test suite
```

## Core Principles

| Principle                         | Description                                                               |
| --------------------------------- | ------------------------------------------------------------------------- |
| **100% Information Preservation** | No content lost during extraction, routing, or merging                    |
| **Complete Extraction**           | Source document fully emptied into library → can be deleted               |
| **User Verification**             | Cleanup and routing always require explicit user decisions                |
| **All Blocks Resolved**           | Cannot complete session until every block has a destination               |
| **Checksum Verification**         | Every write operation is verified by reading back and comparing checksums |
| **Fail-Fast**                     | If any integrity check fails, stop immediately and report                 |

## Usage

The system is designed to be driven by:

1. **Claude Code SDK** - For AI-powered cleanup and routing suggestions
2. **Web UI + API** (Phase 4/5) - For user decisions (click-to-accept)

### API Surface (SessionManager)

```python
from src.session import SessionManager, SessionStorage
from src.models.cleanup_plan import CleanupDisposition

# Initialize
storage = SessionStorage("./sessions")
manager = SessionManager(storage, "./library")

# Create session and parse source
session = await manager.create_session("source.md")

# Generate and approve cleanup plan
cleanup_plan = await manager.generate_cleanup_plan(session.id)
for item in cleanup_plan.items:
    await manager.set_cleanup_decision(session.id, item.block_id, CleanupDisposition.KEEP)
await manager.approve_cleanup_plan(session.id)

# Generate routing plan and select destinations
routing_plan = await manager.generate_routing_plan(session.id)
for block in routing_plan.blocks:
    await manager.select_destination(session.id, block.block_id, option_index=0)

# Approve and execute
await manager.approve_plan(session.id)
# Execute and verify (Phase 2+)
```

### Async vs Sync APIs (Classification / Centroids)

Some subsystems now offer both sync and async entry points:

- **Sync (safe in non-async code)**: `ClassificationService.classify()`, `CentroidManager.compute_centroids()`
- **Async (safe inside event loops)**: `ClassificationService.classify_async()`, `CentroidManager.compute_centroids_async()`, `LLMTierClassifier.classify_async()`

Why this matters:

- Sync wrappers use `asyncio.run()` internally, which will raise if called from a running event loop.
- If you're inside `async def` code (e.g., FastAPI/ASGI), prefer the async variants.

## Development

```bash
# Run tests
pytest

# Run tests with coverage
pytest --cov=src

# Format code
ruff format .

# Lint
ruff check .
```

## Phases

- **Phase A (Core Engine)**: ✅ Data models, extraction, session management
- **Phase B (Smart Routing)**: Planning flow, cleanup/routing plans
- **Phase 3A (Vector Infrastructure)**: Qdrant, embeddings, semantic search
- **Phase 3B (Intelligence Layer)**: Classification, taxonomy, ranking
- **Phase D (REST API)**: FastAPI endpoints
- **Phase E (Query Mode)**: RAG query engine
- **Phase F (Web UI)**: Web interface

## License

MIT
