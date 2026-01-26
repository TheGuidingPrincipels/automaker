# Backup and Restore Guide

## Table of Contents

1. [Overview](#overview)
2. [Backup Strategy](#backup-strategy)
3. [Manual Backup Procedures](#manual-backup-procedures)
4. [Automated Backup Setup](#automated-backup-setup)
5. [Backup Verification](#backup-verification)
6. [Restore Procedures](#restore-procedures)
7. [Disaster Recovery Scenarios](#disaster-recovery-scenarios)
8. [Retention Policies](#retention-policies)
9. [Off-Site Backup Recommendations](#off-site-backup-recommendations)
10. [Monitoring and Alerts](#monitoring-and-alerts)
11. [Troubleshooting](#troubleshooting)

---

## Overview

The MCP Knowledge Server uses three distinct database systems, each requiring specific backup and restore procedures:

- **Neo4j**: Graph database for entity relationships (Docker or native)
- **SQLite**: Event store for event sourcing (file-based)
- **ChromaDB**: Vector database for embeddings (directory-based)

All backup scripts include:

- Transactional consistency
- Automatic compression
- Integrity verification
- Metadata tracking
- Retention policy enforcement

**Location**: All backup scripts are in `/backup/` directory.

**Default Backup Path**: `./backups/` (configurable)

---

## Backup Strategy

### Strategy Overview

The backup system implements a **3-2-1 backup strategy**:

- **3** copies of data (production + 2 backups)
- **2** different storage media (local disk + off-site)
- **1** copy off-site (cloud storage recommended)

### Backup Types

1. **Full Backup**: Complete snapshot of all databases
2. **Component Backup**: Individual database backup
3. **Unified Backup**: Coordinated backup across all databases

### Consistency Model

- **SQLite**: Transaction-safe using `.backup` command
- **Neo4j**: Consistent dump using `neo4j-admin database dump`
- **ChromaDB**: Directory snapshot (stop writes during backup for consistency)

### Retention Schedule

| Backup Type | Retention Period | When           |
| ----------- | ---------------- | -------------- |
| Daily       | 7 days           | Every day      |
| Weekly      | 4 weeks          | Sunday backups |
| Monthly     | 3 months         | 1st of month   |

---

## Manual Backup Procedures

### 1. Neo4j Database Backup

**Script**: `backup/backup_neo4j.sh`

#### Usage

```bash
# Default backup location
./backup/backup_neo4j.sh

# Custom backup location
./backup/backup_neo4j.sh /path/to/backup/dir
```

#### What It Does

1. Detects Neo4j installation type (Docker or native)
2. Creates transaction-consistent dump
3. Compresses the dump file
4. Verifies backup integrity
5. Creates metadata file
6. Applies retention policy
7. Logs all operations

#### Docker-Based Backup

For Neo4j running in Docker:

```bash
# The script automatically:
# 1. Detects container name
# 2. Creates dump inside container: neo4j-admin database dump
# 3. Copies dump to host system
# 4. Cleans up container temporary files
```

#### Native Backup

For native Neo4j installation:

```bash
# Requires neo4j-admin in PATH
# Creates dump directly on host system
neo4j-admin database dump neo4j --to-path=/backup/path
```

#### Output Structure

```
backups/neo4j/
└── 20251007_153045/
    ├── neo4j.dump.gz          # Compressed database dump
    └── metadata.txt           # Backup metadata
```

#### Metadata File

```
Backup Timestamp: 20251007_153045
Date: Mon Oct  7 15:30:45 PDT 2025
Hostname: production-server
Neo4j Type: docker
Backup Size: 256M
Compressed Size: 89M
```

---

### 2. SQLite Event Store Backup

**Script**: `backup/backup_sqlite.sh`

#### Usage

```bash
# Default paths
./backup/backup_sqlite.sh

# Custom backup location and database path
./backup/backup_sqlite.sh /path/to/backup/dir /path/to/events.db
```

#### What It Does

1. Verifies source database exists
2. Uses SQLite's `.backup` command (transaction-safe)
3. Verifies backup integrity with `PRAGMA integrity_check`
4. Collects database statistics
5. Compresses backup
6. Creates metadata and quick restore script
7. Applies retention policy

#### Transaction Safety

The backup uses SQLite's `.backup` command, which:

- Locks database tables during backup
- Ensures transactional consistency
- Allows concurrent reads during backup
- Handles WAL (Write-Ahead Logging) mode correctly

#### Output Structure

```
backups/sqlite/
└── 20251007_153045/
    ├── events.db.gz           # Compressed database backup
    ├── metadata.txt           # Backup metadata
    └── restore.sh             # Quick restore script
```

#### Metadata File

```
Backup Timestamp: 20251007_153045
Date: Mon Oct  7 15:30:45 PDT 2025
Hostname: production-server
Database Path: /project/data/events.db
Original Size: 45M
Compressed Size: 12M
Events Count: 125430
Outbox Count: 23
Integrity Check: OK
```

#### Quick Restore Script

Each backup includes a standalone restore script:

```bash
cd backups/sqlite/20251007_153045
./restore.sh
# Prompts for target path and handles restore
```

---

### 3. ChromaDB Vector Database Backup

**Script**: `backup/backup_chromadb.sh`

#### Usage

```bash
# Default paths
./backup/backup_chromadb.sh

# Custom backup and ChromaDB directory
./backup/backup_chromadb.sh /path/to/backup/dir /path/to/chroma
```

#### What It Does

1. Verifies ChromaDB directory exists
2. Counts collections (if chroma.sqlite3 exists)
3. Creates tar archive of entire directory
4. Verifies archive integrity
5. Compresses archive
6. Creates metadata and restore script
7. Applies retention policy

#### Important Notes

- **Stop writes during backup** for consistency (recommended)
- Preserves file permissions and timestamps
- Backs up all ChromaDB files (SQLite metadata, vectors, indices)

#### Output Structure

```
backups/chromadb/
└── 20251007_153045/
    ├── chromadb.tar.gz        # Compressed directory archive
    ├── metadata.txt           # Backup metadata
    └── restore.sh             # Quick restore script
```

#### Metadata File

```
Backup Timestamp: 20251007_153045
Date: Mon Oct  7 15:30:45 PDT 2025
Hostname: production-server
ChromaDB Directory: /project/data/chroma
Original Size: 1.2G
Archive Size: 1.2G
Compressed Size: 445M
Collections Count: 3
Integrity Check: OK
```

---

### 4. Unified Backup (All Databases)

**Script**: `backup/backup_all.sh`

#### Usage

```bash
# Default backup location
./backup/backup_all.sh

# Custom backup root
./backup/backup_all.sh /path/to/backup/root
```

#### What It Does

1. Orchestrates backups of all three databases
2. Creates unified backup manifest
3. Tracks timing and status for each component
4. Creates symbolic links for easy access
5. Sends notifications (if configured)
6. Provides comprehensive summary

#### Notification Support

Set environment variables for notifications:

```bash
# Email notifications (requires 'mail' command)
export BACKUP_EMAIL="admin@example.com"

# Webhook notifications (requires 'curl')
export BACKUP_WEBHOOK="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"

./backup/backup_all.sh
```

#### Output Structure

```
backups/
├── neo4j/
│   └── 20251007_153045/
│       ├── neo4j.dump.gz
│       └── metadata.txt
├── sqlite/
│   └── 20251007_153045/
│       ├── events.db.gz
│       ├── metadata.txt
│       └── restore.sh
├── chromadb/
│   └── 20251007_153045/
│       ├── chromadb.tar.gz
│       ├── metadata.txt
│       └── restore.sh
├── unified/
│   └── 20251007_153045/
│       ├── manifest.json      # Unified manifest
│       ├── neo4j -> ../../neo4j/20251007_153045     # Symbolic link
│       ├── sqlite -> ../../sqlite/20251007_153045   # Symbolic link
│       └── chromadb -> ../../chromadb/20251007_153045 # Symbolic link
└── backup_all.log             # Unified log file
```

#### Manifest File (manifest.json)

```json
{
  "backup_timestamp": "20251007_153045",
  "backup_date": "Mon Oct  7 15:30:45 PDT 2025",
  "hostname": "production-server",
  "duration_seconds": 142,
  "status": "success",
  "components": {
    "neo4j": {
      "backup_path": "/backups/neo4j/20251007_153045",
      "size": "89M",
      "file": "neo4j.dump.gz"
    },
    "sqlite": {
      "backup_path": "/backups/sqlite/20251007_153045",
      "size": "12M",
      "file": "events.db.gz"
    },
    "chromadb": {
      "backup_path": "/backups/chromadb/20251007_153045",
      "size": "445M",
      "file": "chromadb.tar.gz"
    }
  },
  "restore_command": "bash /backups/unified/20251007_153045/restore_all.sh"
}
```

---

## Automated Backup Setup

### Setting Up Cron Jobs

#### 1. Daily Backup (2 AM)

```bash
# Edit crontab
crontab -e

# Add daily backup at 2 AM
0 2 * * * /path/to/mcp-knowledge-server/backup/backup_all.sh >> /var/log/mcp-backup.log 2>&1
```

#### 2. Weekly Backup (Sunday 3 AM)

```bash
# Sunday at 3 AM (retention policy keeps this as weekly backup)
0 3 * * 0 /path/to/mcp-knowledge-server/backup/backup_all.sh >> /var/log/mcp-backup-weekly.log 2>&1
```

#### 3. Monthly Backup (1st of month, 4 AM)

```bash
# First day of month at 4 AM
0 4 1 * * /path/to/mcp-knowledge-server/backup/backup_all.sh >> /var/log/mcp-backup-monthly.log 2>&1
```

### Complete Cron Configuration Example

```bash
# MCP Knowledge Server Backups
# Email notifications
BACKUP_EMAIL=admin@example.com
# Webhook for Slack/Discord
BACKUP_WEBHOOK=https://hooks.slack.com/services/YOUR/WEBHOOK/URL

# Daily backup at 2 AM
0 2 * * * /home/user/mcp-knowledge-server/backup/backup_all.sh /mnt/backups >> /var/log/mcp-backup.log 2>&1

# Weekly verification on Sundays at 5 AM
0 5 * * 0 /home/user/mcp-knowledge-server/backup/verify_backups.sh >> /var/log/mcp-backup-verify.log 2>&1
```

### Systemd Timer Alternative

For systems using systemd, create a timer unit:

#### /etc/systemd/system/mcp-backup.service

```ini
[Unit]
Description=MCP Knowledge Server Backup
After=network.target

[Service]
Type=oneshot
User=mcp
Environment="BACKUP_EMAIL=admin@example.com"
ExecStart=/opt/mcp-knowledge-server/backup/backup_all.sh /mnt/backups
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

#### /etc/systemd/system/mcp-backup.timer

```ini
[Unit]
Description=MCP Knowledge Server Backup Timer
Requires=mcp-backup.service

[Timer]
OnCalendar=daily
OnCalendar=02:00
Persistent=true

[Install]
WantedBy=timers.target
```

#### Enable the timer

```bash
sudo systemctl enable mcp-backup.timer
sudo systemctl start mcp-backup.timer

# Check status
sudo systemctl status mcp-backup.timer
sudo systemctl list-timers
```

---

## Backup Verification

### Automated Verification

All backup scripts include automatic verification:

- **Neo4j**: Verifies dump file exists and is readable
- **SQLite**: Runs `PRAGMA integrity_check`
- **ChromaDB**: Tests tar archive integrity

### Manual Verification

#### 1. Verify Neo4j Backup

```bash
# Check if dump is valid
gzip -t backups/neo4j/20251007_153045/neo4j.dump.gz
echo $?  # Should output 0 for success

# List contents (if needed)
gunzip -c backups/neo4j/20251007_153045/neo4j.dump.gz | head -n 100
```

#### 2. Verify SQLite Backup

```bash
# Integrity check without restoring
gunzip -c backups/sqlite/20251007_153045/events.db.gz > /tmp/test.db
sqlite3 /tmp/test.db "PRAGMA integrity_check;"
# Output: ok

# Check row counts
sqlite3 /tmp/test.db "SELECT COUNT(*) FROM events;"
sqlite3 /tmp/test.db "SELECT COUNT(*) FROM outbox;"

# Cleanup
rm /tmp/test.db
```

#### 3. Verify ChromaDB Backup

```bash
# Test archive integrity
gzip -t backups/chromadb/20251007_153045/chromadb.tar.gz
echo $?  # Should output 0

# List archive contents
tar -tzf backups/chromadb/20251007_153045/chromadb.tar.gz | head -n 20
```

#### 4. Test Restore (Non-Production)

Create a test restore environment:

```bash
# Create test directory
mkdir -p /tmp/restore-test

# Test SQLite restore
cd backups/sqlite/20251007_153045
./restore.sh
# Enter path: /tmp/restore-test/events.db

# Verify restored database
sqlite3 /tmp/restore-test/events.db "SELECT COUNT(*) FROM events;"
```

### Backup Health Check Script

Create a verification script:

```bash
#!/bin/bash
# verify_backups.sh

BACKUP_DIR="/path/to/backups"
LATEST_BACKUP=$(ls -1d $BACKUP_DIR/unified/*/ | tail -n 1)

echo "Verifying latest backup: $LATEST_BACKUP"

# Check manifest
if [ -f "$LATEST_BACKUP/manifest.json" ]; then
    echo "✓ Manifest exists"
    STATUS=$(jq -r '.status' "$LATEST_BACKUP/manifest.json")
    if [ "$STATUS" = "success" ]; then
        echo "✓ Backup status: success"
    else
        echo "✗ Backup status: $STATUS"
        exit 1
    fi
else
    echo "✗ Manifest missing"
    exit 1
fi

# Verify each component
for component in neo4j sqlite chromadb; do
    COMP_DIR="$LATEST_BACKUP/$component"
    if [ -L "$COMP_DIR" ]; then
        TARGET=$(readlink "$COMP_DIR")
        echo "✓ $component link exists -> $TARGET"

        # Verify metadata
        if [ -f "$TARGET/metadata.txt" ]; then
            echo "  ✓ Metadata exists"
        else
            echo "  ✗ Metadata missing"
            exit 1
        fi
    else
        echo "✗ $component link missing"
        exit 1
    fi
done

echo "✓ All verifications passed"
```

---

## Restore Procedures

### Before You Restore

1. **STOP THE MCP SERVER** - Critical to prevent data corruption
2. **Backup current data** - Safety measure in case restore fails
3. **Verify backup integrity** - Ensure backup files are valid
4. **Plan downtime** - Inform users of service interruption
5. **Test in non-production first** - If possible

### Unified Restore (All Databases)

**Script**: `backup/restore_all.sh`

#### Usage

```bash
# List available backups
./backup/restore_all.sh

# Restore specific backup
./backup/restore_all.sh 20251007_153045
```

#### Interactive Process

The script will:

1. Verify all backup files exist
2. Prompt for confirmation
3. Check if MCP server is running
4. Create safety backup of current data
5. Restore each database sequentially
6. Verify restored data
7. Provide rollback option if needed

#### Example Session

```bash
$ ./backup/restore_all.sh 20251007_153045

========================================================
  MCP Knowledge Server - Unified Restore
========================================================

⚠️  WARNING: This will overwrite all existing data!

Backup Timestamp: 20251007_153045
Neo4j Backup: /backups/neo4j/20251007_153045
SQLite Backup: /backups/sqlite/20251007_153045
ChromaDB Backup: /backups/chromadb/20251007_153045

Verifying backups...
✅ All backups found

Are you sure you want to restore from backup 20251007_153045? (yes/no): yes

🛑 Checking if MCP server is running...
✅ Server not running

💾 Creating safety backup of current data...
   Location: /backups/pre_restore_20251007_154530
✅ Safety backup created

========================================
  Step 1/3: Restoring SQLite Event Store
========================================
Target: /project/data/events.db

✅ SQLite restored and verified

========================================
  Step 2/3: Restoring ChromaDB Vector Database
========================================
Target: /project/data/chroma

✅ ChromaDB restored

========================================
  Step 3/3: Restoring Neo4j Graph Database
========================================
Detected Neo4j container: neo4j
⚠️  Neo4j restore requires stopping the container
Stop Neo4j container to restore? (yes/no): yes

✅ Neo4j restored

========================================
  Restore Summary
========================================

✅ RESTORE COMPLETED SUCCESSFULLY!

Next steps:
  1. Verify data integrity
  2. Start MCP server
  3. Run health checks

Safety backup location: /backups/pre_restore_20251007_154530
```

### Component-Specific Restore

#### 1. SQLite Restore Only

```bash
cd backups/sqlite/20251007_153045
./restore.sh

# Or manually:
gunzip -c events.db.gz > /path/to/data/events.db

# Verify
sqlite3 /path/to/data/events.db "PRAGMA integrity_check;"
```

#### 2. ChromaDB Restore Only

```bash
cd backups/chromadb/20251007_153045
./restore.sh

# Or manually:
rm -rf /path/to/data/chroma
gunzip -c chromadb.tar.gz | tar -xf - -C /path/to/data/

# Verify
ls -la /path/to/data/chroma
```

#### 3. Neo4j Restore Only

**Docker-based restore:**

```bash
# Stop container
docker stop neo4j

# Get backup file
BACKUP_FILE="backups/neo4j/20251007_153045/neo4j.dump.gz"

# Decompress
gunzip -c "$BACKUP_FILE" > /tmp/neo4j.dump

# Copy to container
docker cp /tmp/neo4j.dump neo4j:/tmp/neo4j.dump

# Start container
docker start neo4j
sleep 5

# Load database
docker exec neo4j neo4j-admin database load neo4j \
    --from-path=/tmp \
    --overwrite-destination=true

# Restart
docker restart neo4j

# Cleanup
rm /tmp/neo4j.dump
```

**Native restore:**

```bash
# Stop Neo4j
neo4j stop

# Decompress backup
gunzip -c backups/neo4j/20251007_153045/neo4j.dump.gz > /tmp/neo4j.dump

# Load database
neo4j-admin database load neo4j \
    --from-path=/tmp \
    --overwrite-destination=true

# Start Neo4j
neo4j start

# Cleanup
rm /tmp/neo4j.dump
```

---

## Disaster Recovery Scenarios

### Scenario 1: Complete Data Loss

**Situation**: Server crashed, all data lost.

**Recovery Steps**:

1. Rebuild server infrastructure
2. Install dependencies (Neo4j, SQLite, Python, etc.)
3. Clone MCP Knowledge Server repository
4. Retrieve latest backup from off-site storage
5. Run unified restore:
   ```bash
   ./backup/restore_all.sh <timestamp>
   ```
6. Verify data integrity
7. Start MCP server
8. Run integration tests
9. Resume operations

**Estimated Recovery Time**: 1-4 hours (depending on data size and infrastructure)

### Scenario 2: Corrupted SQLite Database

**Situation**: SQLite database corrupted, other databases intact.

**Recovery Steps**:

1. Stop MCP server
2. Backup corrupted database (for analysis):
   ```bash
   cp data/events.db data/events.db.corrupted
   ```
3. Restore from latest backup:
   ```bash
   cd backups/sqlite/<timestamp>
   ./restore.sh
   ```
4. Verify integrity:
   ```bash
   sqlite3 data/events.db "PRAGMA integrity_check;"
   ```
5. Restart MCP server
6. Monitor for issues

**Estimated Recovery Time**: 15-30 minutes

### Scenario 3: Neo4j Connection Lost

**Situation**: Neo4j container/service crashed or corrupted.

**Recovery Steps**:

1. Stop MCP server
2. Check Neo4j status:
   ```bash
   docker ps -a | grep neo4j
   # or
   systemctl status neo4j
   ```
3. Attempt restart:
   ```bash
   docker restart neo4j
   # or
   systemctl restart neo4j
   ```
4. If restart fails, restore from backup:
   ```bash
   docker stop neo4j
   # Follow Neo4j restore procedure above
   ```
5. Verify Neo4j is healthy:
   ```bash
   docker logs neo4j
   # Check for errors
   ```
6. Restart MCP server

**Estimated Recovery Time**: 30 minutes - 1 hour

### Scenario 4: Accidental Data Deletion

**Situation**: Important data accidentally deleted, discovered within hours.

**Recovery Steps**:

1. **Immediate action**: Stop all writes
   ```bash
   # Stop MCP server immediately
   pkill -f mcp_server.py
   ```
2. Identify last known good backup:
   ```bash
   ls -lt backups/unified/
   ```
3. Create safety snapshot of current state:
   ```bash
   ./backup/backup_all.sh /backups/emergency_snapshot
   ```
4. Restore from backup before deletion:
   ```bash
   ./backup/restore_all.sh <timestamp_before_deletion>
   ```
5. Verify restored data
6. Resume operations

**Estimated Recovery Time**: 30 minutes - 2 hours

### Scenario 5: Partial Component Failure

**Situation**: ChromaDB vectors corrupted, but graph and events intact.

**Recovery Steps**:

1. Stop MCP server
2. Backup current ChromaDB (even if corrupted):
   ```bash
   mv data/chroma data/chroma.corrupted
   ```
3. Restore ChromaDB only:
   ```bash
   cd backups/chromadb/<timestamp>
   ./restore.sh
   ```
4. Verify ChromaDB:
   ```bash
   ls -la data/chroma
   # Check collection count
   sqlite3 data/chroma/chroma.sqlite3 "SELECT COUNT(*) FROM collections;"
   ```
5. Restart MCP server
6. Run vector search tests

**Estimated Recovery Time**: 20-45 minutes

---

## Retention Policies

### Current Retention Policy

Implemented in all backup scripts:

| Type    | Retention | Selection Criteria                      |
| ------- | --------- | --------------------------------------- |
| Daily   | 7 days    | All backups from last 7 days            |
| Weekly  | 4 weeks   | Sunday backups from last 4 weeks        |
| Monthly | 3 months  | 1st of month backups from last 3 months |

### How Retention Works

The retention policy automatically runs after each backup:

1. Scans backup directory for timestamped folders
2. Identifies daily backups (all backups < 7 days old)
3. Identifies weekly backups (Sunday backups < 4 weeks old)
4. Identifies monthly backups (1st of month < 3 months old)
5. Deletes all backups not matching retention criteria

### Customizing Retention

Edit the backup scripts to change retention:

```bash
# In backup_neo4j.sh, backup_sqlite.sh, backup_chromadb.sh
KEEP_DAILY=14    # Keep last 14 daily backups
KEEP_WEEKLY=8    # Keep last 8 weekly backups
KEEP_MONTHLY=6   # Keep last 6 monthly backups
```

### Long-Term Archival

For compliance or long-term storage:

```bash
#!/bin/bash
# archive_backup.sh - Move old backups to archive storage

ARCHIVE_DIR="/mnt/archive/mcp-backups"
BACKUP_DIR="/path/to/backups/unified"

# Find backups older than 90 days
find "$BACKUP_DIR" -type d -mtime +90 | while read backup; do
    TIMESTAMP=$(basename "$backup")

    # Create archive
    tar -czf "$ARCHIVE_DIR/backup_$TIMESTAMP.tar.gz" "$backup"

    # Verify archive
    if tar -tzf "$ARCHIVE_DIR/backup_$TIMESTAMP.tar.gz" > /dev/null 2>&1; then
        echo "Archived: $TIMESTAMP"
        # Optionally remove from backup directory
        # rm -rf "$backup"
    else
        echo "Archive failed: $TIMESTAMP"
    fi
done
```

### Disk Space Management

Monitor backup disk usage:

```bash
# Check total backup size
du -sh /path/to/backups

# Check size by component
du -sh /path/to/backups/neo4j
du -sh /path/to/backups/sqlite
du -sh /path/to/backups/chromadb

# Find largest backups
du -sh /path/to/backups/*/* | sort -hr | head -n 10
```

Alert when disk usage exceeds threshold:

```bash
#!/bin/bash
# check_backup_disk.sh

BACKUP_DIR="/path/to/backups"
THRESHOLD_PERCENT=80
EMAIL="admin@example.com"

USAGE=$(df "$BACKUP_DIR" | tail -1 | awk '{print $5}' | sed 's/%//')

if [ "$USAGE" -gt "$THRESHOLD_PERCENT" ]; then
    echo "Backup disk usage: ${USAGE}% (threshold: ${THRESHOLD_PERCENT}%)" | \
        mail -s "Backup Disk Alert" "$EMAIL"
fi
```

---

## Off-Site Backup Recommendations

### Why Off-Site Backups?

Protect against:

- Physical disasters (fire, flood, theft)
- Site-wide failures (power, network)
- Ransomware attacks
- Human error affecting entire server

### Recommended Off-Site Solutions

#### 1. Cloud Storage (S3, Azure Blob, Google Cloud Storage)

**AWS S3 Example**:

```bash
#!/bin/bash
# sync_to_s3.sh

BACKUP_DIR="/path/to/backups"
S3_BUCKET="s3://my-mcp-backups"

# Install AWS CLI first: pip install awscli

# Sync backups to S3
aws s3 sync "$BACKUP_DIR/unified/" "$S3_BUCKET/unified/" \
    --storage-class GLACIER_IR \
    --exclude "*" \
    --include "*/manifest.json"

# Sync actual backup files
aws s3 sync "$BACKUP_DIR/neo4j/" "$S3_BUCKET/neo4j/" --storage-class GLACIER_IR
aws s3 sync "$BACKUP_DIR/sqlite/" "$S3_BUCKET/sqlite/" --storage-class GLACIER_IR
aws s3 sync "$BACKUP_DIR/chromadb/" "$S3_BUCKET/chromadb/" --storage-class GLACIER_IR

# List backups in S3
aws s3 ls "$S3_BUCKET/unified/"
```

**Storage Classes**:

- `STANDARD`: Immediate access, higher cost
- `STANDARD_IA`: Infrequent access, lower cost
- `GLACIER_IR`: Instant retrieval, very low cost
- `GLACIER`: Minutes-hours retrieval, lowest cost

**Automated S3 Sync with Cron**:

```bash
# Sync to S3 daily at 3 AM (after backup completes)
0 3 * * * /path/to/sync_to_s3.sh >> /var/log/s3-sync.log 2>&1
```

#### 2. rsync to Remote Server

```bash
#!/bin/bash
# sync_to_remote.sh

BACKUP_DIR="/path/to/backups"
REMOTE_HOST="backup-server.example.com"
REMOTE_USER="backup"
REMOTE_DIR="/mnt/backups/mcp"

# Sync using rsync over SSH
rsync -avz --delete \
    -e "ssh -i /home/user/.ssh/backup_key" \
    "$BACKUP_DIR/" \
    "$REMOTE_USER@$REMOTE_HOST:$REMOTE_DIR/"

# Verify
ssh -i /home/user/.ssh/backup_key "$REMOTE_USER@$REMOTE_HOST" \
    "du -sh $REMOTE_DIR"
```

#### 3. Encrypted Backups with Restic

Restic provides encrypted, deduplicated, incremental backups:

```bash
# Install restic
sudo apt install restic  # or: brew install restic

# Initialize repository (one time)
restic init --repo /mnt/backup-drive/mcp-restic

# Backup
restic backup /path/to/backups \
    --repo /mnt/backup-drive/mcp-restic \
    --tag mcp-daily

# List snapshots
restic snapshots --repo /mnt/backup-drive/mcp-restic

# Restore
restic restore latest \
    --repo /mnt/backup-drive/mcp-restic \
    --target /restore/location
```

**Restic to Cloud**:

```bash
# S3
export RESTIC_REPOSITORY="s3:s3.amazonaws.com/my-bucket/mcp-backups"
export AWS_ACCESS_KEY_ID="..."
export AWS_SECRET_ACCESS_KEY="..."

restic backup /path/to/backups

# Azure
export RESTIC_REPOSITORY="azure:mycontainer:/mcp-backups"
export AZURE_ACCOUNT_NAME="..."
export AZURE_ACCOUNT_KEY="..."

restic backup /path/to/backups
```

### Off-Site Backup Best Practices

1. **Encrypt in transit and at rest**
   - Use SSH/TLS for transfer
   - Use encrypted storage (S3 with KMS, encrypted drives)

2. **Automate transfers**
   - Run after local backup completes
   - Verify transfer success
   - Alert on failures

3. **Test retrievals regularly**
   - Monthly: Download and verify one backup
   - Quarterly: Full restore test in isolated environment

4. **Geographic diversity**
   - Store in different region/availability zone
   - Consider multi-region replication for critical data

5. **Access control**
   - Use dedicated credentials with minimal permissions
   - Rotate credentials regularly
   - Enable MFA where possible

### Sample Complete Backup Pipeline

```bash
#!/bin/bash
# complete_backup_pipeline.sh

set -e

echo "===== MCP Backup Pipeline ====="

# 1. Local backup
echo "Step 1: Creating local backup..."
/path/to/mcp-knowledge-server/backup/backup_all.sh /local/backups

# 2. Verify local backup
echo "Step 2: Verifying local backup..."
LATEST=$(ls -1td /local/backups/unified/*/ | head -1)
if [ ! -f "$LATEST/manifest.json" ]; then
    echo "ERROR: Backup verification failed"
    exit 1
fi

# 3. Sync to remote server
echo "Step 3: Syncing to remote server..."
rsync -avz /local/backups/ backup@remote:/mnt/backups/

# 4. Sync to S3
echo "Step 4: Syncing to S3..."
aws s3 sync /local/backups/unified/ s3://my-bucket/mcp/unified/ \
    --storage-class GLACIER_IR

# 5. Cleanup old local backups (keep only 7 days)
echo "Step 5: Cleaning old local backups..."
find /local/backups/unified -type d -mtime +7 -exec rm -rf {} +

echo "===== Backup Pipeline Complete ====="
```

---

## Monitoring and Alerts

### Monitoring Checklist

- [ ] Backup completion status
- [ ] Backup duration
- [ ] Backup size trends
- [ ] Disk space usage
- [ ] Failed backup attempts
- [ ] Off-site sync status
- [ ] Restore test results

### Logging

All backup scripts log to:

- **Component logs**: `backups/{component}/backup_{component}.log`
- **Unified log**: `backups/backup_all.log`

View recent backup activity:

```bash
# Last 50 lines
tail -n 50 backups/backup_all.log

# Follow live
tail -f backups/backup_all.log

# Search for errors
grep -i error backups/backup_all.log

# Show all backups today
grep "$(date +%Y-%m-%d)" backups/backup_all.log
```

### Health Check Script

```bash
#!/bin/bash
# backup_health_check.sh

BACKUP_DIR="/path/to/backups"
ALERT_EMAIL="admin@example.com"
MAX_AGE_HOURS=25  # Alert if no backup in 25 hours

# Check last backup time
LATEST_BACKUP=$(find "$BACKUP_DIR/unified" -maxdepth 1 -type d | sort | tail -1)
LATEST_TIME=$(stat -f %m "$LATEST_BACKUP" 2>/dev/null || stat -c %Y "$LATEST_BACKUP")
CURRENT_TIME=$(date +%s)
AGE_HOURS=$(( (CURRENT_TIME - LATEST_TIME) / 3600 ))

if [ $AGE_HOURS -gt $MAX_AGE_HOURS ]; then
    echo "ALERT: Last backup is $AGE_HOURS hours old" | \
        mail -s "MCP Backup Alert" "$ALERT_EMAIL"
    exit 1
fi

# Check backup status
MANIFEST="$LATEST_BACKUP/manifest.json"
if [ -f "$MANIFEST" ]; then
    STATUS=$(jq -r '.status' "$MANIFEST")
    if [ "$STATUS" != "success" ]; then
        echo "ALERT: Last backup status: $STATUS" | \
            mail -s "MCP Backup Failed" "$ALERT_EMAIL"
        exit 1
    fi
else
    echo "ALERT: Backup manifest missing" | \
        mail -s "MCP Backup Alert" "$ALERT_EMAIL"
    exit 1
fi

# Check disk space
DISK_USAGE=$(df "$BACKUP_DIR" | tail -1 | awk '{print $5}' | sed 's/%//')
if [ $DISK_USAGE -gt 85 ]; then
    echo "ALERT: Backup disk usage at ${DISK_USAGE}%" | \
        mail -s "MCP Backup Disk Alert" "$ALERT_EMAIL"
fi

echo "Backup health check: OK"
```

### Integration with Monitoring Systems

#### Prometheus Exporter

Create a custom Prometheus exporter:

```python
# backup_exporter.py
from prometheus_client import start_http_server, Gauge, Counter
import json
import time
import os

# Metrics
backup_age_seconds = Gauge('mcp_backup_age_seconds', 'Age of last backup in seconds')
backup_size_bytes = Gauge('mcp_backup_size_bytes', 'Backup size in bytes', ['component'])
backup_duration_seconds = Gauge('mcp_backup_duration_seconds', 'Backup duration')
backup_failures = Counter('mcp_backup_failures_total', 'Total backup failures')

def collect_metrics():
    backup_dir = '/path/to/backups/unified'
    latest = max([d for d in os.listdir(backup_dir) if os.path.isdir(os.path.join(backup_dir, d))])
    manifest_path = os.path.join(backup_dir, latest, 'manifest.json')

    with open(manifest_path) as f:
        manifest = json.load(f)

    # Update metrics
    backup_age_seconds.set(time.time() - os.path.getmtime(manifest_path))
    backup_duration_seconds.set(manifest['duration_seconds'])

    if manifest['status'] != 'success':
        backup_failures.inc()

    for component, data in manifest['components'].items():
        # Parse size (e.g., "89M" -> bytes)
        size_str = data['size']
        # Simplified parsing
        backup_size_bytes.labels(component=component).set(0)

if __name__ == '__main__':
    start_http_server(8000)
    while True:
        collect_metrics()
        time.sleep(60)
```

#### Slack/Discord Notifications

Integrated in `backup_all.sh` via webhook:

```bash
export BACKUP_WEBHOOK="https://hooks.slack.com/services/T00/B00/XXX"
./backup/backup_all.sh
```

Custom notification script:

```bash
#!/bin/bash
# send_slack_notification.sh

WEBHOOK_URL="$1"
MESSAGE="$2"
STATUS="$3"  # success or failure

if [ "$STATUS" = "success" ]; then
    COLOR="good"
    EMOJI=":white_check_mark:"
else
    COLOR="danger"
    EMOJI=":x:"
fi

curl -X POST "$WEBHOOK_URL" \
    -H 'Content-Type: application/json' \
    -d "{
        \"attachments\": [{
            \"color\": \"$COLOR\",
            \"title\": \"$EMOJI MCP Backup $STATUS\",
            \"text\": \"$MESSAGE\",
            \"footer\": \"MCP Knowledge Server\",
            \"ts\": $(date +%s)
        }]
    }"
```

---

## Troubleshooting

### Common Issues and Solutions

#### Issue 1: Neo4j Backup Fails - Container Not Found

**Error**:

```
❌ Error: Neo4j not found (not in Docker and neo4j-admin not in PATH)
```

**Solutions**:

1. Check if Neo4j is running:

   ```bash
   docker ps | grep neo4j
   ```

2. If not running, start it:

   ```bash
   docker start neo4j
   # or
   docker-compose up -d neo4j
   ```

3. If using custom container name:

   ```bash
   # Edit backup_neo4j.sh
   CONTAINER_NAME="my-custom-neo4j-name"
   ```

4. For native installation, ensure `neo4j-admin` is in PATH:
   ```bash
   which neo4j-admin
   # Add to PATH if needed
   export PATH=$PATH:/path/to/neo4j/bin
   ```

#### Issue 2: SQLite Backup - Database Locked

**Error**:

```
Error: database is locked
```

**Solutions**:

1. Check for processes using the database:

   ```bash
   lsof /path/to/data/events.db
   ```

2. Stop MCP server:

   ```bash
   pkill -f mcp_server.py
   ```

3. Wait for write operations to complete:

   ```bash
   # Check if WAL file exists
   ls -la /path/to/data/events.db-wal

   # If exists, trigger checkpoint
   sqlite3 /path/to/data/events.db "PRAGMA wal_checkpoint(TRUNCATE);"
   ```

4. Retry backup:
   ```bash
   ./backup/backup_sqlite.sh
   ```

#### Issue 3: ChromaDB Backup - Permission Denied

**Error**:

```
tar: chroma: Cannot open: Permission denied
```

**Solutions**:

1. Check directory permissions:

   ```bash
   ls -la /path/to/data/chroma
   ```

2. Fix permissions:

   ```bash
   sudo chown -R $(whoami):$(whoami) /path/to/data/chroma
   ```

3. Or run backup with sudo:
   ```bash
   sudo ./backup/backup_chromadb.sh
   ```

#### Issue 4: Backup Directory Full

**Error**:

```
No space left on device
```

**Solutions**:

1. Check disk usage:

   ```bash
   df -h /path/to/backups
   ```

2. Manually remove old backups:

   ```bash
   # Remove backups older than 30 days
   find /path/to/backups -type d -mtime +30 -exec rm -rf {} +
   ```

3. Adjust retention policy:

   ```bash
   # Edit backup scripts
   KEEP_DAILY=3   # Reduce from 7
   KEEP_WEEKLY=2  # Reduce from 4
   ```

4. Move backups to larger disk:
   ```bash
   rsync -avz /path/to/backups/ /mnt/larger-disk/backups/
   ```

#### Issue 5: Restore Fails - Integrity Check

**Error**:

```
❌ Backup integrity check failed
```

**Solutions**:

1. Try previous backup:

   ```bash
   ls -lt backups/unified/
   # Use earlier timestamp
   ./backup/restore_all.sh <earlier_timestamp>
   ```

2. Verify backup file:

   ```bash
   # For gzip files
   gzip -t backup.db.gz

   # For tar files
   tar -tzf backup.tar.gz > /dev/null
   ```

3. Check if file is corrupted:

   ```bash
   file backup.db.gz
   # Should show: "gzip compressed data"
   ```

4. If backup is corrupted, check off-site backups

#### Issue 6: Neo4j Restore - Database Load Fails

**Error**:

```
Failed to load database
```

**Solutions**:

1. Check Neo4j logs:

   ```bash
   docker logs neo4j
   # or
   tail -n 100 /var/log/neo4j/neo4j.log
   ```

2. Ensure database is stopped before load:

   ```bash
   docker exec neo4j cypher-shell -u neo4j -p password "STOP DATABASE neo4j"
   # Wait a few seconds
   docker exec neo4j neo4j-admin database load neo4j --from-path=/tmp
   docker exec neo4j cypher-shell -u neo4j -p password "START DATABASE neo4j"
   ```

3. Check dump file format:

   ```bash
   gunzip -c neo4j.dump.gz | head -c 100
   # Should show Neo4j dump header
   ```

4. Try loading with force:
   ```bash
   docker exec neo4j neo4j-admin database load neo4j \
       --from-path=/tmp \
       --overwrite-destination=true \
       --verbose
   ```

#### Issue 7: Compression Fails

**Error**:

```
⚠️  Compression failed, keeping uncompressed backup
```

**Solutions**:

1. Check if gzip is available:

   ```bash
   which gzip
   ```

2. Check disk space:

   ```bash
   df -h /path/to/backups
   ```

3. Manually compress:

   ```bash
   gzip /path/to/backup/file.db
   ```

4. Use alternative compression:
   ```bash
   # Edit backup script to use bzip2 or xz
   bzip2 "$BACKUP_FILE"  # Better compression, slower
   xz "$BACKUP_FILE"     # Best compression, slowest
   ```

### Debug Mode

Run backups in verbose mode:

```bash
# Enable debug output
bash -x ./backup/backup_neo4j.sh

# Or add to script
set -x  # Add at top of script for verbose output
```

### Getting Help

1. Check logs:

   ```bash
   tail -n 100 backups/backup_all.log
   ```

2. Run verification:

   ```bash
   ./verify_backups.sh
   ```

3. Test individual component:

   ```bash
   # Test just SQLite backup
   ./backup/backup_sqlite.sh /tmp/test-backup
   ```

4. Create issue with:
   - Full error message
   - Relevant log excerpts
   - System information (OS, Docker version, etc.)
   - Backup script version

---

## Quick Reference

### Backup Commands

```bash
# Full system backup
./backup/backup_all.sh

# Individual components
./backup/backup_neo4j.sh
./backup/backup_sqlite.sh
./backup/backup_chromadb.sh

# Custom location
./backup/backup_all.sh /custom/backup/path
```

### Restore Commands

```bash
# List available backups
ls -lt backups/unified/

# Restore everything
./backup/restore_all.sh 20251007_153045

# Restore component
cd backups/sqlite/20251007_153045
./restore.sh
```

### Verification Commands

```bash
# Verify backup integrity
gzip -t backups/neo4j/*/neo4j.dump.gz
gzip -t backups/sqlite/*/events.db.gz
tar -tzf backups/chromadb/*/chromadb.tar.gz > /dev/null

# Check backup status
cat backups/unified/latest/manifest.json

# View logs
tail backups/backup_all.log
```

### Maintenance Commands

```bash
# Check disk usage
du -sh backups/*

# Remove old backups manually
rm -rf backups/*/20241001_*

# Test backup
./verify_backups.sh
```

---

## Conclusion

This backup and restore system provides:

- Comprehensive coverage of all database systems
- Transaction-safe backup procedures
- Automated retention and cleanup
- Verification and integrity checking
- Disaster recovery capabilities
- Off-site backup support
- Monitoring and alerting

### Best Practices Summary

1. Run automated backups daily
2. Test restores monthly
3. Store backups off-site
4. Monitor backup status
5. Document recovery procedures
6. Maintain safety backups before restores
7. Verify backup integrity regularly
8. Keep retention policy balanced with storage

### Next Steps

1. Set up automated cron jobs
2. Configure off-site storage (S3, etc.)
3. Test restore procedure in non-production
4. Set up monitoring and alerts
5. Document custom procedures specific to your environment
6. Train team on restore procedures

---

**Document Version**: 1.0
**Last Updated**: 2025-10-07
**Maintained By**: MCP Knowledge Server Team
