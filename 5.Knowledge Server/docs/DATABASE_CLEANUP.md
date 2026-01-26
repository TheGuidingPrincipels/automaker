# Database Cleanup Guide

Quick reference for cleaning up test data and resetting databases to a fresh state.

## Overview

The `scripts/cleanup_databases.py` utility safely cleans all databases in the MCP Knowledge Server:

- **Neo4j** - Graph database (concepts and relationships)
- **ChromaDB** - Vector database (embeddings for semantic search)
- **SQLite** - Event store (audit trail and events)

## When to Use

- After running test suites
- To get a fresh database state
- Before starting production usage
- When test data pollutes the system

## Basic Usage

### Full Cleanup (Recommended)

```bash
# With automatic backup (safest)
.venv/bin/python scripts/cleanup_databases.py --full --yes

# Without backup (faster for test cleanup)
.venv/bin/python scripts/cleanup_databases.py --full --yes --no-backup
```

### Preview Mode

```bash
# See what would be deleted without making changes
.venv/bin/python scripts/cleanup_databases.py --full --dry-run
```

### Check Database Status

```bash
# Show current node/document/event counts
.venv/bin/python scripts/cleanup_databases.py --stats
```

## Selective Cleanup

Clean specific databases only:

```bash
# Neo4j only
.venv/bin/python scripts/cleanup_databases.py --neo4j --yes

# ChromaDB only
.venv/bin/python scripts/cleanup_databases.py --chromadb --yes

# SQLite only
.venv/bin/python scripts/cleanup_databases.py --sqlite --yes
```

## Safety Features

1. **Server Check** - Prevents cleanup while MCP server is running
2. **Automatic Backup** - Creates backup before cleanup (use `--no-backup` to skip)
3. **Confirmation Prompt** - Asks for confirmation (use `--yes` to skip)
4. **Verification** - Shows final counts after cleanup

## Common Workflow

After test runs:

```bash
# 1. Stop the MCP server if running
# 2. Run cleanup
.venv/bin/python scripts/cleanup_databases.py --full --yes --no-backup

# 3. Verify clean state
.venv/bin/python scripts/cleanup_databases.py --stats
```

Expected output after cleanup:

```
Neo4j: 0 nodes
ChromaDB: 0 documents
SQLite: 0 events
```

## Troubleshooting

**Error: "MCP server is currently running"**

- Stop the server first: `ps aux | grep mcp_server.py` then `kill <PID>`

**Error: "Failed to clear Neo4j"**

- Verify Neo4j container is running: `docker ps | grep neo4j`
- Container name must be: `mcp-knowledge-neo4j`

**ChromaDB shows documents after cleanup**

- The init script adds a test document - this is normal
- It will be removed on first real concept creation
