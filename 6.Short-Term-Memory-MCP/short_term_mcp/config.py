"""Configuration for Short-Term Memory MCP Server"""

from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
LOG_DIR = PROJECT_ROOT / "logs"
DB_PATH = DATA_DIR / "short_term_memory.db"

# Database settings
DB_RETENTION_DAYS = 7
ENABLE_WAL = True
AUTO_VACUUM = True

# Performance settings
QUERY_TIMEOUT = 5.0  # seconds
BATCH_SIZE = 25
CACHE_TTL = 300  # 5 minutes

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)
