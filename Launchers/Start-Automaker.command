#!/bin/bash
# Automaker Quick Launcher - Double-click to start
# This script launches Automaker in Electron mode
# Uses ports 3017/3018 to avoid conflicts with Docker (which uses 3007/3008)

cd "$(dirname "$0")/.."

# Check if it's the first run or if node_modules is missing
if [ ! -d "node_modules" ]; then
    echo "First run detected. Installing dependencies..."
    npm install
fi

# Port configuration to avoid Docker conflicts
export PORT=3018
export TEST_PORT=3017

# Launch automaker in electron mode
echo "Starting Automaker..."
echo ""
echo "UI will be available at: http://localhost:3017"
echo "Server running at: http://localhost:3018"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

npm run dev:electron
