# Automaker Development & Testing Strategy

## Overview

This guide describes how to develop ON Automaker while simultaneously USING it as a development tool. The dual-instance architecture allows you to work on features while having a stable version available.

## Quick Start

### Recommended: Electron Mode
```bash
cd /Users/ruben/Documents/GitHub/automaker
npm run dev:electron
```

This launches Automaker as a desktop application with an embedded server.

### Alternative: Web Mode
```bash
cd /Users/ruben/Documents/GitHub/automaker
npm run dev:web
```
- UI: http://localhost:3007
- Server: http://localhost:3008

### Interactive Launcher
```bash
./start-automaker.sh
```
Presents a TUI menu with options:
1. Web App (browser mode)
2. Electron (desktop app)
3. Docker (containerized)
4. Electron + Docker (hybrid)

---

## Dual-Instance Architecture

For developing ON Automaker while USING it:

| Instance | Purpose | UI Port | Server Port | Location |
|----------|---------|---------|-------------|----------|
| **STABLE** | Production-like tool | 3007 | 3008 | Main repo |
| **DEV** | Code being modified | 4007 | 4008 | Git worktree |

### Setting Up DEV Instance

1. **Create a worktree for feature development:**
   ```bash
   cd /Users/ruben/Documents/GitHub/automaker
   git worktree add ../automaker-dev feature/my-feature
   cd ../automaker-dev
   npm install
   ```

2. **Run DEV instance on different ports:**
   ```bash
   TEST_PORT=4007 PORT=4008 VITE_SERVER_URL="http://localhost:4008" CORS_ORIGIN="http://localhost:4007" npm run dev:web
   ```

3. **Use STABLE instance to test DEV:**
   - Open STABLE at http://localhost:3007
   - Use it to interact with/verify DEV at http://localhost:4007

---

## Key Commands Reference

### Development
```bash
# Interactive launcher (recommended)
npm run dev                    # or ./start-automaker.sh

# Direct modes
npm run dev:web               # Web browser mode
npm run dev:electron          # Desktop app mode
npm run dev:docker            # Docker containerized
npm run dev:full              # Server + Web concurrently
```

### Building
```bash
npm run build:packages        # Build shared packages (required before dev)
npm run build                 # Build everything
npm run build:electron        # Build Electron distributable
```

### Testing
```bash
npm run test                  # UI tests
npm run test:server           # Server tests
npm run test:unit             # Unit tests
npm run test:all              # All tests
```

---

## Port Configuration

Default ports:
- **Web UI**: 3007
- **Server API**: 3008

### Custom ports via environment variables:
```bash
TEST_PORT=4007        # Vite UI port
PORT=4008             # Express server port
VITE_SERVER_URL="http://localhost:4008"
CORS_ORIGIN="http://localhost:4007"
```

---

## MCP Integration for Testing

Automaker includes built-in MCP server management. When developing features, you can:

1. **Use Chrome MCP from Claude Code** to interact with the UI
2. **Navigate** to verify feature implementations
3. **Take screenshots** for documentation
4. **Read page elements** to verify rendering

### Example workflow with Claude Code:
```
1. Start Automaker DEV instance (port 4007)
2. Use Chrome MCP to navigate to http://localhost:4007
3. Use read_page to verify UI elements
4. Use computer tool to interact with features
5. Verify behavior matches expectations
```

---

## Feature Development Workflow

1. **Create feature branch/worktree**
   ```bash
   git worktree add ../automaker-feature feature/my-feature
   ```

2. **Start DEV instance** on alternate ports

3. **Implement feature** with hot reload

4. **Test using STABLE instance** or Chrome MCP

5. **Run tests**
   ```bash
   npm run test
   ```

6. **Create PR** when complete

---

## Troubleshooting

### Port Conflicts
The launcher script (`start-automaker.sh`) automatically detects and offers to kill processes on ports 3007/3008.

Manual check:
```bash
lsof -i :3007
lsof -i :3008
```

### Hot Reload Issues
If changes aren't reflecting:
1. Check terminal for errors
2. Try `npm run build:packages` to rebuild shared code
3. Restart the dev server

### Electron Not Starting
- Ensure ports are available
- Try `npm run dev:electron:debug` for verbose output
- Check that node_modules are installed

### Docker Mode Issues
- Verify Docker is running: `docker info`
- First run takes time (building images)
- Use `docker compose logs` to debug

---

## Dependencies

- **Node.js**: >=22.0.0 <23.0.0 (required)
- **npm**: Comes with Node.js
- **Docker**: Optional, for containerized mode
- **Chrome**: For browser testing and MCP integration

---

## Desktop Launcher

### macOS - Terminal Launcher
File: `Start-Automaker.command`

To use:
1. Make executable: `chmod +x Start-Automaker.command`
2. Double-click to launch in Terminal

### macOS - AppleScript App
File: `Automaker-Launcher.applescript`

To create app:
1. Open in Script Editor
2. File > Export > Application
3. Save to Desktop

---

## Version Info

- **Automaker**: v0.12.0rc
- **Mode**: Autonomous AI Development Studio
