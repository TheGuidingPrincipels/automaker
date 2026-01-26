-- Automaker Launcher (Web Mode)
-- Save this as an Application using Script Editor for a desktop icon
-- Uses ports 3017/3018 to avoid conflicts with Docker (which uses 3007/3008)

set automakerPath to "/Users/ruben/Documents/GitHub/automaker"
set webURL to "http://localhost:3017"

-- Start both frontend and backend in Terminal
-- PORT = backend server, TEST_PORT = Vite frontend, TEST_SERVER_PORT = proxy target
tell application "Terminal"
	activate
	do script "cd " & quoted form of automakerPath & " && PORT=3018 TEST_PORT=3017 TEST_SERVER_PORT=3018 npm run dev:full"
end tell

display notification "Automaker is starting..." with title "Automaker" subtitle "Opening Chrome when ready..."

-- Wait for server to be ready (check every 2 seconds, max 60 seconds)
set maxAttempts to 30
set attempt to 0
set serverReady to false

repeat while attempt < maxAttempts and not serverReady
	delay 2
	try
		do shell script "curl -s " & webURL & " > /dev/null 2>&1"
		set serverReady to true
	end try
	set attempt to attempt + 1
end repeat

-- Open Chrome using shell command (avoids race condition that can create two windows)
do shell script "open -a 'Google Chrome' " & quoted form of webURL

-- Wait briefly for Chrome to open, then maximize window
delay 1.5
tell application "Google Chrome"
	activate
	if (count of windows) > 0 then
		-- Get screen bounds and maximize window (leaving space for menu bar)
		tell application "Finder"
			set screenBounds to bounds of window of desktop
		end tell
		set bounds of front window to {0, 25, item 3 of screenBounds, item 4 of screenBounds}
	end if
end tell

display notification "Automaker is ready!" with title "Automaker" subtitle webURL
