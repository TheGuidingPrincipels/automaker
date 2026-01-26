# Database Cleanup Script

Quick reference for the database cleanup utility.

## Quick Start

```bash
# Basic usage (with confirmation prompt)
python scripts/cleanup_database.py

# Skip confirmation prompt
python scripts/cleanup_database.py --yes

# Create backup before cleaning
python scripts/cleanup_database.py --backup
```

## Create Shell Alias (Recommended)

```bash
# For bash
echo "alias clean-short-term='python $(pwd)/scripts/cleanup_database.py'" >> ~/.bashrc
source ~/.bashrc

# For zsh
echo "alias clean-short-term='python $(pwd)/scripts/cleanup_database.py'" >> ~/.zshrc
source ~/.zshrc

# Then use:
clean-short-term
clean-short-term --yes
clean-short-term --backup
```

## What Gets Cleaned

**Deleted:**

- All sessions
- All concepts (CASCADE)
- All concept stage data (CASCADE)
- All research cache entries

**Preserved:**

- Domain whitelist configuration
- Database schema and indexes

## Output Example

```
============================================================
  🧹 Short-Term Memory MCP - Database Cleanup
============================================================

============================================================
  Current Database State
============================================================

📊 Current Data:
   Sessions:             3
   Concepts:            12
   Stage Data:          24
   Research Cache:       8
   Domain Whitelist:    12

💾 Size: 104.50 KB
============================================================

⚠️  WARNING: This will DELETE ALL DATA except domain whitelist!
   - 3 sessions
   - 12 concepts
   - 24 stage data entries
   - 8 research cache entries

   Domain whitelist (12 domains) will be PRESERVED.

   Type 'RESET' to confirm deletion: RESET

🧹 Cleaning database...

🔍 Verifying database health...
   ✓ Database is healthy

============================================================
  Cleanup Results
============================================================

🗑️  Deleted:
   Sessions:             3
   Concepts:            12
   Stage Data:          24
   Research Cache:       8

✅ Preserved:
   Domain Whitelist:    12

💾 Storage:
   Before:      104.50 KB
   After:        12.25 KB
   Reclaimed:    92.25 KB
============================================================

✅ Database cleanup complete!

💡 Tip: Create an alias for easy future use:
   alias clean-short-term='python /path/to/scripts/cleanup_database.py'
```

## Full Documentation

For complete documentation including selective cleanup, backups, and troubleshooting, see:

- [TROUBLESHOOTING-GUIDE.md](../TROUBLESHOOTING-GUIDE.md#database-cleanup--reset)
