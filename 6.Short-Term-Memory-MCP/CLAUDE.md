# Short-Term Memory MCP - Development Guidelines

## 🚨 CRITICAL: Documentation Maintenance

**ALWAYS update [PRD-Short-Term-Memory-MCP.md](PRD-Short-Term-Memory-MCP.md) when:**

- Adding new MCP tools
- Changing database schema
- Modifying pipeline stages or workflow
- Adding/removing session types
- Changing tool tier organization
- Updating performance targets
- Modifying configuration options

**PRD is the single source of truth** - keep it synchronized with actual implementation.

---

## 📚 Core Documentation

Reference these in order:

1. **[PRD-Short-Term-Memory-MCP.md](PRD-Short-Term-Memory-MCP.md)** - System architecture
2. **[Session-System-Prompts-Guide.md](Session-System-Prompts-Guide.md)** - Session instructions
3. **[TROUBLESHOOTING-GUIDE.md](TROUBLESHOOTING-GUIDE.md)** - Debug & recovery

---

## 🧪 Testing

- **Maintain 100% pass rate** (159 tests)
- Add tests for all new features
- Run `pytest short_term_mcp/tests/ -v` before committing

---

## 🔧 Adding New Tools

1. Register in [server.py](short_term_mcp/server.py) with `@mcp.tool()` decorator
2. Implement in [tools_impl.py](short_term_mcp/tools_impl.py)
3. Update PRD tool catalog with new tool
4. Add to appropriate tier and session guide
5. Write tests in `short_term_mcp/tests/`

---

## 📊 Database Changes

- Update [database.py](short_term_mcp/database.py) schema
- Update [models.py](short_term_mcp/models.py) Pydantic models
- Update PRD database schema section
- Add migration logic if needed
- Test with existing data
