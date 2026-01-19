-- Automaker Launcher
-- Save this as an Application using Script Editor for a desktop icon

set automakerPath to "/Users/ruben/Documents/GitHub/automaker"

tell application "Terminal"
    activate
    do script "cd " & quoted form of automakerPath & " && npm run dev:web"
end tell

display notification "Automaker is starting..." with title "Automaker" subtitle "UI at http://localhost:3007"
