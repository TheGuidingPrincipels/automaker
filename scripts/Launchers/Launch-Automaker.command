#!/bin/bash
# Launch Automaker with Knowledge Library
# Double-click this file to start everything

cd "$(dirname "$0")/../.."
REPO_ROOT="$(pwd)"

echo "============================================"
echo "  Automaker Launcher"
echo "============================================"
echo ""

# Kill any existing processes
echo "Cleaning up old processes..."
pkill -f "run_api.py" 2>/dev/null
pkill -f "node.*vite" 2>/dev/null
pkill -f "tsx watch" 2>/dev/null
sleep 2

# Start Knowledge Library in background
echo ""
echo "Starting Knowledge Library..."
cd "$REPO_ROOT/2.ai-library"
CORS_ORIGINS="http://localhost:3017,http://localhost:3018,http://127.0.0.1:3017,http://127.0.0.1:3018" \
  ./start-with-automaker.sh &
KL_PID=$!

# Wait for KL to be ready
echo "Waiting for Knowledge Library to be ready..."
for i in {1..30}; do
    if curl -s --max-time 2 http://localhost:8002/health | grep -q healthy; then
        echo "Knowledge Library is ready!"
        break
    fi
    sleep 2
    echo "  Still waiting... ($i)"
done

# Check if KL started
if ! curl -s --max-time 2 http://localhost:8002/health | grep -q healthy; then
    echo ""
    echo "ERROR: Knowledge Library failed to start!"
    echo "Check the output above for errors."
    echo ""
    read -p "Press Enter to exit..."
    exit 1
fi

# Start Automaker
echo ""
echo "Starting Automaker..."
cd "$REPO_ROOT"
VITE_KNOWLEDGE_LIBRARY_API=http://localhost:8002 \
  PORT=3018 \
  TEST_PORT=3017 \
  TEST_SERVER_PORT=3018 \
  npm run dev:full &
AUTOMAKER_PID=$!

# Wait for Automaker to be ready
echo "Waiting for Automaker to be ready..."
for i in {1..30}; do
    if curl -s --max-time 2 http://localhost:3018/api/health | grep -q ok; then
        echo "Automaker server is ready!"
        break
    fi
    sleep 2
    echo "  Still waiting... ($i)"
done

# Wait for Vite
sleep 5

# Open Chrome (only one window/tab)
echo ""
echo "Opening Chrome..."
if pgrep -x "Google Chrome" > /dev/null; then
    # Chrome is running - create tab explicitly in front window to avoid Workona interference
    osascript <<'EOF'
tell application "Google Chrome"
    activate
    if (count of windows) > 0 then
        tell front window
            make new tab with properties {URL:"http://localhost:3017"}
        end tell
    else
        make new window
        set URL of active tab of front window to "http://localhost:3017"
    end if
end tell
EOF
else
    # Chrome not running - open fresh
    open -a "Google Chrome" "http://localhost:3017"
fi

echo ""
echo "============================================"
echo "  Automaker is running!"
echo "============================================"
echo ""
echo "  UI: http://localhost:3017"
echo "  Server: http://localhost:3018"
echo "  Knowledge Library: http://localhost:8002"
echo ""
echo "Press Ctrl+C to stop all services."
echo ""

# Wait for user to stop
wait
