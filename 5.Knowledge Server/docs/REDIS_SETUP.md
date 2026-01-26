# Redis Setup for Automated Confidence Scoring

## Overview

The automated confidence scoring system requires **Redis** for caching score calculations and intermediate results. Redis must be running for the confidence scoring feature to work.

## Why Redis is Required

- **Performance**: Caches confidence score calculations (TTL: 1 hour)
- **Efficiency**: Stores intermediate calculation data (relationships, review history)
- **Scalability**: Enables fast recalculation without repeatedly querying Neo4j

## Quick Start

### 1. Start Redis

```bash
# Start Redis as a background service
redis-server --daemonize yes

# Verify it's running
redis-cli ping
# Expected output: PONG
```

### 2. Verify Confidence Scoring

```bash
# Run the verification script
python scripts/verify_confidence_scoring.py
```

Expected output:

```
1. Checking Redis connectivity...
   ✅ Redis is running and responding
2. Connecting to Neo4j...
   ✅ Neo4j connected
3. Building confidence runtime...
   ✅ Confidence runtime initialized successfully
...
✅ VERIFICATION COMPLETE - Confidence scoring is working!
```

### 3. Backfill Existing Concepts

```bash
# Calculate scores for all concepts without automated scores
python scripts/backfill_confidence_scores.py

# Or recalculate ALL concepts
python scripts/backfill_confidence_scores.py --all

# Dry-run mode (calculate but don't save)
python scripts/backfill_confidence_scores.py --dry-run
```

### 4. Start MCP Server

```bash
python mcp_server.py
```

Look for these log messages:

```
✅ Confidence scoring runtime initialized
✅ Confidence event listener started
```

## Configuration

Redis connection settings (defaults shown):

```bash
# .env file
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=       # Leave empty for no authentication
```

## Troubleshooting

### Redis Not Running

**Symptom**: Server logs show:

```
⚠️  Confidence scoring runtime unavailable; automated certainty scores disabled.
```

**Solution**:

```bash
# Start Redis
redis-server --daemonize yes

# Check status
redis-cli ping
```

### Redis Connection Refused

**Symptom**: `Connection refused` error when connecting to Redis

**Solutions**:

1. Check if Redis is running:

   ```bash
   ps aux | grep redis-server
   ```

2. Check the port:

   ```bash
   redis-cli -p 6379 ping
   ```

3. Check firewall settings (if using remote Redis)

### All Concepts Return Score 0.0

**Symptom**: All concepts show `certainty_score: 0.0`

**Diagnosis**:

```bash
python scripts/verify_confidence_scoring.py
```

**Solutions**:

1. **Redis not running**: Start Redis (see above)

2. **Scores not calculated yet**:
   - New concepts: Wait 5-10 seconds for background worker
   - Existing concepts: Run backfill script

3. **Check Neo4j properties**:
   ```cypher
   MATCH (c:Concept)
   RETURN c.concept_id,
          c.certainty_score,
          c.certainty_score_auto,
          c.confidence_last_calculated
   LIMIT 5
   ```

## Redis Management

### Stop Redis

```bash
redis-cli shutdown
```

### Monitor Redis Activity

```bash
# Watch Redis commands in real-time
redis-cli monitor

# Get server stats
redis-cli info
```

### Clear Confidence Cache

```bash
# Clear all confidence-related keys
redis-cli KEYS "confidence:*" | xargs redis-cli DEL
```

## Production Deployment

For production environments:

1. **Use Redis with authentication**:

   ```bash
   REDIS_PASSWORD=your_secure_password
   ```

2. **Enable SSL/TLS**:

   ```bash
   REDIS_SSL=true
   REDIS_SSL_CERT_REQS=required
   ```

3. **Configure persistence**:

   ```bash
   # In redis.conf
   save 900 1      # Save after 900 sec if 1 key changed
   save 300 10     # Save after 300 sec if 10 keys changed
   save 60 10000   # Save after 60 sec if 10000 keys changed
   ```

4. **Set up monitoring**:
   - Monitor memory usage
   - Set maxmemory policy
   - Configure eviction strategy

## System Architecture

```
┌─────────────────────────────────────────────┐
│           MCP Knowledge Server              │
├─────────────────────────────────────────────┤
│                                             │
│  ┌────────────────────────────────────┐    │
│  │   Confidence Scoring Runtime       │    │
│  │                                    │    │
│  │  • Composite Calculator            │    │
│  │  • Understanding Calculator        │    │
│  │  • Retention Calculator            │    │
│  │  • Cache Manager ──────────┐      │    │
│  │  • Event Listener          │      │    │
│  └───────────────────────────┼──────┘    │
│                              │            │
└──────────────────────────────┼────────────┘
                               │
                               ▼
                    ┌──────────────────┐
                    │      Redis       │
                    │   Cache Layer    │
                    ├──────────────────┤
                    │ • Scores (1h)    │
                    │ • Relationships  │
                    │ • Review Data    │
                    └──────────────────┘
```

## Cache Key Structure

- **Scores**: `confidence:score:{concept_id}` (TTL: 1 hour)
- **Relationships**: `confidence:calc:relationships:{concept_id}` (TTL: 24 hours)
- **Review History**: `confidence:calc:review:{concept_id}` (TTL: 24 hours)

## Monitoring Confidence Scoring

### Check Runtime Status

```bash
# In Python REPL
from services.confidence.runtime import build_confidence_runtime
from services.neo4j_service import Neo4jService
import asyncio

neo4j = Neo4jService("bolt://localhost:7687", "neo4j", "password")
neo4j.connect()

runtime = asyncio.run(build_confidence_runtime(neo4j))
print(f"Runtime initialized: {runtime is not None}")
```

### Monitor Background Worker

```bash
# Check event listener checkpoint
cat services/confidence/cache/confidence_listener_checkpoint.json
```

Shows the last processed event offset.

### View Cached Scores

```bash
# Get all cached scores
redis-cli KEYS "confidence:score:*"

# Get specific concept score
redis-cli GET "confidence:score:your-concept-id-here"
```

## Performance Tuning

### Redis Memory Settings

```bash
# Set max memory (example: 256MB)
redis-cli CONFIG SET maxmemory 256mb

# Set eviction policy (remove least recently used keys)
redis-cli CONFIG SET maxmemory-policy allkeys-lru
```

### Cache TTL Adjustment

Edit `services/confidence/config.py`:

```python
# Increase/decrease cache lifetimes
SCORE_CACHE_TTL: int = 3600      # 1 hour (increase for less frequent recalc)
CALC_CACHE_TTL: int = 86400      # 24 hours
```

## Related Documentation

- [Confidence Scoring System](../System-Overview/05-CONFIDENCE-SCORING.md)
- [System Architecture](../System-Overview/03-ARCHITECTURE.md)
- [Issue Resolution Log](../System-Overview/Issue-List.md)
