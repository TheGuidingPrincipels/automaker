#!/bin/bash
# Automaker Quick Launcher - Double-click to start
# This script launches Automaker in web mode and opens Chrome
# Uses ports 3017/3018 to avoid conflicts with Docker (which uses 3007/3008)

cd "$(dirname "$0")/.."

# Check if it's the first run or if node_modules is missing
if [ ! -d "node_modules" ]; then
    echo "First run detected. Installing dependencies..."
    npm install
fi

# Port configuration to avoid Docker conflicts
# PORT = backend server port
# TEST_PORT = Vite frontend port
# TEST_SERVER_PORT = tells Vite where to proxy API calls
export PORT=3018
export TEST_PORT=3017
export TEST_SERVER_PORT=3018

# Function to check if server is ready
wait_for_server() {
    echo "Waiting for server to start..."
    local max_attempts=60
    local attempt=0
    while [ $attempt -lt $max_attempts ]; do
        if curl -s "http://localhost:3017" > /dev/null 2>&1; then
            return 0
        fi
        sleep 1
        attempt=$((attempt + 1))
    done
    return 1
}

# Launch automaker (both frontend and backend)
echo "Starting Automaker Web Mode..."
echo ""
echo "UI will be available at: http://localhost:3017"
echo "Server running at: http://localhost:3018"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start both frontend and backend
npm run dev:full &
SERVER_PID=$!

# Wait for server to be ready, then open Chrome
if wait_for_server; then
    echo "Server ready! Opening Chrome..."
    open -a "Google Chrome" "http://localhost:3017"
else
    echo "Warning: Server may still be starting. Opening Chrome anyway..."
    open -a "Google Chrome" "http://localhost:3017"
fi

# Wait for the server process (keeps terminal open)
wait $SERVER_PID
