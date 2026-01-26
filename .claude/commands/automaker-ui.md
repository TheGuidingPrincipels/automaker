# Automaker UI Browser Automation

Browser automation for testing/verifying Automaker web UI via Chrome MCP.

## Critical Rules

1. **Load only necessary tools** - Use `ToolSearch` to load ONLY the specific tools needed for the task
2. **Stay focused** - Complete the user's task efficiently, don't explore unnecessarily
3. **Minimize screenshots** - Take screenshots only when needed to verify or debug
4. **Stop on issues** - If stuck after 2-3 attempts, report and ask for guidance

## Quick Start

```
1. ToolSearch: "select:mcp__claude-in-chrome__tabs_context_mcp"
2. Call tabs_context_mcp (createIfEmpty: true)
3. ToolSearch: "select:mcp__claude-in-chrome__navigate"
4. Navigate to http://localhost:3017
5. Load additional tools as needed for the specific task
```

## Tool Reference

**Load via ToolSearch** with `select:mcp__claude-in-chrome__<tool_name>`

| Tool                    | When to Load                    |
| ----------------------- | ------------------------------- |
| `tabs_context_mcp`      | Always first                    |
| `navigate`              | Changing pages                  |
| `computer`              | Clicking, typing, screenshots   |
| `read_page`             | Finding element refs            |
| `find`                  | Natural language element search |
| `form_input`            | Setting input values            |
| `read_console_messages` | Debugging errors                |
| `read_network_requests` | Debugging API calls             |
| `javascript_tool`       | DOM inspection                  |
| `gif_creator`           | Recording workflows             |

## URLs

**Default**: `http://localhost:3017` (feature-1 worktree)

| Port | Worktree  |
| ---- | --------- |
| 3007 | main      |
| 3017 | feature-1 |
| 3027 | feature-2 |

## Key Routes

| Path                | View                |
| ------------------- | ------------------- |
| `/`                 | Board (Kanban)      |
| `/settings`         | Global settings     |
| `/project-settings` | Project settings    |
| `/agent`            | Agent chat          |
| `/terminal`         | Terminal            |
| `/agents`           | Custom agents       |
| `/systems`          | Multi-agent systems |
| `/knowledge-hub`    | Knowledge hub       |

## Shortcuts (when no input focused)

`K` Board | `A` Agent | `T` Terminal | `S` Settings | `Shift+S` Project Settings
`Shift+A` Agents | `Shift+Y` Systems | `Shift+K` Knowledge Hub
`N` Add feature | `G` Start next | `O` Open project

## Workflow Patterns

**Click element**: `read_page` (filter: "interactive") → get ref → `computer` (action: "left_click", ref: "ref_X")

**Type in input**: `form_input` (ref: "ref_X", value: "text")

**Debug**: `read_console_messages` (pattern: "error")

**Screenshot**: `computer` (action: "screenshot")

## Error Recovery

- **Extension not connected**: User must open Chrome with Claude extension
- **Element not found**: Screenshot → check page state → try different selector
- **Action fails**: Wait → scroll element into view → retry once

## Instructions

Execute the user's task efficiently:

1. Load only required tools via ToolSearch
2. Initialize browser session
3. Navigate to correct URL
4. Complete task with minimal steps
5. Report results concisely

$ARGUMENTS
