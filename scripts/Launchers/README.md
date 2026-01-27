# Automaker Launcher

## Quick Start

Double-click **`Launch-Automaker.command`** (or the Desktop shortcut)

## What It Does

1. Kills any existing Automaker/KL processes
2. Starts Knowledge Library on port 8002
3. Waits for KL to be healthy
4. Starts Automaker (server + UI)
5. Opens Chrome to http://localhost:3017

## Ports

| Service           | Port |
| ----------------- | ---- |
| Knowledge Library | 8002 |
| Automaker Server  | 3018 |
| Automaker UI      | 3017 |

## Stopping

Press `Ctrl+C` in the Terminal window to stop all services.

## Files

| File                       | Purpose                             |
| -------------------------- | ----------------------------------- |
| `Launch-Automaker.command` | Main launcher (double-click to run) |
| `README.md`                | This file                           |

A Desktop shortcut (symlink) is available for easy access.
