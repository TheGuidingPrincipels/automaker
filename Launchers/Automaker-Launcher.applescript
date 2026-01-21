-- Automaker Launcher
-- Save this as an Application using Script Editor for a desktop icon
-- Uses ports 3017/3018 to avoid conflicts with Docker (which uses 3007/3008)

set automakerPath to "/Users/ruben/Documents/GitHub/automaker"

tell application "Terminal"
    activate
    do script "cd " & quoted form of automakerPath & " && PORT=3018 TEST_PORT=3017 npm run dev:electron"
end tell

display notification "Automaker is starting..." with title "Automaker" subtitle "UI at http://localhost:3017"
