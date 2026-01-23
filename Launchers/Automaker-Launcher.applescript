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

-- Open Chrome
tell application "Google Chrome"
	activate
	if (count of windows) = 0 then
		make new window
	end if
	set URL of active tab of front window to webURL
end tell

display notification "Automaker is ready!" with title "Automaker" subtitle webURL
