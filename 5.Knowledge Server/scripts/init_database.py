"""
Initialize SQLite Event Store Database
Creates the event store database with event sourcing schema
"""

import sqlite3
from pathlib import Path


def init_event_store():
    """Initialize the event store database with schema"""

    # Ensure data directory exists
    data_dir = Path(__file__).parent.parent / "data"
    data_dir.mkdir(exist_ok=True)

    db_path = data_dir / "events.db"

    print(f"Initializing event store at: {db_path}")

    # Connect to database (creates if doesn't exist)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Create events table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                event_id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                aggregate_id TEXT NOT NULL,
                aggregate_type TEXT NOT NULL,
                event_data TEXT NOT NULL,
                metadata TEXT,
                version INTEGER NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Create indexes on events table
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_aggregate
            ON events(aggregate_id, version)
        """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_created_at
            ON events(created_at)
        """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_event_type
            ON events(event_type)
        """
        )

        # Create UNIQUE constraint on (aggregate_id, version) to prevent race conditions
        cursor.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_aggregate_version
            ON events(aggregate_id, version)
        """
        )

        # Create outbox table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS outbox (
                outbox_id TEXT PRIMARY KEY,
                event_id TEXT NOT NULL,
                projection_name TEXT NOT NULL,
                status TEXT NOT NULL,
                attempts INTEGER DEFAULT 0,
                last_attempt DATETIME,
                error_message TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (event_id) REFERENCES events(event_id)
            )
        """
        )

        # Create indexes on outbox table
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_status
            ON outbox(status, projection_name)
        """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_event
            ON outbox(event_id)
        """
        )

        # Create consistency_snapshots table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS consistency_snapshots (
                snapshot_id TEXT PRIMARY KEY,
                neo4j_count INTEGER,
                chromadb_count INTEGER,
                discrepancies TEXT,
                checked_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                status TEXT
            )
        """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_checked_at
            ON consistency_snapshots(checked_at)
        """
        )

        # Create embedding_cache table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS embedding_cache (
                text_hash TEXT NOT NULL,
                model_name TEXT NOT NULL,
                embedding TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (text_hash, model_name)
            )
        """
        )

        # Create index on text_hash for fast lookups
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_text_hash
            ON embedding_cache(text_hash)
        """
        )

        # Create index on created_at for cache management
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_cache_created_at
            ON embedding_cache(created_at)
        """
        )

        # Commit changes
        conn.commit()

        print("✅ Event store database initialized successfully!")
        print("   - events table created")
        print("   - outbox table created")
        print("   - consistency_snapshots table created")
        print("   - embedding_cache table created")
        print("   - Indexes created")

        # Verify schema
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"\n📋 Tables in database: {[t[0] for t in tables]}")

        return True

    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        conn.rollback()
        return False

    finally:
        conn.close()


if __name__ == "__main__":
    init_event_store()
