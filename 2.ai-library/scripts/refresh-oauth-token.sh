#!/bin/bash
# refresh-oauth-token.sh - Get a fresh OAuth token for AI Library
#
# This script:
# 1. Temporarily unsets OAuth env vars (so CLI does fresh login)
# 2. Runs claude login
# 3. Shows the new token location and provides update instructions

set -e

echo "=========================================="
echo "  OAuth Token Refresh for AI Library"
echo "=========================================="
echo ""

# Unset existing OAuth tokens to force fresh login
echo "Step 1: Clearing existing OAuth environment variables..."
unset ANTHROPIC_AUTH_TOKEN
unset CLAUDE_CODE_OAUTH_TOKEN
unset ANTHROPIC_API_KEY
echo "  ✓ Environment variables cleared"
echo ""

# Check for existing auth file
AUTH_FILE="$HOME/.config/claude-code/auth.json"
if [ -f "$AUTH_FILE" ]; then
    echo "Step 2: Found existing auth file at $AUTH_FILE"
    echo "  Backing up to ${AUTH_FILE}.bak"
    cp "$AUTH_FILE" "${AUTH_FILE}.bak"
else
    echo "Step 2: No existing auth file found (this is expected)"
    mkdir -p "$HOME/.config/claude-code"
fi
echo ""

# Run login
echo "Step 3: Starting Claude login flow..."
echo "  → A browser window will open for authentication"
echo "  → Log in with your Claude Pro/Max subscription account"
echo ""
claude login

echo ""
echo "Step 4: Checking for new credentials..."
if [ -f "$AUTH_FILE" ]; then
    echo "  ✓ Auth file created at: $AUTH_FILE"
    echo ""
    echo "  Contents (first 100 chars):"
    head -c 100 "$AUTH_FILE"
    echo "..."
    echo ""

    # Extract token if it's JSON with accessToken
    if command -v jq &> /dev/null; then
        TOKEN=$(jq -r '.accessToken // .oauthAccessToken // .token // empty' "$AUTH_FILE" 2>/dev/null)
        if [ -n "$TOKEN" ]; then
            echo "=========================================="
            echo "  ✓ SUCCESS! New OAuth token obtained"
            echo "=========================================="
            echo ""
            echo "Token preview: ${TOKEN:0:50}..."
            echo ""
            echo "To update your .zshrc, run:"
            echo ""
            echo "  sed -i '' 's/^export CLAUDE_CODE_OAUTH_TOKEN=.*/export CLAUDE_CODE_OAUTH_TOKEN=\"$TOKEN\"/' ~/.zshrc"
            echo ""
            echo "Or manually edit ~/.zshrc and replace the CLAUDE_CODE_OAUTH_TOKEN value."
        else
            echo "Could not extract token from auth file. Check the file manually:"
            echo "  cat $AUTH_FILE"
        fi
    else
        echo "Install 'jq' to auto-extract the token, or check the file manually:"
        echo "  cat $AUTH_FILE"
    fi
else
    echo "  ⚠ Auth file was not created."
    echo "  This might mean the login was cancelled or failed."
    echo ""
    echo "  Try running 'claude login' directly in your terminal."
fi

echo ""
echo "=========================================="
echo "  Next Steps"
echo "=========================================="
echo "1. Update CLAUDE_CODE_OAUTH_TOKEN in ~/.zshrc with the new token"
echo "2. Run: source ~/.zshrc"
echo "3. Restart the AI Library: ./start-with-automaker.sh"
echo ""
