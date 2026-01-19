#!/bin/bash
# Automaker Quick Launcher - Double-click to start
# This script launches Automaker in web mode

cd "$(dirname "$0")"

# Check if it's the first run or if node_modules is missing
if [ ! -d "node_modules" ]; then
    echo "First run detected. Installing dependencies..."
    npm install
fi

# Launch automaker in web mode (non-interactive)
echo "Starting Automaker..."
echo ""
echo "UI will be available at: http://localhost:3007"
echo "Server running at: http://localhost:3008"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

npm run dev:web
