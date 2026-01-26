# Troubleshooting Guide: Short-Term Memory MCP

## Quick Diagnostics

### Health Check

```bash
# Run health check via MCP tool
# Returns database status, cache status, response time
mcp call short-term-memory health_check
```

### System Metrics

```bash
# Get performance metrics
mcp call short-term-memory get_system_metrics

# Returns:
# - Database size
# - Operation counts
# - Timing statistics
# - Cache entries
```

## Common Issues

### Session Already Exists

**Symptom**: `initialize_daily_session` returns warning "Session already exists"

**Cause**: Session with same date already created

**Solution**:

```bash
# Check existing session
mcp call short-term-memory get_active_session --date "2025-01-10"

# If you need to start fresh, delete old session
sqlite3 short_term_mcp.db "DELETE FROM sessions WHERE session_id = '2025-01-10';"
```

### Concepts Not Found

**Symptom**: `get_concepts_by_session` returns empty list

**Cause**:

1. Session doesn't exist
2. Concepts not yet stored
3. Wrong session ID

**Solution**:

```bash
# Verify session exists
sqlite3 short_term_mcp.db "SELECT * FROM sessions WHERE session_id = '2025-01-10';"

# Check if concepts exist
sqlite3 short_term_mcp.db "SELECT * FROM concepts WHERE session_id = '2025-01-10';"

# Store concepts first
mcp call short-term-memory store_concepts_from_research \
  --session_id "2025-01-10" \
  --concepts '[{"name": "python asyncio", "data": {}}]'
```

### Mark Concept Stored Fails

**Symptom**: `mark_concept_stored` returns "CONCEPT_NOT_FOUND"

**Cause**: Invalid concept_id or concept doesn't exist

**Solution**:

```bash
# List concepts to find correct ID
sqlite3 short_term_mcp.db "SELECT concept_id, concept_name FROM concepts WHERE session_id = '2025-01-10';"

# Use correct concept_id
mcp call short-term-memory mark_concept_stored \
  --concept_id "actual-uuid-here" \
  --knowledge_mcp_id "knowledge-123"
```

## Research Cache Issues

### Debug Cache State

```bash
# Check cache contents
sqlite3 short_term_mcp.db "SELECT * FROM research_cache;"

# Check specific concept
sqlite3 short_term_mcp.db "SELECT * FROM research_cache WHERE concept_name = 'python asyncio';"

# Check cache statistics
sqlite3 short_term_mcp.db "
  SELECT
    COUNT(*) as total_entries,
    AVG(LENGTH(explanation)) as avg_explanation_length,
    MIN(created_at) as oldest_entry,
    MAX(created_at) as newest_entry
  FROM research_cache;
"
```

### Cache Not Working

**Symptom**: Cache always returns `"cached": false`

**Cause**:

1. Concept name mismatch (case-sensitive)
2. Cache not populated
3. Database migration not run

**Solution**:

```bash
# Check if research_cache table exists
sqlite3 short_term_mcp.db ".tables"

# If table missing, run migration
python -c "from short_term_mcp.database import get_db; get_db().migrate_to_research_cache_schema()"

# Check cache with exact name
mcp call short-term-memory check_research_cache --concept_name "python asyncio"

# Populate cache manually
mcp call short-term-memory update_research_cache \
  --concept_name "python asyncio" \
  --explanation "Async programming in Python" \
  --source_urls '[]'
```

### Clear Cache

```bash
# Clear all cache entries
sqlite3 short_term_mcp.db "DELETE FROM research_cache;"

# Clear specific concept
sqlite3 short_term_mcp.db "DELETE FROM research_cache WHERE concept_name = 'python asyncio';"

# Clear old entries (>30 days)
sqlite3 short_term_mcp.db "DELETE FROM research_cache WHERE created_at < datetime('now', '-30 days');"
```

### Cache Statistics

```bash
# Check cache hit rate (manually)
sqlite3 short_term_mcp.db "
  SELECT
    COUNT(*) as total_cached,
    COUNT(DISTINCT concept_name) as unique_concepts
  FROM research_cache;
"

# Check most frequently cached concepts
# (Would need access log - not currently tracked)
```

## Domain Whitelist Issues

### Check Domain Whitelist

```bash
# List all whitelisted domains
mcp call short-term-memory list_whitelisted_domains

# List by category
sqlite3 short_term_mcp.db "SELECT * FROM domain_whitelist WHERE category = 'official';"

# Check specific domain
sqlite3 short_term_mcp.db "SELECT * FROM domain_whitelist WHERE domain = 'docs.python.org';"
```

### Add Missing Domain

```bash
# Add domain to whitelist
mcp call short-term-memory add_domain_to_whitelist \
  --domain "numpy.org" \
  --category "official" \
  --quality_score 1.0
```

### Remove Invalid Domain

```bash
# Remove domain
mcp call short-term-memory remove_domain_from_whitelist --domain "example.com"
```

### Reset to Default Whitelist

```bash
# Clear all domains
sqlite3 short_term_mcp.db "DELETE FROM domain_whitelist;"

# Re-initialize (will populate defaults)
python -c "from short_term_mcp.database import get_db; db = get_db(); db._populate_initial_domains(); db.connection.commit()"
```

## Database Cleanup & Reset

### Clean Database (Complete Reset)

Use the cleanup script to completely reset the database while preserving domain whitelist configuration. This is useful for:

- Removing test data after development/testing
- Starting fresh when troubleshooting issues
- Cleaning up after experimental sessions

```bash
# Basic usage (with confirmation prompt)
python scripts/cleanup_database.py

# Skip confirmation prompt (use with caution!)
python scripts/cleanup_database.py --yes

# Create backup before cleaning
python scripts/cleanup_database.py --backup
```

**What gets deleted:**

- All sessions
- All concepts (CASCADE deletion)
- All concept stage data (CASCADE deletion)
- All research cache entries

**What gets preserved:**

- Domain whitelist configuration
- Database schema and indexes

**Output:**
The script shows:

- Current database state (counts before cleanup)
- Deletion confirmation prompt
- Cleanup results (items deleted, storage reclaimed)
- Database health check after cleanup

### Create Shell Alias (Recommended)

For easy access, create a shell alias:

```bash
# For bash (~/.bashrc or ~/.bash_profile)
echo "alias clean-short-term='python $(pwd)/scripts/cleanup_database.py'" >> ~/.bashrc
source ~/.bashrc

# For zsh (~/.zshrc)
echo "alias clean-short-term='python $(pwd)/scripts/cleanup_database.py'" >> ~/.zshrc
source ~/.zshrc

# Now you can run:
clean-short-term
clean-short-term --yes
clean-short-term --backup
```

### Clear Old Sessions (Selective Cleanup)

To remove only old sessions while keeping recent data:

```bash
# Via MCP tool (keeps last 7 days by default)
mcp call short-term-memory clear_old_sessions --days_to_keep 7

# Custom retention (keeps last 30 days)
mcp call short-term-memory clear_old_sessions --days_to_keep 30

# Via direct SQL (manual approach)
sqlite3 short_term_mcp.db "DELETE FROM sessions WHERE date < '2025-01-01';"
```

### Database Backup

```bash
# Manual backup before cleanup
cp data/short_term_memory.db data/short_term_memory_backup_$(date +%Y%m%d).db

# Or use the --backup flag with cleanup script
python scripts/cleanup_database.py --backup

# Backups are saved to: data/backups/short_term_memory_backup_YYYYMMDD_HHMMSS.db
```

### Restore from Backup

```bash
# Stop MCP server first (if running)

# Restore from backup
cp data/backups/short_term_memory_backup_20250110_120000.db data/short_term_memory.db

# Restart MCP server
```

### Vacuum Database (Reclaim Space)

After deleting large amounts of data, vacuum the database to reclaim disk space:

```bash
# Via SQLite
sqlite3 data/short_term_memory.db "VACUUM;"

# Cleanup script automatically runs VACUUM
python scripts/cleanup_database.py --yes
```

## Performance Issues

### Slow Database Operations

**Symptom**: Tools taking >1 second to respond

**Diagnosis**:

```bash
# Check database size
ls -lh short_term_mcp.db

# Check table sizes
sqlite3 short_term_mcp.db "
  SELECT
    name,
    (SELECT COUNT(*) FROM sessions) as sessions,
    (SELECT COUNT(*) FROM concepts) as concepts,
    (SELECT COUNT(*) FROM concept_stage_data) as stage_data,
    (SELECT COUNT(*) FROM research_cache) as cache_entries
  FROM sqlite_master WHERE type='table' LIMIT 1;
"
```

**Solutions**:

```bash
# Vacuum database (reclaim space)
sqlite3 short_term_mcp.db "VACUUM;"

# Analyze for query optimization
sqlite3 short_term_mcp.db "ANALYZE;"

# Clear old sessions (auto-cleanup)
mcp call short-term-memory clear_old_sessions --days_to_keep 7
```

### Cache Not Helping Performance

**Symptom**: No speedup from cache hits

**Diagnosis**:

1. Check cache hit rate in logs
2. Verify cache lookups are fast (<100ms)

**Solutions**:

```bash
# Run performance benchmark
pytest short_term_mcp/tests/benchmarks/test_research_cache_performance.py -v

# Check if indexes exist
sqlite3 short_term_mcp.db "
  SELECT name FROM sqlite_master
  WHERE type='index' AND tbl_name='research_cache';
"

# Recreate indexes if missing
sqlite3 short_term_mcp.db "
  CREATE INDEX IF NOT EXISTS idx_research_cache_name ON research_cache(concept_name);
  CREATE INDEX IF NOT EXISTS idx_research_cache_created ON research_cache(created_at);
"
```

## Database Corruption

### Detect Corruption

```bash
# Integrity check
sqlite3 short_term_mcp.db "PRAGMA integrity_check;"

# Should return: ok

# Check for foreign key violations
sqlite3 short_term_mcp.db "PRAGMA foreign_key_check;"
```

### Repair Database

```bash
# Backup first
cp short_term_mcp.db short_term_mcp_backup.db

# Export and re-import
sqlite3 short_term_mcp.db .dump > backup.sql
rm short_term_mcp.db
sqlite3 short_term_mcp.db < backup.sql
```

### Nuclear Option: Fresh Start

```bash
# Backup existing database
mv short_term_mcp.db short_term_mcp_old.db

# Restart server (will create new database)
# Database is auto-initialized on first run
```

## Transfer Issues (Knowledge MCP)

### Concepts Not Transferring

**Symptom**: `get_unstored_concepts` returns concepts but transfer fails

**Diagnosis**:

```bash
# Check unstored concepts
mcp call short-term-memory get_unstored_concepts --session_id "2025-01-10"

# Verify Knowledge MCP is running
mcp call knowledge list_concepts

# Check cache for URLs
mcp call short-term-memory check_research_cache --concept_name "python asyncio"
```

**Solution**:

```bash
# Manual transfer (example)
# 1. Get unstored concepts
# 2. For each concept:
#    - Check cache for URLs
#    - Create in Knowledge MCP
#    - Mark as stored

# If Knowledge MCP fails, check its logs
# If cache missing, re-research concept first
```

### Source URLs Not Transferred

**Symptom**: Concepts transferred but without URLs

**Cause**:

1. Cache miss (URLs not in cache)
2. Knowledge MCP doesn't support source_urls parameter
3. JSON serialization error

**Solution**:

```bash
# Check cache has URLs
mcp call short-term-memory check_research_cache --concept_name "python asyncio"

# Verify URL format (should be valid JSON)
sqlite3 short_term_mcp.db "
  SELECT concept_name, source_urls
  FROM research_cache
  WHERE concept_name = 'python asyncio';
"

# Check Knowledge MCP version (should support source_urls parameter)
# If not supported, URLs will be omitted (graceful fallback)
```

## Logging & Debugging

### Enable Debug Logging

```bash
# Set LOG_LEVEL in .env
echo "LOG_LEVEL=DEBUG" >> .env

# Restart server
# Now logs will show detailed cache operations
```

### Check Logs

```bash
# SHOOT stage logs cache statistics
# Look for:
# INFO: Cache HIT: python asyncio (age: 120s)
# INFO: Cache MISS: react hooks - triggering research
# INFO: Cache statistics: 7 hits, 3 misses (70.0% hit rate)
```

### Error Log

```bash
# Get recent errors via MCP
mcp call short-term-memory get_error_log --limit 10

# Check database error log (if table exists)
sqlite3 short_term_mcp.db "SELECT * FROM error_log ORDER BY timestamp DESC LIMIT 10;"
```

## Testing Issues

### Tests Failing

```bash
# Run all tests
pytest short_term_mcp/tests/ -v

# Run specific test
pytest short_term_mcp/tests/test_research_cache_integration.py::test_shoot_stage_full_workflow -v

# Run with debug output
pytest short_term_mcp/tests/ -v -s
```

### Clean Test Databases

```bash
# Remove test database files
rm -f test_*.db

# Re-run tests
pytest short_term_mcp/tests/ -v
```

## Environment Issues

### Wrong Python Version

```bash
# Check Python version (requires 3.10+)
python --version

# Use correct Python
python3.11 -m pytest short_term_mcp/tests/ -v
```

### Missing Dependencies

```bash
# Install dependencies
pip install -e .

# Or with uv
uv pip install -e .
```

### MCP Server Not Starting

```bash
# Check MCP configuration
cat ~/.config/mcp/settings.json

# Verify path in config
# Run manually to see errors
cd /path/to/Short-Term-Memory-MCP
uv run short-term-mcp
```

## Get Help

If you encounter issues not covered here:

1. Check logs for error messages
2. Run health check and system metrics
3. Verify database integrity
4. Check GitHub Issues: [Short-Term-Memory-MCP Issues](https://github.com/your-org/Short-Term-Memory-MCP/issues)
5. Review [PRD-Short-Term-Memory-MCP.md](PRD-Short-Term-Memory-MCP.md) for system architecture
6. Check [Concept-Transfer-Workflow.md](docs/Concept-Transfer-Workflow.md) for transfer issues

## Quick Reference

### Database Location

```bash
# Default location
./short_term_mcp.db

# Configured via .env
DB_PATH=short_term_mcp.db
```

### Important Tables

- `sessions` - Daily learning sessions
- `concepts` - Concepts through pipeline
- `research_cache` - Cached research results
- `domain_whitelist` - Trusted domains

### Key Tools

- `health_check` - System status
- `get_system_metrics` - Performance metrics
- `check_research_cache` - Cache status
- `clear_old_sessions` - Cleanup

### Performance Targets

- Cache hit: <100ms (P95)
- Tool execution: <1s (excluding research)
- Database size: <50MB (typical)
