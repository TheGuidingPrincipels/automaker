# Short-Term Memory MCP - Production Guide

**Version:** 1.0.0
**Status:** Production Ready
**Last Updated:** 2025-10-10

## Table of Contents

1. [Overview](#overview)
2. [Installation & Setup](#installation--setup)
3. [Claude Desktop Integration](#claude-desktop-integration)
4. [Configuration](#configuration)
5. [Monitoring & Health Checks](#monitoring--health-checks)
6. [Logging](#logging)
7. [Performance Tuning](#performance-tuning)
8. [Backup & Recovery](#backup--recovery)
9. [Troubleshooting](#troubleshooting)
10. [Security Considerations](#security-considerations)

---

## Overview

Short-Term Memory MCP is a production-ready Model Context Protocol server for tracking daily learning concepts through a structured pipeline. It provides:

- **22 MCP Tools** for complete concept lifecycle management
- **Structured Logging** with JSON formatting and rotation
- **Health Monitoring** with real-time metrics
- **Caching Layer** for optimal performance
- **SQLite Database** with WAL mode and auto-vacuum
- **7-Day Retention** with automatic cleanup

### System Requirements

- **Python**: 3.11 or higher
- **OS**: macOS, Linux, or Windows
- **Disk Space**: Minimum 100MB (database grows ~1KB per concept)
- **Memory**: Minimum 50MB RAM
- **Dependencies**: See `requirements.txt`

---

## Installation & Setup

### 1. Clone Repository

```bash
cd ~/Documents/GitHub
git clone https://github.com/yourusername/Short-Term-Memory-MCP.git
cd Short-Term-Memory-MCP
```

### 2. Create Virtual Environment

```bash
python3.11 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Verify Installation

```bash
# Run test suite
pytest short_term_mcp/tests/ -v

# Expected: 159 passed in ~2 seconds
```

### 5. Initialize Database

The database is automatically initialized on first run. To manually initialize:

```python
from short_term_mcp.database import get_db
db = get_db()
print(f"Database initialized at: {db.db_path}")
```

---

## Claude Desktop Integration

### Option 1: uv (Recommended)

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "short-term-memory": {
      "command": "uv",
      "args": [
        "--directory",
        "/Users/YOUR_USERNAME/Documents/GitHub/Short-Term-Memory-MCP",
        "run",
        "short-term-mcp"
      ]
    }
  }
}
```

### Option 2: Direct Python

```json
{
  "mcpServers": {
    "short-term-memory": {
      "command": "/Users/YOUR_USERNAME/Documents/GitHub/Short-Term-Memory-MCP/.venv/bin/python",
      "args": ["-m", "short_term_mcp.server"]
    }
  }
}
```

### Verification

1. Restart Claude Desktop
2. Open a new conversation
3. Type: "What MCP tools are available?"
4. Verify you see 22 tools from "Short-term Memory MCP"

### Available Tools

**Session Management (Tier 1):**

- `initialize_daily_session` - Start new learning session
- `get_active_session` - Get today's session with statistics

**Concept Tracking (Tier 1):**

- `store_concepts_from_research` - Bulk store concepts (up to 25)
- `get_concepts_by_session` - Query concepts with filters
- `update_concept_status` - Move through pipeline stages

**Stage Data (Tier 1):**

- `store_stage_data` - Store stage-specific data (AIM/SHOOT/SKIN)
- `get_stage_data` - Retrieve stage data

**Storage Integration (Tier 1):**

- `mark_concept_stored` - Link to Knowledge MCP
- `get_unstored_concepts` - Find incomplete transfers

**Session Completion (Tier 2):**

- `mark_session_complete` - Complete session with validation
- `clear_old_sessions` - Manual cleanup of old data
- `get_concepts_by_status` - Filter by pipeline status

**Code Teacher Support (Tier 3):**

- `get_todays_concepts` - Full concept list (cached 5 min)
- `get_todays_learning_goals` - Lightweight goals query (cached)
- `search_todays_concepts` - Search by name/content (cached)

**Knowledge Graph (Tier 4):**

- `add_concept_question` - Track user questions
- `get_concept_page` - Complete concept view with timeline
- `add_concept_relationship` - Build concept relationships
- `get_related_concepts` - Query relationship graph

**Monitoring (Tier 5):**

- `health_check` - System health status
- `get_system_metrics` - Performance metrics
- `get_error_log` - Recent error entries

---

## Configuration

### Configuration File

Location: `/Users/YOUR_USERNAME/Documents/GitHub/Short-Term-Memory-MCP/short_term_mcp/config.py`

```python
# Paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
LOG_DIR = PROJECT_ROOT / "logs"
DB_PATH = DATA_DIR / "short_term_memory.db"

# Database settings
DB_RETENTION_DAYS = 7  # Auto-delete sessions older than 7 days
ENABLE_WAL = True      # Write-Ahead Logging for concurrency
AUTO_VACUUM = True     # Automatic database cleanup

# Performance settings
QUERY_TIMEOUT = 5.0    # Query timeout in seconds
BATCH_SIZE = 25        # Maximum concepts per batch operation
CACHE_TTL = 300        # Cache TTL in seconds (5 minutes)
```

### Environment-Specific Configuration

**Development:**

```python
DB_RETENTION_DAYS = 1  # Shorter retention for testing
CACHE_TTL = 60         # Faster cache expiration
```

**Production:**

```python
DB_RETENTION_DAYS = 7  # Standard 7-day retention
CACHE_TTL = 300        # 5-minute cache for optimal performance
```

### Customizing Retention

To keep data longer:

```python
# In config.py
DB_RETENTION_DAYS = 14  # Keep 2 weeks of data

# Or use manual cleanup
from short_term_mcp import tools_impl
await tools_impl.clear_old_sessions_impl(days_to_keep=14)
```

---

## Monitoring & Health Checks

### Health Check

Use the `health_check` tool to verify system status:

```python
# Via MCP
result = await health_check()

# Expected response:
{
    "status": "success",
    "overall_status": "healthy",  # or "degraded"
    "timestamp": "2025-10-10T12:34:56",
    "response_time_ms": 12.34,
    "components": {
        "database": {
            "status": "healthy",
            "connection": "active",
            "integrity": "ok",
            "size_bytes": 123456
        },
        "cache": {
            "status": "operational",
            "size": 5,
            "ttl_seconds": 300
        }
    }
}
```

**Health Status Indicators:**

- `healthy` - All components operational
- `degraded` - Some components have issues
- `disconnected` - Database not connected
- `error` - Critical failure

### System Metrics

Use `get_system_metrics` for detailed performance data:

```python
result = await get_system_metrics()

# Returns:
{
    "database": {
        "size_mb": 0.12,           # Database file size
        "sessions": 3,             # Total sessions
        "concepts": 75,            # Total concepts
        "stage_data_entries": 300  # Stage data records
    },
    "operations": {
        "reads": 150,              # Read operations
        "writes": 75,              # Write operations
        "queries": 225,            # Query operations
        "errors": 0                # Error count
    },
    "performance": {
        "read_times": {
            "count": 150,
            "avg_ms": 0.5,
            "min_ms": 0.1,
            "max_ms": 2.0
        },
        // ... write_times, query_times
    },
    "cache": {
        "entries": 5,              # Cached items
        "ttl_seconds": 300         # Cache TTL
    }
}
```

### Error Monitoring

Use `get_error_log` to retrieve recent errors:

```python
# Get last 10 errors
result = await get_error_log(limit=10)

# Filter by error type
result = await get_error_log(limit=50, error_type="DatabaseError")

# Response:
{
    "error_count": 2,
    "errors": [
        {
            "timestamp": "2025-10-10T12:34:56",
            "error_type": "DatabaseError",
            "message": "Connection timeout",
            "context": {"operation": "query", "duration_ms": 5001}
        }
    ]
}
```

### Monitoring Best Practices

1. **Regular Health Checks**: Run `health_check` at start of each session
2. **Metrics Review**: Check `get_system_metrics` weekly to identify trends
3. **Error Alerting**: Monitor `get_error_log` for recurring issues
4. **Database Size**: Keep database under 10MB for optimal performance

---

## Logging

### Log Files

**Location:** `/Users/YOUR_USERNAME/Documents/GitHub/Short-Term-Memory-MCP/logs/`

**Files:**

- `short_term_mcp.log` - All application logs (JSON format)
- `errors.log` - Error-level logs only (JSON format)

### Log Rotation

- **Max Size:** 10MB per file
- **Backups:** 5 rotating backups
- **Format:** JSON (production), colored text (console)

### Log Levels

```python
# In logging_config.py
setup_logging(
    log_level="INFO",           # DEBUG, INFO, WARNING, ERROR, CRITICAL
    enable_file_logging=True,   # Write to files
    enable_console_logging=True # Print to console
)
```

**Recommended Levels:**

- **Development:** DEBUG - See all operations
- **Production:** INFO - Normal operations only
- **Troubleshooting:** DEBUG - Detailed diagnostics

### Log Format (JSON)

```json
{
  "timestamp": "2025-10-10T12:34:56.789",
  "level": "INFO",
  "logger": "short_term_mcp.database",
  "message": "create_concept completed",
  "module": "database",
  "function": "create_concept",
  "line": 142,
  "extra_data": {
    "operation": "create_concept",
    "duration_ms": 1.23,
    "success": true
  }
}
```

### Viewing Logs

```bash
# Tail application logs
tail -f logs/short_term_mcp.log | jq .

# View errors only
tail -f logs/errors.log | jq .

# Search for specific operations
cat logs/short_term_mcp.log | jq 'select(.extra_data.operation == "create_concept")'

# Filter by time period
cat logs/short_term_mcp.log | jq 'select(.timestamp > "2025-10-10T12:00:00")'
```

### Log Cleanup

```bash
# Remove old logs
find logs/ -name "*.log.*" -mtime +30 -delete

# Archive logs
tar -czf logs_archive_$(date +%Y%m%d).tar.gz logs/*.log
```

---

## Performance Tuning

### Performance Targets

| Operation                     | Target | Actual |
| ----------------------------- | ------ | ------ |
| Health Check                  | <50ms  | 12ms   |
| Batch Insert (25 concepts)    | <100ms | 2.5ms  |
| Query Session Concepts        | <50ms  | 0.1ms  |
| Individual Update             | <20ms  | <1ms   |
| Complete Pipeline             | <5s    | 0.02s  |
| Code Teacher Queries (cached) | <1ms   | <1ms   |

### Optimization Strategies

#### 1. Database Optimization

**Enable WAL Mode** (already enabled):

```sql
PRAGMA journal_mode=WAL;
```

**Optimize Indexes:**

```sql
-- Analyze query patterns
ANALYZE;

-- Check index usage
EXPLAIN QUERY PLAN SELECT * FROM concepts WHERE session_id = ?;
```

**Vacuum Regularly:**

```bash
# Manual vacuum (done automatically)
sqlite3 data/short_term_memory.db "VACUUM;"
```

#### 2. Cache Optimization

**Increase Cache TTL for stable data:**

```python
# In config.py
CACHE_TTL = 600  # 10 minutes instead of 5
```

**Pre-warm cache at session start:**

```python
# Warm cache for today's concepts
await get_todays_concepts_impl()
```

#### 3. Batch Operations

**Use bulk operations:**

```python
# Good: Batch insert
await store_concepts_from_research(session_id, concepts)

# Avoid: Individual inserts
for concept in concepts:
    await create_concept(concept)  # Slower
```

#### 4. Query Optimization

**Use indexed columns:**

```python
# Good: Indexed column
get_concepts_by_session(session_id)  # Uses idx_concepts_session

# Avoid: Full table scan
get_all_concepts()  # No index
```

### Performance Monitoring

```python
# Get performance metrics
metrics = await get_system_metrics_impl()

# Check operation times
print(f"Average read time: {metrics['performance']['read_times']['avg_ms']}ms")
print(f"Max write time: {metrics['performance']['write_times']['max_ms']}ms")

# Identify slow operations
if metrics['performance']['query_times']['max_ms'] > 100:
    print("WARNING: Slow queries detected")
```

---

## Backup & Recovery

### Database Backup

#### Manual Backup

```bash
# Create backup
cp data/short_term_memory.db data/backups/short_term_memory_$(date +%Y%m%d).db

# Verify backup
sqlite3 data/backups/short_term_memory_20251010.db "PRAGMA integrity_check;"
```

#### Automated Backup

```bash
# Add to crontab (daily at 2 AM)
0 2 * * * cd /Users/YOUR_USERNAME/Documents/GitHub/Short-Term-Memory-MCP && cp data/short_term_memory.db data/backups/short_term_memory_$(date +\%Y\%m\%d).db
```

#### Backup Strategy

1. **Daily Backups**: Keep last 7 days
2. **Weekly Backups**: Keep last 4 weeks
3. **Monthly Backups**: Keep last 3 months

```bash
# Backup script
#!/bin/bash
BACKUP_DIR="data/backups"
DB_FILE="data/short_term_memory.db"

# Create backup
cp $DB_FILE $BACKUP_DIR/short_term_memory_$(date +%Y%m%d).db

# Clean old daily backups (keep 7 days)
find $BACKUP_DIR -name "short_term_memory_*.db" -mtime +7 -delete
```

### Recovery

#### From Backup

```bash
# Stop MCP server (restart Claude Desktop)

# Restore from backup
cp data/backups/short_term_memory_20251010.db data/short_term_memory.db

# Verify integrity
sqlite3 data/short_term_memory.db "PRAGMA integrity_check;"
```

#### Database Corruption

```bash
# Check for corruption
sqlite3 data/short_term_memory.db "PRAGMA integrity_check;"

# If corrupted, try recovery
sqlite3 data/short_term_memory.db ".dump" | sqlite3 data/short_term_memory_recovered.db

# Replace corrupted database
mv data/short_term_memory.db data/short_term_memory_corrupted.db
mv data/short_term_memory_recovered.db data/short_term_memory.db
```

---

## Troubleshooting

### Common Issues

#### 1. Database Locked

**Symptom:** `sqlite3.OperationalError: database is locked`

**Causes:**

- Multiple connections without WAL mode
- Long-running transaction
- Crashed process holding lock

**Solutions:**

```bash
# Check for lock file
ls -la data/short_term_memory.db-shm data/short_term_memory.db-wal

# Kill stale processes
ps aux | grep short_term_mcp

# Restart Claude Desktop
# Or manually close database
```

#### 2. Cache Import Error

**Symptom:** `ImportError: cannot import name 'cache' from 'short_term_mcp.utils'`

**Solution:**

```python
# Verify utils.py exports cache
from short_term_mcp.utils import cache  # Should work

# If not, add to utils.py:
cache = SimpleCache()
```

#### 3. Slow Queries

**Symptom:** Queries taking >50ms

**Diagnosis:**

```python
metrics = await get_system_metrics_impl()
if metrics['performance']['query_times']['avg_ms'] > 50:
    # Check database size
    if metrics['database']['size_mb'] > 10:
        # Database too large, run cleanup
        await clear_old_sessions_impl(days_to_keep=7)
```

**Solutions:**

- Run `VACUUM` to defragment database
- Reduce retention period
- Check for missing indexes

#### 4. Memory Leaks

**Symptom:** Increasing memory usage over time

**Diagnosis:**

```python
# Check metrics growth
metrics = db.get_metrics()
print(f"Read times tracked: {len(db.metrics['timing']['read_times'])}")
print(f"Errors tracked: {len(db.metrics['errors'])}")
```

**Solutions:**

- Verify metrics are capped (1000 timing records, 100 errors)
- Check for orphaned cache entries
- Restart MCP server periodically

### Debug Mode

Enable verbose logging for troubleshooting:

```python
# In logging_config.py or server.py
setup_logging(log_level="DEBUG")
```

### Getting Help

1. **Check logs**: Review `logs/errors.log` for error details
2. **Run health check**: Verify system status
3. **Check metrics**: Look for anomalies in operation counts
4. **GitHub Issues**: Report bugs with logs and reproduction steps

---

## Security Considerations

### Data Security

1. **Local Storage Only**: All data stored locally in SQLite database
2. **No Network Exposure**: MCP server runs locally, no external connections
3. **File Permissions**: Ensure restrictive permissions on database

```bash
# Secure database file
chmod 600 data/short_term_memory.db

# Secure logs directory
chmod 700 logs/
```

### Sensitive Data

- **Do not store**: Passwords, API keys, personal identifying information
- **Concept data**: Publicly shareable learning content only
- **Questions**: Assume questions may be logged

### Access Control

- **File-based**: Access controlled by OS file permissions
- **Single User**: Designed for individual use, not multi-user
- **Claude Desktop**: Inherits Claude Desktop security model

### Best Practices

1. **Regular Backups**: Protect against data loss
2. **Log Rotation**: Prevent log files from growing indefinitely
3. **Cleanup Old Data**: Use 7-day retention by default
4. **Review Logs**: Periodically check for suspicious activity

---

## Production Checklist

Before deploying to Claude Desktop:

### Pre-Deployment

- [ ] All 159 tests passing
- [ ] Database initialized successfully
- [ ] Log directory created with proper permissions
- [ ] Configuration reviewed and customized
- [ ] Backup strategy implemented

### Integration

- [ ] Claude Desktop config file updated
- [ ] MCP server registered and recognized
- [ ] All 22 tools visible in Claude Desktop
- [ ] Health check returns "healthy" status

### Monitoring

- [ ] Health checks scheduled (start of each session)
- [ ] Metrics review process established (weekly)
- [ ] Error log monitoring configured
- [ ] Log rotation verified (10MB max, 5 backups)

### Maintenance

- [ ] Backup schedule configured (daily/weekly/monthly)
- [ ] Old session cleanup verified (7-day retention)
- [ ] Database size monitoring enabled
- [ ] Performance targets validated

---

## Support & Resources

### Documentation

- [System Plan](System-Plan.md) - Complete implementation plan
- [API Documentation](API-Complete.md) - All 22 tools documented
- [Integration Testing](Integration-Testing.md) - Test workflow examples
- [Code Teacher API](Code-Teacher-API.md) - Code Teacher integration
- [Future Features API](Future-Features-API.md) - Knowledge graph features

### Performance

- **All Tests**: 159 passed in 2.24 seconds
- **Tool Count**: 22 MCP tools
- **Database Size**: ~1KB per concept
- **Cache Performance**: <1ms hit, <50ms miss

### Version

- **Version**: 1.0.0
- **Status**: Production Ready
- **Python**: 3.11+
- **FastMCP**: 2.12.4+
- **Last Updated**: 2025-10-10

---

**End of Production Guide**
