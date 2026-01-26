# Short-Term Memory MCP 🧠

**A Model Context Protocol Server for Daily Concept Tracking**

[![Tests](https://img.shields.io/badge/tests-159%20passed-success)]()
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)]()
[![Status](https://img.shields.io/badge/status-production%20ready-brightgreen)]()
[![FastMCP](https://img.shields.io/badge/FastMCP-2.12.4%2B-purple)]()

Track your daily learning concepts through a structured pipeline with built-in monitoring, caching, and knowledge graph capabilities.

## ✨ Features

- **22 MCP Tools** for complete concept lifecycle management
- **5-Stage Pipeline**: Research → AIM → SHOOT → SKIN → Storage
- **Real-time Monitoring**: Health checks, metrics, and error logging
- **5-Minute Caching**: Optimized for Code Teacher integration
- **Knowledge Graph**: Track relationships and questions
- **Structured Logging**: JSON logs with rotation (10MB max, 5 backups)
- **Auto-Cleanup**: 7-day retention with cascade deletion
- **Production Ready**: 159 tests, 100% pass rate, comprehensive docs

## 🚀 Quick Start

### Installation

```bash
# Clone repository
cd ~/Documents/GitHub
git clone https://github.com/yourusername/Short-Term-Memory-MCP.git
cd Short-Term-Memory-MCP

# Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest short_term_mcp/tests/ -v
```

### Claude Desktop Integration

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

Restart Claude Desktop and verify with: _"What MCP tools are available?"_

## 📋 Available Tools

### Tier 1: Core Pipeline (9 tools)

- `initialize_daily_session` - Start new learning session
- `get_active_session` - Get today's session with stats
- `store_concepts_from_research` - Bulk concept insertion (up to 25)
- `get_concepts_by_session` - Query concepts with filters
- `update_concept_status` - Move through pipeline stages
- `store_stage_data` - Save stage-specific data
- `get_stage_data` - Retrieve stage data
- `mark_concept_stored` - Link to Knowledge MCP
- `get_unstored_concepts` - Find incomplete transfers

### Tier 2: Reliability (3 tools)

- `mark_session_complete` - Complete session with validation
- `clear_old_sessions` - Manual cleanup of old data
- `get_concepts_by_status` - Filter by pipeline status

### Tier 3: Code Teacher Support (3 tools)

- `get_todays_concepts` - Full concept list (cached 5 min)
- `get_todays_learning_goals` - Lightweight goals query (cached)
- `search_todays_concepts` - Search by name/content (cached)

### Tier 4: Knowledge Graph (4 tools)

- `add_concept_question` - Track user questions
- `get_concept_page` - Complete concept view with timeline
- `add_concept_relationship` - Build concept relationships
- `get_related_concepts` - Query relationship graph

### Tier 5: Production Monitoring (3 tools)

- `health_check` - System health status (<50ms)
- `get_system_metrics` - Performance metrics
- `get_error_log` - Recent error entries with filtering

## 🔄 Daily Workflow

```mermaid
graph LR
    A[Research Session] --> B[Identify 25 Concepts]
    B --> C[AIM: Chunk & Questions]
    C --> D[SHOOT: Encode & Self-Explain]
    D --> E[SKIN: Evaluate Understanding]
    E --> F[Transfer to Knowledge MCP]
    F --> G[Mark Session Complete]
```

### Example Usage

```python
# 1. Initialize session
session = await initialize_daily_session(
    learning_goal="Learn React Hooks",
    building_goal="Build todo app"
)

# 2. Store concepts from Research
concepts = [{"concept_name": "useState", "data": {...}}, ...]
await store_concepts_from_research(session["session_id"], concepts)

# 3-5. Process through AIM, SHOOT, SKIN stages
# (see API-Complete.md for full workflow)

# 6. Complete session
await mark_session_complete(session["session_id"])
```

## 📊 Performance

| Operation         | Target | Actual |
| ----------------- | ------ | ------ |
| Health Check      | <50ms  | ~12ms  |
| Batch Insert (25) | <100ms | ~2.5ms |
| Query Session     | <50ms  | ~0.1ms |
| Complete Pipeline | <5s    | ~0.02s |
| Cache Hit         | <1ms   | <1ms   |

**Test Suite:**

- 159 tests across 7 phases
- 100% pass rate
- Execution time: 2.24 seconds

## 🗂️ Architecture

### Database Schema

- **sessions**: Daily learning sessions
- **concepts**: Individual concepts with status tracking
- **concept_stage_data**: Stage-specific incremental data

### Storage Strategy

- **Hybrid**: Cumulative data in concepts.current_data + incremental in stage_data
- **Retention**: 7-day auto-cleanup (configurable)
- **Optimization**: SQLite WAL mode, auto-vacuum, 7 performance indexes

### Caching

- **TTL**: 5 minutes (300 seconds)
- **Thread-safe**: Lock-based concurrency
- **Targets**: Code Teacher queries, session data

## 📚 Documentation

- **[Production Guide](Production-Guide.md)** - Complete deployment & operations guide
- **[API Reference](API-Complete.md)** - All 22 tools documented with examples
- **[System Plan](System-Plan.md)** - Implementation plan & progress tracker
- **[Integration Testing](Integration-Testing.md)** - Test workflows & examples
- **[Code Teacher API](Code-Teacher-API.md)** - Detailed Code Teacher integration
- **[Future Features API](Future-Features-API.md)** - Knowledge graph features

## 🔧 Configuration

Location: `short_term_mcp/config.py`

```python
# Database settings
DB_RETENTION_DAYS = 7    # Auto-delete after 7 days
ENABLE_WAL = True        # Concurrent access
AUTO_VACUUM = True       # Auto-cleanup

# Performance
QUERY_TIMEOUT = 5.0      # Query timeout (seconds)
BATCH_SIZE = 25          # Max concepts per batch
CACHE_TTL = 300          # Cache TTL (5 minutes)
```

## 🔍 Monitoring

### Health Check

```python
result = await health_check()
# Returns: overall_status, database health, cache status, response time
```

### System Metrics

```python
metrics = await get_system_metrics()
# Returns: database size, operation counts, performance stats, cache info
```

### Error Logging

```python
errors = await get_error_log(limit=10, error_type="DatabaseError")
# Returns: recent errors with timestamps, types, messages, context
```

## 🧪 Testing

```bash
# Run all tests
pytest short_term_mcp/tests/ -v

# Run specific phase
pytest short_term_mcp/tests/test_production.py -v

# With coverage
pytest short_term_mcp/tests/ --cov=short_term_mcp --cov-report=term-missing

# Performance tests only
pytest short_term_mcp/tests/ -k "performance" -v
```

**Test Organization:**

- Phase 0: Setup (3 tests)
- Phase 1: Database (24 tests)
- Phase 2: Core Tools (24 tests)
- Phase 3: Integration (19 tests)
- Phase 4: Reliability (17 tests)
- Phase 5: Code Teacher (20 tests)
- Phase 6: Knowledge Graph (25 tests)
- Phase 7: Production (27 tests)

## 📁 Project Structure

```
Short-Term-Memory-MCP/
├── short_term_mcp/
│   ├── __init__.py
│   ├── server.py           # FastMCP server (22 tools)
│   ├── database.py         # SQLite operations + metrics
│   ├── models.py           # Pydantic models
│   ├── tools_impl.py       # Tool implementations
│   ├── utils.py            # Cache + helpers
│   ├── config.py           # Configuration
│   ├── logging_config.py   # Structured logging
│   └── tests/
│       ├── test_setup.py
│       ├── test_database.py
│       ├── test_tools.py
│       ├── test_integration.py
│       ├── test_reliability_tools.py
│       ├── test_code_teacher.py
│       ├── test_future_features.py
│       ├── test_production.py
│       └── fixtures/
│           └── mock_data.py
├── data/
│   └── short_term_memory.db
├── logs/
│   ├── short_term_mcp.log
│   └── errors.log
├── docs/
│   ├── Production-Guide.md
│   ├── API-Complete.md
│   ├── System-Plan.md
│   ├── Integration-Testing.md
│   ├── Code-Teacher-API.md
│   └── Future-Features-API.md
├── requirements.txt
└── README.md
```

## 🛡️ Security

- **Local Storage**: All data stored locally in SQLite
- **No Network Exposure**: MCP server runs locally only
- **File Permissions**: Restrictive permissions on database (chmod 600)
- **No Secrets**: Do not store passwords, API keys, or PII

## 🔄 Backup & Recovery

### Backup Strategy

```bash
# Daily backups (keep 7 days)
cp data/short_term_memory.db data/backups/short_term_memory_$(date +%Y%m%d).db

# Automated with crontab (2 AM daily)
0 2 * * * cd /path/to/Short-Term-Memory-MCP && cp data/short_term_memory.db data/backups/short_term_memory_$(date +\%Y\%m\%d).db
```

### Recovery

```bash
# Restore from backup
cp data/backups/short_term_memory_20251010.db data/short_term_memory.db

# Verify integrity
sqlite3 data/short_term_memory.db "PRAGMA integrity_check;"
```

## 🐛 Troubleshooting

### Database Locked

```bash
# Restart Claude Desktop
# Or manually close database
rm data/short_term_memory.db-shm data/short_term_memory.db-wal
```

### Slow Queries

```python
# Check metrics
metrics = await get_system_metrics()
if metrics['database']['size_mb'] > 10:
    # Run cleanup
    await clear_old_sessions(days_to_keep=7)
```

### View Logs

```bash
# Tail application logs
tail -f logs/short_term_mcp.log | jq .

# View errors only
tail -f logs/errors.log | jq .
```

## 📈 Roadmap

### Completed ✅

- [x] Phase 0: Project Setup
- [x] Phase 1: Core Database (97% coverage)
- [x] Phase 2: Critical Tools (9 tools)
- [x] Phase 3: Pipeline Integration
- [x] Phase 4: Reliability Tools (3 tools)
- [x] Phase 5: Code Teacher Support (3 tools)
- [x] Phase 6: Knowledge Graph (4 tools)
- [x] Phase 7: Production Readiness (3 tools)

### Future Enhancements 🔮

- [ ] Web dashboard for metrics visualization
- [ ] Export concepts to Markdown/JSON
- [ ] Spaced repetition scheduling
- [ ] Integration with other MCP servers
- [ ] Concept similarity analysis
- [ ] Auto-chunking suggestions

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new features
4. Ensure all 159 tests pass
5. Submit a pull request

### Development Setup

```bash
# Install dev dependencies
pip install -r requirements.txt
pip install pytest pytest-asyncio pytest-cov

# Run tests before committing
pytest short_term_mcp/tests/ -v
```

## 📄 License

MIT License - See LICENSE file for details

## 🙏 Acknowledgments

- Built with [FastMCP](https://github.com/jlowin/fastmcp)
- Inspired by the [Model Context Protocol](https://modelcontextprotocol.io/)
- Part of the Personal Learning System architecture

## 📞 Support

- **Documentation**: See `docs/` directory
- **Issues**: GitHub Issues
- **Discussions**: GitHub Discussions

---

**Status:** ✅ Production Ready (v1.0.0)
**Last Updated:** 2025-10-10
**Tests:** 159 passed, 100% pass rate
**Tools:** 22 MCP tools across 5 tiers
**Performance:** All targets met or exceeded

Made with ❤️ for daily learning
