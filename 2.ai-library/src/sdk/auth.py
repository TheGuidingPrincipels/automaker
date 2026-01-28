# src/sdk/auth.py
"""OAuth token loading with fallback to automaker credentials."""

import json
import logging
import os
from pathlib import Path
from typing import Optional, List

logger = logging.getLogger(__name__)


def _get_credentials_paths() -> List[Path]:
    """
    Get ordered list of credential paths to check.

    Priority:
    1. DATA_DIR/credentials.json (automaker's actual storage location)
    2. AUTOMAKER_DATA_DIR/credentials.json (explicit override)
    3. ~/.automaker/credentials.json (legacy fallback)
    """
    paths = []

    # Priority 1: DATA_DIR (where automaker actually stores credentials)
    data_dir = os.getenv("DATA_DIR")
    if data_dir:
        paths.append(Path(data_dir) / "credentials.json")

    # Priority 2: AUTOMAKER_DATA_DIR (explicit override for ai-library)
    automaker_data_dir = os.getenv("AUTOMAKER_DATA_DIR")
    if automaker_data_dir:
        paths.append(Path(automaker_data_dir) / "credentials.json")

    # Priority 3: Default ./data/credentials.json (common case)
    paths.append(Path("./data/credentials.json"))

    # Priority 4: Legacy ~/.automaker/credentials.json
    paths.append(Path.home() / ".automaker" / "credentials.json")

    return paths


def _try_load_token_from_file(creds_path: Path) -> Optional[str]:
    """Try to load OAuth token from a credentials file."""
    if not creds_path.exists():
        return None

    try:
        with open(creds_path) as f:
            creds = json.load(f)

        # Try the direct key first
        token = creds.get("anthropic_oauth_token")
        if token:
            logger.debug("Found OAuth token in %s (anthropic_oauth_token)", creds_path)
            return token

        # Try nested under apiKeys (automaker's structure)
        api_keys = creds.get("apiKeys", {})
        token = api_keys.get("anthropic_oauth_token")
        if token:
            logger.debug("Found OAuth token in %s (apiKeys.anthropic_oauth_token)", creds_path)
            return token

    except (json.JSONDecodeError, IOError) as e:
        logger.debug("Failed to read %s: %s", creds_path, e)

    return None


def load_oauth_token(credentials_path: Optional[Path] = None) -> Optional[str]:
    """
    Load OAuth token with fallback priority.

    IMPORTANT: When CLAUDE_CODE_OAUTH_TOKEN is set, we do NOT set ANTHROPIC_AUTH_TOKEN.
    This matches Automaker's behavior and allows the Claude CLI to use its internal
    OAuth mechanism, which works properly with Max/Pro subscriptions.

    Setting ANTHROPIC_AUTH_TOKEN explicitly overrides the CLI's internal auth and
    can cause "Credit balance is too low" errors even with valid subscription tokens.

    Priority:
    1. ANTHROPIC_AUTH_TOKEN environment variable (explicit override)
    2. CLAUDE_CODE_OAUTH_TOKEN environment variable (let CLI handle OAuth)
    3. Credentials files (explicit token from file)

    Returns:
        OAuth token string or None if not found
    """
    # Priority 1: ANTHROPIC_AUTH_TOKEN environment variable (explicit override)
    token = os.getenv("ANTHROPIC_AUTH_TOKEN")
    if token:
        logger.debug("Using OAuth token from ANTHROPIC_AUTH_TOKEN env var")
        return token

    # Priority 2: CLAUDE_CODE_OAUTH_TOKEN environment variable
    # DO NOT set ANTHROPIC_AUTH_TOKEN - let the CLI handle OAuth internally
    # This matches Automaker's buildEnv() behavior (claude-provider.ts:199-204)
    token = os.getenv("CLAUDE_CODE_OAUTH_TOKEN")
    if token:
        logger.debug(
            "CLAUDE_CODE_OAUTH_TOKEN is set - CLI will use internal OAuth. "
            "Not setting ANTHROPIC_AUTH_TOKEN to avoid overriding CLI auth."
        )
        # Return a marker that auth is available, but don't modify env
        return "__CLI_HANDLES_OAUTH__"

    # Priority 3: Try credentials files in order
    if credentials_path:
        # Explicit path provided - only try that
        token = _try_load_token_from_file(credentials_path)
        if token:
            os.environ["ANTHROPIC_AUTH_TOKEN"] = token
            logger.debug("Loaded OAuth token from %s", credentials_path)
            return token
    else:
        # Try all known paths
        for creds_path in _get_credentials_paths():
            token = _try_load_token_from_file(creds_path)
            if token:
                # Set env var so SDK can find it
                os.environ["ANTHROPIC_AUTH_TOKEN"] = token
                logger.debug("Loaded OAuth token from %s", creds_path)
                return token

    # Log which paths were checked
    checked_paths = [str(p) for p in _get_credentials_paths()]
    logger.warning(
        "No OAuth token found. Checked: %s. "
        "Set CLAUDE_CODE_OAUTH_TOKEN or ANTHROPIC_AUTH_TOKEN env var, "
        "or ensure credentials.json contains 'anthropic_oauth_token' key.",
        ", ".join(checked_paths)
    )
    return None


def check_oauth_token_available(credentials_path: Optional[Path] = None) -> bool:
    """
    Check if an OAuth token is available without modifying environment.

    Returns:
        True if token is available, False otherwise
    """
    # Check environment variables first
    if os.getenv("ANTHROPIC_AUTH_TOKEN") or os.getenv("CLAUDE_CODE_OAUTH_TOKEN"):
        return True

    # Check credentials files
    if credentials_path:
        return _try_load_token_from_file(credentials_path) is not None

    for creds_path in _get_credentials_paths():
        if _try_load_token_from_file(creds_path):
            return True

    return False
