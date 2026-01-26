# MCP Knowledge Server - Cleanup Guide

This guide explains how to clean and maintain your MCP Knowledge Server installation, including database cleanup and repository maintenance.

## Table of Contents

- [Overview](#overview)
- [Database Cleanup](#database-cleanup)
- [Repository Cleanup](#repository-cleanup)
- [Automated Cleanup](#automated-cleanup)
- [Safety Features](#safety-features)
- [Troubleshooting](#troubleshooting)

## Overview

The MCP Knowledge Server provides two cleanup utilities:

1. **Database Cleanup** (`scripts/cleanup_databases.py`) - Clear data from Neo4j, ChromaDB, and SQLite
2. **Repository Cleanup** (`scripts/cleanup_repository.py`) - Remove temporary files and caches

Both utilities include safety features like dry-run mode, automatic backups, and confirmation prompts.

## Database Cleanup

### Quick Start

```bash
# Show current database statistics
python scripts/cleanup_databases.py --stats

# Preview what would be deleted (dry run)
python scripts/cleanup_databases.py --full --dry-run

# Full database cleanup with backup
python scripts/cleanup_databases.py --full
```

### Database Cleanup Options

#### Full Cleanup

Clears all data from all databases:

```bash
python scripts/cleanup_databases.py --full
```

This will:

1. Create a backup of all databases
2. Clear Neo4j (all nodes and relationships)
3. Clear ChromaDB (all vector embeddings)
4. Clear SQLite event store (all events)
5. Reinitialize all database schemas

#### Selective Cleanup

Clean specific databases:

```bash
# Clear only Neo4j
python scripts/cleanup_databases.py --neo4j

# Clear only ChromaDB
python scripts/cleanup_databases.py --chromadb

# Clear only SQLite event store
python scripts/cleanup_databases.py --sqlite
```

#### Safety Options

**Dry Run** - Preview changes without making them:

```bash
python scripts/cleanup_databases.py --full --dry-run
```

**Skip Backup** - Dangerous! Only use if you have a recent backup:

```bash
python scripts/cleanup_databases.py --full --no-backup
```

**Skip Confirmation** - Auto-confirm prompts:

```bash
python scripts/cleanup_databases.py --full --yes
```

### What Gets Cleaned

| Database     | What's Deleted                       | What's Preserved              |
| ------------ | ------------------------------------ | ----------------------------- |
| **Neo4j**    | All nodes and relationships          | Schema (constraints, indexes) |
| **ChromaDB** | All vector embeddings                | Collection structure          |
| **SQLite**   | All events, outbox, snapshots, cache | Table schemas                 |

### Database Statistics

Check current database contents before cleanup:

```bash
python scripts/cleanup_databases.py --stats
```

Output example:

```
Neo4j: 1,234 nodes
ChromaDB: 1,234 documents
SQLite: 5,678 events
```

### Prerequisites

Before running database cleanup:

1. **Stop the MCP server**

   ```bash
   # Check if running
   ps aux | grep mcp_server.py

   # Kill if needed
   pkill -f mcp_server.py
   ```

2. **Ensure Neo4j is running** (for Neo4j cleanup)

   ```bash
   docker ps | grep neo4j
   ```

3. **Have a backup** (automatic unless you use `--no-backup`)

### Cleanup Process

The script follows this sequence:

1. **Verification**
   - Check if MCP server is stopped
   - Display current database statistics
   - Show cleanup plan

2. **Confirmation**
   - Prompt for user confirmation (unless `--yes` flag used)
   - Explain what will be deleted

3. **Backup**
   - Create full backup using `backup/backup_all.sh`
   - Store in `backups/unified/TIMESTAMP/`

4. **Database Cleanup**
   - Clear Neo4j: `MATCH (n) DETACH DELETE n`
   - Clear ChromaDB: Delete all files in `data/chroma/`
   - Clear SQLite: Delete `data/events.db` file

5. **Reinitialization**
   - Run `scripts/init_database.py`
   - Run `scripts/init_neo4j.py`
   - Run `scripts/init_chromadb.py`
   - Remove test data from ChromaDB

6. **Verification**
   - Display final database statistics
   - Confirm all databases are empty

## Repository Cleanup

### Quick Start

```bash
# Preview what would be deleted
python scripts/cleanup_repository.py --dry-run

# Clean all temporary files
python scripts/cleanup_repository.py
```

### Repository Cleanup Options

#### Full Cleanup

Remove all temporary files:

```bash
python scripts/cleanup_repository.py
```

#### Selective Cleanup

Clean specific file types:

```bash
# Python cache files only
python scripts/cleanup_repository.py --python-cache

# Test artifacts only
python scripts/cleanup_repository.py --test-artifacts

# System files only (.DS_Store, Thumbs.db)
python scripts/cleanup_repository.py --system-files

# Temporary documentation only
python scripts/cleanup_repository.py --temp-docs

# Log files only
python scripts/cleanup_repository.py --log-files
```

#### Safety Options

**Dry Run**:

```bash
python scripts/cleanup_repository.py --dry-run
```

**Skip Confirmation**:

```bash
python scripts/cleanup_repository.py --yes
```

### What Gets Cleaned

| Category           | Files Removed                                             | Reason                        |
| ------------------ | --------------------------------------------------------- | ----------------------------- |
| **Python Cache**   | `__pycache__/`, `.pytest_cache/`, `.tox/`, `.hypothesis/` | Generated at runtime          |
| **Test Artifacts** | `.coverage`, `htmlcov/`, `tests/**/*.json`                | Regeneratable test results    |
| **System Files**   | `.DS_Store`, `Thumbs.db`                                  | OS-specific metadata          |
| **Temp Docs**      | `*_REPORT.md`, `*_SUMMARY.md`, `TASK_*.md`                | Development session artifacts |
| **Log Files**      | `*.log` (root only)                                       | Old log files                 |

### What's Preserved

The cleanup script **never** removes:

- Source code files (`*.py`, `*.sh`)
- Configuration files (`.env`, `config.py`)
- Essential documentation (`docs/`)
- Database files (`data/`)
- Backup files (`backups/`)
- Test code (`tests/*.py`)
- Production scripts (`scripts/`, `backup/`, `monitoring/`)

## Automated Cleanup

### Scheduled Cleanup

Add to crontab for regular cleanup:

```bash
# Clean repository weekly (Sundays at 3 AM)
0 3 * * 0 cd /path/to/mcp-knowledge-server && python scripts/cleanup_repository.py --yes

# Clean test artifacts daily (2 AM)
0 2 * * * cd /path/to/mcp-knowledge-server && python scripts/cleanup_repository.py --test-artifacts --yes
```

### Pre-commit Hook

Add to `.git/hooks/pre-commit`:

```bash
#!/bin/bash
# Clean temporary files before commit
python scripts/cleanup_repository.py --python-cache --system-files --yes
```

## Safety Features

### Automatic Backups

Database cleanup automatically creates backups before any changes:

```bash
# Backups stored in:
backups/unified/YYYYMMDD_HHMMSS/
├── manifest.json          # Backup metadata
├── neo4j -> ../../neo4j/TIMESTAMP/
├── chromadb -> ../../chromadb/TIMESTAMP/
└── sqlite -> ../../sqlite/TIMESTAMP/
```

See [BACKUP_AND_RESTORE.md](BACKUP_AND_RESTORE.md) for restore procedures.

### Server Running Check

Database cleanup refuses to run if the MCP server is active:

```
❌ MCP server is currently running!
❌ Please stop the server before running cleanup.
```

### Dry Run Mode

Both utilities support `--dry-run` to preview changes:

```bash
python scripts/cleanup_databases.py --full --dry-run
python scripts/cleanup_repository.py --dry-run
```

Output shows:

- What would be deleted
- How much space would be freed
- Statistics before/after (for databases)

### Confirmation Prompts

Interactive confirmation before destructive operations:

```
⚠️  This will permanently delete data. Continue? (yes/no):
```

Skip with `--yes` flag for automation.

## Troubleshooting

### Issue: "MCP server is currently running"

**Solution**: Stop the server first

```bash
# Find process
ps aux | grep mcp_server.py

# Kill process
pkill -f mcp_server.py

# Or if running via systemd
sudo systemctl stop mcp-knowledge-server
```

### Issue: "Neo4j connection failed"

**Solution**: Ensure Neo4j is running

```bash
# Check Neo4j status
docker ps | grep neo4j

# Start Neo4j if needed
docker start neo4j

# Or for native installation
sudo systemctl start neo4j
```

### Issue: "Permission denied" when cleaning files

**Solution**: Check file permissions

```bash
# For repository cleanup
sudo python scripts/cleanup_repository.py

# Better: Fix permissions
sudo chown -R $USER:$USER .
```

### Issue: Database cleanup fails during reinitialization

**Solution**: Manually reinitialize

```bash
# SQLite
python scripts/init_database.py

# Neo4j
python scripts/init_neo4j.py

# ChromaDB
python scripts/init_chromadb.py

# Remove test data
python -c "
import chromadb
client = chromadb.PersistentClient('./data/chroma')
collection = client.get_collection('concepts')
collection.delete(ids=['test_concept_001'])
"
```

### Issue: Backup fails before cleanup

**Solution**: Check backup system

```bash
# Test backup manually
./backup/backup_all.sh

# Check logs
cat backup/*/backup_*.log

# Ensure adequate disk space
df -h
```

## Best Practices

### Regular Maintenance Schedule

1. **Daily**: Clean test artifacts

   ```bash
   python scripts/cleanup_repository.py --test-artifacts --yes
   ```

2. **Weekly**: Clean repository completely

   ```bash
   python scripts/cleanup_repository.py --yes
   ```

3. **Monthly**: Review database size

   ```bash
   python scripts/cleanup_databases.py --stats
   ```

4. **As Needed**: Clean databases between projects
   ```bash
   python scripts/cleanup_databases.py --full
   ```

### Before Production Deployment

Clean everything for a fresh start:

```bash
# 1. Backup current state
./backup/backup_all.sh

# 2. Clean repository
python scripts/cleanup_repository.py --yes

# 3. Clean databases
python scripts/cleanup_databases.py --full --yes

# 4. Verify clean state
python scripts/cleanup_databases.py --stats
git status --ignored

# 5. Start fresh
./scripts/production_start.sh
```

### After Development/Testing

Remove test data while preserving schemas:

```bash
# Clean test files from repository
python scripts/cleanup_repository.py --test-artifacts --yes

# Clean databases if needed
python scripts/cleanup_databases.py --full --yes
```

## Related Documentation

- [Backup and Restore Guide](BACKUP_AND_RESTORE.md)
- [Production Deployment](PRODUCTION_DEPLOYMENT.md)
- [Monitoring Guide](MONITORING_GUIDE.md)
- [Error Handling Guide](ERROR_HANDLING_GUIDE.md)

## Support

For issues or questions:

- Check [Troubleshooting](#troubleshooting) section above
- Review logs in `backups/*/backup_*.log`
- Consult [Error Handling Guide](ERROR_HANDLING_GUIDE.md)
- File an issue on GitHub
