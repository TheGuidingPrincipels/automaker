"""SQLite database operations for Short-Term Memory MCP Server"""

import asyncio
import json
import logging
import sqlite3
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import AUTO_VACUUM, DB_PATH, ENABLE_WAL
from .models import (
    Concept,
    ConceptStatus,
    DomainWhitelist,
    ResearchCacheEntry,
    Session,
    SessionStatus,
    SourceURL,
    Stage,
)
from .utils import normalize_concept_name

INITIAL_DOMAIN_WHITELIST = [
    ("docs.python.org", "official", 1.0),
    ("reactjs.org", "official", 1.0),
    ("developer.mozilla.org", "official", 1.0),
    ("kubernetes.io", "official", 1.0),
    ("realpython.com", "in_depth", 0.8),
    ("freecodecamp.org", "in_depth", 0.8),
    ("css-tricks.com", "in_depth", 0.8),
    ("github.com", "authoritative", 0.6),
    ("stackoverflow.com", "authoritative", 0.6),
    ("medium.com", "authoritative", 0.6),
]

logger = logging.getLogger(__name__)


class DatabaseError(Exception):
    """Base exception for database errors"""

    pass


class Database:
    """SQLite database manager for Short-term MCP"""

    # Whitelist mapping for status to timestamp field (prevents SQL injection)
    STATUS_TIMESTAMP_FIELDS = {
        ConceptStatus.IDENTIFIED: "identified_at",
        ConceptStatus.CHUNKED: "chunked_at",
        ConceptStatus.ENCODED: "encoded_at",
        ConceptStatus.EVALUATED: "evaluated_at",
        ConceptStatus.STORED: "stored_at",
    }

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.connection: Optional[sqlite3.Connection] = None
        self._semaphore: Optional[asyncio.Semaphore] = None

        # Metrics tracking
        self.metrics = {
            "operations": {"reads": 0, "writes": 0, "queries": 0, "errors": 0},
            "timing": {"read_times": [], "write_times": [], "query_times": []},
            "errors": [],
        }

    @property
    def semaphore(self) -> asyncio.Semaphore:
        """Lazy-initialize semaphore to limit concurrent DB operations"""
        if self._semaphore is None:
            try:
                # Allow max 10 concurrent database operations (increased from 5 for better throughput)
                self._semaphore = asyncio.Semaphore(10)
            except RuntimeError:
                # If no event loop, create dummy semaphore for sync tests
                class DummySemaphore:
                    async def __aenter__(self):
                        return self

                    async def __aexit__(self, *args):
                        pass

                self._semaphore = DummySemaphore()
        return self._semaphore

    def initialize(self):
        """Create database and tables if they don't exist"""
        self.connection = sqlite3.connect(str(self.db_path), check_same_thread=False, timeout=5.0)
        self.connection.row_factory = sqlite3.Row

        # Enable foreign key constraints (required for CASCADE deletes)
        self.connection.execute("PRAGMA foreign_keys=ON")

        # Enable optimizations
        if ENABLE_WAL:
            self.connection.execute("PRAGMA journal_mode=WAL")
        if AUTO_VACUUM:
            self.connection.execute("PRAGMA auto_vacuum=FULL")

        self._create_tables()

    def _create_tables(self):
        """Create all tables with proper schema"""
        schema = """
        -- Sessions table: tracks daily learning sessions
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            date TEXT NOT NULL,
            learning_goal TEXT,
            building_goal TEXT,
            status TEXT DEFAULT 'in_progress',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        -- Concepts table: tracks individual concepts through pipeline
        CREATE TABLE IF NOT EXISTS concepts (
            concept_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            concept_name TEXT NOT NULL,
            current_status TEXT DEFAULT 'identified',

            -- Stage timestamps
            identified_at TEXT,
            chunked_at TEXT,
            encoded_at TEXT,
            evaluated_at TEXT,
            stored_at TEXT,

            -- Link to permanent storage
            knowledge_mcp_id TEXT,

            -- Hybrid storage: cumulative data
            current_data TEXT,  -- JSON

            -- User questions about this concept
            user_questions TEXT,  -- JSON array

            -- Metadata
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
        );

        -- Stage data table: incremental data per stage
        CREATE TABLE IF NOT EXISTS concept_stage_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            concept_id TEXT NOT NULL,
            stage TEXT NOT NULL,
            data TEXT NOT NULL,  -- JSON
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (concept_id) REFERENCES concepts(concept_id) ON DELETE CASCADE,
            UNIQUE(concept_id, stage)
        );

        -- Indexes for performance
        CREATE INDEX IF NOT EXISTS idx_sessions_date ON sessions(date);
        CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status);
        CREATE INDEX IF NOT EXISTS idx_concepts_session ON concepts(session_id);
        CREATE INDEX IF NOT EXISTS idx_concepts_status ON concepts(current_status);
        CREATE INDEX IF NOT EXISTS idx_concepts_session_status ON concepts(session_id, current_status);
        CREATE INDEX IF NOT EXISTS idx_concepts_name ON concepts(concept_name);
        CREATE INDEX IF NOT EXISTS idx_stage_data_concept_stage ON concept_stage_data(concept_id, stage);

        -- Research cache table: stores temporary research state
        CREATE TABLE IF NOT EXISTS research_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            concept_name TEXT NOT NULL UNIQUE,
            explanation TEXT NOT NULL,
            source_urls TEXT,
            last_researched_at TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_research_cache_name ON research_cache(concept_name);
        CREATE INDEX IF NOT EXISTS idx_research_cache_created ON research_cache(created_at);

        -- Domain whitelist table: trusted research sources
        CREATE TABLE IF NOT EXISTS domain_whitelist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            domain TEXT NOT NULL UNIQUE,
            category TEXT NOT NULL CHECK(category IN ('official', 'in_depth', 'authoritative', 'community')),
            quality_score REAL NOT NULL CHECK(quality_score >= 0.0 AND quality_score <= 1.0),
            added_at TEXT NOT NULL,
            added_by TEXT DEFAULT 'system'
        );
        CREATE INDEX IF NOT EXISTS idx_domain_whitelist_domain ON domain_whitelist(domain);
        CREATE INDEX IF NOT EXISTS idx_domain_whitelist_category ON domain_whitelist(category);
        """

        self.connection.executescript(schema)
        self._populate_initial_domains()
        self.connection.commit()

    def _populate_initial_domains(self):
        """Seed the domain whitelist with trusted defaults."""
        cursor = self.connection.cursor()
        now = datetime.now().isoformat()

        for domain, category, quality in INITIAL_DOMAIN_WHITELIST:
            cursor.execute(
                """
                INSERT OR IGNORE INTO domain_whitelist
                (domain, category, quality_score, added_at, added_by)
                VALUES (?, ?, ?, ?, 'system')
                """,
                (domain, category, quality, now),
            )

    def migrate_to_research_cache_schema(self):
        """Ensure research cache-related tables exist on older databases."""
        if not self.connection:
            self.initialize()
            return

        cursor = self.connection.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='research_cache'"
        )
        research_exists = cursor.fetchone()

        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='domain_whitelist'"
        )
        whitelist_exists = cursor.fetchone()

        if research_exists and whitelist_exists:
            return

        self._create_tables()

    @contextmanager
    def transaction(self):
        """Context manager for transactions"""
        import time

        start = time.time()
        try:
            yield self.connection
            self.connection.commit()
            duration = (time.time() - start) * 1000
            logger.debug(f"Transaction committed in {duration:.2f}ms")
        except Exception as e:
            self.connection.rollback()
            logger.error(f"Transaction failed after {(time.time() - start) * 1000:.2f}ms: {e}")
            raise DatabaseError(f"Transaction failed: {e}")

    # SESSION OPERATIONS

    def create_session(self, session: Session) -> str:
        """Create a new session"""
        start = time.time()
        with self.transaction():
            self.connection.execute(
                """
                INSERT INTO sessions (session_id, date, learning_goal, building_goal, status)
                VALUES (?, ?, ?, ?, ?)
            """,
                (
                    session.session_id,
                    session.date,
                    session.learning_goal,
                    session.building_goal,
                    session.status.value,
                ),
            )

        # Record metrics
        duration_ms = (time.time() - start) * 1000
        self.record_operation("write", duration_ms)

        return session.session_id

    def get_session(self, session_id: str) -> Optional[Dict]:
        """Get session by ID"""
        start = time.time()

        cursor = self.connection.execute(
            "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
        )
        row = cursor.fetchone()

        # Record metrics
        duration_ms = (time.time() - start) * 1000
        self.record_operation("read", duration_ms)

        return dict(row) if row else None

    # CONCEPT OPERATIONS

    def create_concept(self, concept: Concept) -> str:
        """Create a new concept"""
        start = time.time()
        with self.transaction():
            self.connection.execute(
                """
                INSERT INTO concepts (
                    concept_id, session_id, concept_name, current_status,
                    identified_at, current_data, user_questions
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    concept.concept_id,
                    concept.session_id,
                    concept.concept_name,
                    concept.current_status.value,
                    concept.identified_at or datetime.now().isoformat(),
                    json.dumps(concept.current_data or {}),
                    json.dumps(
                        [q.model_dump() for q in concept.user_questions]
                        if concept.user_questions
                        else []
                    ),
                ),
            )

        # Record metrics
        duration_ms = (time.time() - start) * 1000
        self.record_operation("write", duration_ms)

        return concept.concept_id

    def get_concept(self, concept_id: str) -> Optional[Dict]:
        """Get concept by ID"""
        start = time.time()

        cursor = self.connection.execute(
            "SELECT * FROM concepts WHERE concept_id = ?", (concept_id,)
        )
        row = cursor.fetchone()

        # Record metrics
        duration_ms = (time.time() - start) * 1000
        self.record_operation("read", duration_ms)

        if row:
            result = dict(row)
            result["current_data"] = json.loads(result["current_data"] or "{}")
            result["user_questions"] = json.loads(result["user_questions"] or "[]")
            return result
        return None

    def update_concept_status(
        self, concept_id: str, new_status: ConceptStatus, timestamp: Optional[str] = None
    ) -> bool:
        """Update concept status and corresponding timestamp"""
        start = time.time()
        timestamp = timestamp or datetime.now().isoformat()
        # Use whitelist mapping to ensure only valid column names (SQL injection safe)
        timestamp_field = self.STATUS_TIMESTAMP_FIELDS[new_status]

        with self.transaction():
            # SQL injection safe: timestamp_field from STATUS_TIMESTAMP_FIELDS whitelist
            cursor = self.connection.execute(
                f"""
                UPDATE concepts
                SET current_status = ?,
                    {timestamp_field} = ?,
                    updated_at = ?
                WHERE concept_id = ?
            """,  # nosec B608
                (new_status.value, timestamp, timestamp, concept_id),
            )

            success = cursor.rowcount > 0

        # Record metrics
        duration_ms = (time.time() - start) * 1000
        self.record_operation("write", duration_ms)

        return success

    def get_concepts_by_session(
        self, session_id: str, status_filter: Optional[ConceptStatus] = None
    ) -> List[Dict]:
        """Get all concepts for a session, optionally filtered by status"""
        start = time.time()

        if status_filter:
            cursor = self.connection.execute(
                """
                SELECT * FROM concepts
                WHERE session_id = ? AND current_status = ?
                ORDER BY created_at
            """,
                (session_id, status_filter.value),
            )
        else:
            cursor = self.connection.execute(
                """
                SELECT * FROM concepts
                WHERE session_id = ?
                ORDER BY created_at
            """,
                (session_id,),
            )

        concepts = []
        for row in cursor.fetchall():
            concept = dict(row)
            concept["current_data"] = json.loads(concept["current_data"] or "{}")
            concept["user_questions"] = json.loads(concept["user_questions"] or "[]")
            concepts.append(concept)

        # Record metrics
        duration_ms = (time.time() - start) * 1000
        self.record_operation("query", duration_ms)

        return concepts

    # STAGE DATA OPERATIONS

    def store_stage_data(self, concept_id: str, stage: Stage, data: Dict[str, Any]) -> int:
        """Store stage-specific data (UPSERT)"""
        start = time.time()
        with self.transaction():
            cursor = self.connection.execute(
                """
                INSERT INTO concept_stage_data (concept_id, stage, data)
                VALUES (?, ?, ?)
                ON CONFLICT(concept_id, stage)
                DO UPDATE SET data = excluded.data, created_at = CURRENT_TIMESTAMP
            """,
                (concept_id, stage.value, json.dumps(data)),
            )

            last_id = cursor.lastrowid

        # Record metrics
        duration_ms = (time.time() - start) * 1000
        self.record_operation("write", duration_ms)

        return last_id

    def get_stage_data(self, concept_id: str, stage: Stage) -> Optional[Dict]:
        """Get stage-specific data"""
        start = time.time()

        cursor = self.connection.execute(
            """
            SELECT * FROM concept_stage_data
            WHERE concept_id = ? AND stage = ?
        """,
            (concept_id, stage.value),
        )

        row = cursor.fetchone()

        # Record metrics
        duration_ms = (time.time() - start) * 1000
        self.record_operation("read", duration_ms)

        if row:
            result = dict(row)
            result["data"] = json.loads(result["data"])
            return result
        return None

    # RELIABILITY OPERATIONS (Phase 4)

    def mark_session_complete(self, session_id: str) -> bool:
        """Mark a session as completed"""
        with self.transaction():
            cursor = self.connection.execute(
                """
                UPDATE sessions
                SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE session_id = ?
            """,
                (SessionStatus.COMPLETED.value, session_id),
            )
            return cursor.rowcount > 0

    def clear_old_sessions(self, cutoff_date: str) -> Dict[str, int]:
        """
        Manually clear sessions older than cutoff_date.
        Returns counts of deleted records.
        """
        with self.transaction():
            # Count concepts to delete
            concepts_cursor = self.connection.execute(
                """
                SELECT COUNT(*) FROM concepts
                WHERE session_id IN (
                    SELECT session_id FROM sessions WHERE date < ?
                )
            """,
                (cutoff_date,),
            )
            concepts_deleted = concepts_cursor.fetchone()[0]

            # Delete sessions (cascades to concepts and stage_data via foreign key)
            sessions_cursor = self.connection.execute(
                "DELETE FROM sessions WHERE date < ?", (cutoff_date,)
            )
            sessions_deleted = sessions_cursor.rowcount

            return {"sessions_deleted": sessions_deleted, "concepts_deleted": concepts_deleted}

    # CODE TEACHER OPERATIONS (Phase 5)

    def get_todays_session(self, date: Optional[str] = None) -> Optional[Dict]:
        """Get today's session (or specified date)"""
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        return self.get_session(date)

    def search_concepts(self, session_id: str, search_term: str) -> List[Dict]:
        """
        Search concepts by name or data content.
        Case-insensitive search in concept_name and current_data JSON.
        """
        search_pattern = f"%{search_term.lower()}%"

        cursor = self.connection.execute(
            """
            SELECT * FROM concepts
            WHERE session_id = ?
            AND (
                LOWER(concept_name) LIKE ?
                OR LOWER(current_data) LIKE ?
            )
            ORDER BY created_at
        """,
            (session_id, search_pattern, search_pattern),
        )

        concepts = []
        for row in cursor.fetchall():
            concept = dict(row)
            concept["current_data"] = json.loads(concept["current_data"] or "{}")
            concept["user_questions"] = json.loads(concept["user_questions"] or "[]")
            concepts.append(concept)

        return concepts

    # PHASE 6 OPERATIONS: User Questions & Relationships

    def add_question_to_concept(self, concept_id: str, question: str, session_stage: str) -> bool:
        """Add a user question to a concept's question list"""
        # Perform entire operation inside transaction for atomicity
        with self.transaction():
            # Get current concept (inside transaction to prevent race condition)
            concept = self.get_concept(concept_id)
            if not concept:
                return False

            # Get existing questions
            questions = concept.get("user_questions", [])

            # Add new question
            new_question = {
                "question": question,
                "asked_at": datetime.now().isoformat(),
                "session_stage": session_stage,
                "answered": False,
                "answer": None,
            }
            questions.append(new_question)

            # Update database
            cursor = self.connection.execute(
                """
                UPDATE concepts
                SET user_questions = ?,
                    updated_at = ?
                WHERE concept_id = ?
            """,
                (json.dumps(questions), datetime.now().isoformat(), concept_id),
            )

            return cursor.rowcount > 0

    def update_concept_data(self, concept_id: str, data_updates: Dict[str, Any]) -> bool:
        """Update concept's current_data JSON with new fields"""
        # Perform entire operation inside transaction for atomicity
        with self.transaction():
            # Get current concept (inside transaction to prevent race condition)
            concept = self.get_concept(concept_id)
            if not concept:
                return False

            # Merge new data with existing
            current_data = concept.get("current_data", {})
            current_data.update(data_updates)

            # Update database
            cursor = self.connection.execute(
                """
                UPDATE concepts
                SET current_data = ?,
                    updated_at = ?
                WHERE concept_id = ?
            """,
                (json.dumps(current_data), datetime.now().isoformat(), concept_id),
            )

            return cursor.rowcount > 0

    def get_concept_with_all_data(self, concept_id: str) -> Optional[Dict]:
        """
        Get concept with all stage data in a single query.
        Returns concept with 'stage_data' field containing all stages.
        """
        concept = self.get_concept(concept_id)
        if not concept:
            return None

        # Get all stage data for this concept
        cursor = self.connection.execute(
            """
            SELECT stage, data, created_at
            FROM concept_stage_data
            WHERE concept_id = ?
            ORDER BY created_at
        """,
            (concept_id,),
        )

        stage_data = {}
        for row in cursor.fetchall():
            stage_data[row[0]] = {"data": json.loads(row[1]), "created_at": row[2]}

        concept["stage_data"] = stage_data
        return concept

    # RESEARCH CACHE CRUD OPERATIONS (Session 3)

    def get_research_cache_entry(self, concept_name: str) -> Optional[ResearchCacheEntry]:
        """Get cached research entry by concept name"""
        normalized_name = normalize_concept_name(concept_name)

        cursor = self.connection.execute(
            """
            SELECT id, concept_name, explanation, source_urls,
                   last_researched_at, created_at, updated_at
            FROM research_cache
            WHERE concept_name = ?
        """,
            (normalized_name,),
        )

        row = cursor.fetchone()
        if not row:
            return None

        # Parse source_urls JSON array
        source_urls = []
        if row[3]:
            try:
                urls_data = json.loads(row[3])
                source_urls = [SourceURL(**url) for url in urls_data]
            except (json.JSONDecodeError, ValueError):
                # Malformed JSON - return empty array
                source_urls = []

        return ResearchCacheEntry(
            id=row[0],
            concept_name=row[1],
            explanation=row[2],
            source_urls=source_urls,
            last_researched_at=datetime.fromisoformat(row[4]),
            created_at=datetime.fromisoformat(row[5]),
            updated_at=datetime.fromisoformat(row[6]),
        )

    def upsert_research_cache(self, entry: ResearchCacheEntry) -> ResearchCacheEntry:
        """Insert or update research cache entry (UPSERT)"""
        normalized_name = normalize_concept_name(entry.concept_name)

        # Serialize source_urls to JSON
        source_urls_json = None
        if entry.source_urls:
            # Convert HttpUrl to string before serialization
            source_urls_json = json.dumps(
                [{**url.model_dump(), "url": str(url.url)} for url in entry.source_urls]
            )

        # UPSERT pattern: INSERT ... ON CONFLICT ... DO UPDATE
        with self.transaction():
            cursor = self.connection.execute(
                """
                INSERT INTO research_cache
                (concept_name, explanation, source_urls, last_researched_at, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(concept_name) DO UPDATE SET
                    explanation = excluded.explanation,
                    source_urls = excluded.source_urls,
                    last_researched_at = excluded.last_researched_at,
                    updated_at = excluded.updated_at
            """,
                (
                    normalized_name,
                    entry.explanation,
                    source_urls_json,
                    entry.last_researched_at.isoformat(),
                    entry.created_at.isoformat(),
                    entry.updated_at.isoformat(),
                ),
            )

            # Get the entry ID (for INSERT or UPDATE)
            if cursor.lastrowid:
                entry.id = cursor.lastrowid
            else:
                # UPDATE case - fetch existing ID
                cursor = self.connection.execute(
                    "SELECT id FROM research_cache WHERE concept_name = ?", (normalized_name,)
                )
                entry.id = cursor.fetchone()[0]

        return entry

    def delete_research_cache(self, concept_name: str) -> bool:
        """Delete research cache entry"""
        normalized_name = normalize_concept_name(concept_name)

        with self.transaction():
            cursor = self.connection.execute(
                "DELETE FROM research_cache WHERE concept_name = ?", (normalized_name,)
            )

            return cursor.rowcount > 0

    def search_research_cache(self, query: str, limit: int = 10) -> List[ResearchCacheEntry]:
        """Search research cache by partial concept name"""
        normalized_query = normalize_concept_name(query)

        cursor = self.connection.execute(
            """
            SELECT id, concept_name, explanation, source_urls,
                   last_researched_at, created_at, updated_at
            FROM research_cache
            WHERE concept_name LIKE ?
            ORDER BY created_at DESC
            LIMIT ?
        """,
            (f"%{normalized_query}%", limit),
        )

        entries = []
        for row in cursor.fetchall():
            # Parse source_urls
            source_urls = []
            if row[3]:
                try:
                    urls_data = json.loads(row[3])
                    source_urls = [SourceURL(**url) for url in urls_data]
                except (json.JSONDecodeError, ValueError):
                    source_urls = []

            entries.append(
                ResearchCacheEntry(
                    id=row[0],
                    concept_name=row[1],
                    explanation=row[2],
                    source_urls=source_urls,
                    last_researched_at=datetime.fromisoformat(row[4]),
                    created_at=datetime.fromisoformat(row[5]),
                    updated_at=datetime.fromisoformat(row[6]),
                )
            )

        return entries

    def add_domain_to_whitelist(
        self, domain: str, category: str, quality_score: float, added_by: str = "ai"
    ) -> Optional[DomainWhitelist]:
        """Add domain to whitelist. Returns None if domain already exists."""
        # Validate inputs
        if category not in ("official", "in_depth", "authoritative", "community"):
            raise ValueError(f"Invalid category: {category}")
        if not (0.0 <= quality_score <= 1.0):
            raise ValueError(f"Invalid quality_score: {quality_score}")

        domain_lower = domain.lower()
        now = datetime.now().isoformat()

        try:
            with self.transaction():
                cursor = self.connection.execute(
                    """
                    INSERT INTO domain_whitelist (domain, category, quality_score, added_at, added_by)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    (domain_lower, category, quality_score, now, added_by),
                )

                return DomainWhitelist(
                    id=cursor.lastrowid,
                    domain=domain_lower,
                    category=category,
                    quality_score=quality_score,
                    added_at=datetime.fromisoformat(now),
                    added_by=added_by,
                )
        except DatabaseError as e:
            # Check if this is a duplicate domain error (UNIQUE constraint)
            if "UNIQUE constraint" in str(e):
                return None
            # Re-raise other database errors
            raise

    def remove_domain_from_whitelist(self, domain: str) -> bool:
        """Remove domain from whitelist"""
        domain_lower = domain.lower()

        with self.transaction():
            cursor = self.connection.execute(
                "DELETE FROM domain_whitelist WHERE domain = ?", (domain_lower,)
            )

            return cursor.rowcount > 0

    def list_whitelisted_domains(self, category: Optional[str] = None) -> List[DomainWhitelist]:
        """List whitelisted domains, optionally filtered by category"""
        if category is not None:
            cursor = self.connection.execute(
                """
                SELECT id, domain, category, quality_score, added_at, added_by
                FROM domain_whitelist
                WHERE category = ?
                ORDER BY quality_score DESC, domain ASC
            """,
                (category,),
            )
        else:
            cursor = self.connection.execute(
                """
                SELECT id, domain, category, quality_score, added_at, added_by
                FROM domain_whitelist
                ORDER BY quality_score DESC, domain ASC
            """
            )

        domains = []
        for row in cursor.fetchall():
            domains.append(
                DomainWhitelist(
                    id=row[0],
                    domain=row[1],
                    category=row[2],
                    quality_score=row[3],
                    added_at=datetime.fromisoformat(row[4]),
                    added_by=row[5],
                )
            )

        return domains

    # METRICS & MONITORING

    def record_operation(self, operation_type: str, duration_ms: float):
        """Record operation metrics"""
        # Map operation types to their proper plural forms
        plural_map = {"read": "reads", "write": "writes", "query": "queries"}

        if operation_type in plural_map:
            plural_key = plural_map[operation_type]
            self.metrics["operations"][plural_key] += 1
            self.metrics["timing"][f"{operation_type}_times"].append(duration_ms)

            # Keep only last 1000 timing records to prevent memory growth
            if len(self.metrics["timing"][f"{operation_type}_times"]) > 1000:
                self.metrics["timing"][f"{operation_type}_times"] = self.metrics["timing"][
                    f"{operation_type}_times"
                ][-1000:]

    def record_error(self, error_type: str, error_message: str, context: Dict = None):
        """Record error for monitoring"""
        self.metrics["operations"]["errors"] += 1
        error_record = {
            "timestamp": datetime.now().isoformat(),
            "error_type": error_type,
            "message": error_message,
            "context": context or {},
        }
        self.metrics["errors"].append(error_record)

        # Keep only last 100 errors
        if len(self.metrics["errors"]) > 100:
            self.metrics["errors"] = self.metrics["errors"][-100:]

    def get_metrics(self) -> Dict:
        """Get current metrics"""
        metrics = {"operations": self.metrics["operations"].copy(), "timing": {}}

        # Calculate timing statistics
        for op_type, times in self.metrics["timing"].items():
            if times:
                metrics["timing"][op_type] = {
                    "count": len(times),
                    "min_ms": min(times),
                    "max_ms": max(times),
                    "avg_ms": sum(times) / len(times),
                }
            else:
                metrics["timing"][op_type] = {"count": 0, "min_ms": 0, "max_ms": 0, "avg_ms": 0}

        return metrics

    def get_errors(self, limit: int = 10, error_type: Optional[str] = None) -> List[Dict]:
        """Get recent errors"""
        errors = self.metrics["errors"]

        # Filter by error type if specified
        if error_type:
            errors = [e for e in errors if e["error_type"] == error_type]

        # Return most recent errors
        return errors[-limit:]

    def get_database_size(self) -> int:
        """Get database file size in bytes"""
        if self.db_path.exists():
            return self.db_path.stat().st_size
        return 0

    def get_health_status(self) -> Dict:
        """Get database health status"""
        try:
            # Test connection
            if not self.connection:
                return {"status": "disconnected", "message": "Database not connected"}

            # Test query
            cursor = self.connection.execute("SELECT 1")
            cursor.fetchone()

            # Get database info
            cursor = self.connection.execute("PRAGMA integrity_check")
            integrity = cursor.fetchone()[0]

            cursor = self.connection.execute("PRAGMA page_count")
            page_count = cursor.fetchone()[0]

            cursor = self.connection.execute("PRAGMA page_size")
            page_size = cursor.fetchone()[0]

            return {
                "status": "healthy",
                "connection": "active",
                "integrity": integrity,
                "size_bytes": page_count * page_size,
                "db_path": str(self.db_path),
            }

        except Exception as e:
            return {"status": "error", "message": str(e), "error_type": type(e).__name__}

    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            self.connection = None

    # ============================================================================
    # ASYNC WRAPPERS FOR NON-BLOCKING OPERATIONS (WITH SEMAPHORE)
    # ============================================================================

    async def async_create_session(self, session: Session) -> str:
        """Async wrapper for create_session with concurrency control"""
        async with self.semaphore:
            return await asyncio.to_thread(self.create_session, session)

    async def async_get_session(self, session_id: str) -> Optional[Dict]:
        """Async wrapper for get_session with concurrency control"""
        async with self.semaphore:
            return await asyncio.to_thread(self.get_session, session_id)

    async def async_create_concept(self, concept: Concept) -> str:
        """Async wrapper for create_concept"""
        async with self.semaphore:
            return await asyncio.to_thread(self.create_concept, concept)

    async def async_get_concept(self, concept_id: str) -> Optional[Dict]:
        """Async wrapper for get_concept"""
        async with self.semaphore:
            return await asyncio.to_thread(self.get_concept, concept_id)

    async def async_update_concept_status(
        self, concept_id: str, new_status: ConceptStatus, timestamp: Optional[str] = None
    ) -> bool:
        """Async wrapper for update_concept_status"""
        async with self.semaphore:
            return await asyncio.to_thread(
                self.update_concept_status, concept_id, new_status, timestamp
            )

    async def async_get_concepts_by_session(
        self, session_id: str, status_filter: Optional[ConceptStatus] = None
    ) -> List[Dict]:
        """Async wrapper for get_concepts_by_session"""
        async with self.semaphore:
            return await asyncio.to_thread(self.get_concepts_by_session, session_id, status_filter)

    async def async_store_stage_data(
        self, concept_id: str, stage: Stage, data: Dict[str, Any]
    ) -> int:
        """Async wrapper for store_stage_data"""
        async with self.semaphore:
            return await asyncio.to_thread(self.store_stage_data, concept_id, stage, data)

    async def async_get_stage_data(self, concept_id: str, stage: Stage) -> Optional[Dict]:
        """Async wrapper for get_stage_data"""
        async with self.semaphore:
            return await asyncio.to_thread(self.get_stage_data, concept_id, stage)

    async def async_mark_session_complete(self, session_id: str) -> bool:
        """Async wrapper for mark_session_complete"""
        async with self.semaphore:
            return await asyncio.to_thread(self.mark_session_complete, session_id)

    async def async_clear_old_sessions(self, cutoff_date: str) -> Dict[str, int]:
        """Async wrapper for clear_old_sessions"""
        async with self.semaphore:
            return await asyncio.to_thread(self.clear_old_sessions, cutoff_date)

    async def async_get_todays_session(self, date: Optional[str] = None) -> Optional[Dict]:
        """Async wrapper for get_todays_session"""
        async with self.semaphore:
            return await asyncio.to_thread(self.get_todays_session, date)

    async def async_search_concepts(self, session_id: str, search_term: str) -> List[Dict]:
        """Async wrapper for search_concepts"""
        async with self.semaphore:
            return await asyncio.to_thread(self.search_concepts, session_id, search_term)

    async def async_add_question_to_concept(
        self, concept_id: str, question: str, session_stage: str
    ) -> bool:
        """Async wrapper for add_question_to_concept"""
        async with self.semaphore:
            return await asyncio.to_thread(
                self.add_question_to_concept, concept_id, question, session_stage
            )

    async def async_update_concept_data(
        self, concept_id: str, data_updates: Dict[str, Any]
    ) -> bool:
        """Async wrapper for update_concept_data"""
        async with self.semaphore:
            return await asyncio.to_thread(self.update_concept_data, concept_id, data_updates)

    async def async_get_concept_with_all_data(self, concept_id: str) -> Optional[Dict]:
        """Async wrapper for get_concept_with_all_data"""
        async with self.semaphore:
            return await asyncio.to_thread(self.get_concept_with_all_data, concept_id)

    async def async_get_metrics(self) -> Dict:
        """Async wrapper for get_metrics"""
        async with self.semaphore:
            return await asyncio.to_thread(self.get_metrics)

    async def async_get_errors(
        self, limit: int = 10, error_type: Optional[str] = None
    ) -> List[Dict]:
        """Async wrapper for get_errors"""
        async with self.semaphore:
            return await asyncio.to_thread(self.get_errors, limit, error_type)

    async def async_get_database_size(self) -> int:
        """Async wrapper for get_database_size"""
        async with self.semaphore:
            return await asyncio.to_thread(self.get_database_size)

    async def async_get_health_status(self) -> Dict:
        """Async wrapper for get_health_status"""
        async with self.semaphore:
            return await asyncio.to_thread(self.get_health_status)

    # ASYNC WRAPPERS FOR RESEARCH CACHE OPERATIONS (Session 3)

    async def async_get_research_cache_entry(
        self, concept_name: str
    ) -> Optional[ResearchCacheEntry]:
        """Async wrapper for get_research_cache_entry"""
        async with self.semaphore:
            return await asyncio.to_thread(self.get_research_cache_entry, concept_name)

    async def async_upsert_research_cache(self, entry: ResearchCacheEntry) -> ResearchCacheEntry:
        """Async wrapper for upsert_research_cache"""
        async with self.semaphore:
            return await asyncio.to_thread(self.upsert_research_cache, entry)

    async def async_delete_research_cache(self, concept_name: str) -> bool:
        """Async wrapper for delete_research_cache"""
        async with self.semaphore:
            return await asyncio.to_thread(self.delete_research_cache, concept_name)

    async def async_search_research_cache(
        self, query: str, limit: int = 10
    ) -> List[ResearchCacheEntry]:
        """Async wrapper for search_research_cache"""
        async with self.semaphore:
            return await asyncio.to_thread(self.search_research_cache, query, limit)

    async def async_add_domain_to_whitelist(
        self, domain: str, category: str, quality_score: float, added_by: str = "ai"
    ) -> DomainWhitelist:
        """Async wrapper for add_domain_to_whitelist"""
        async with self.semaphore:
            return await asyncio.to_thread(
                self.add_domain_to_whitelist, domain, category, quality_score, added_by
            )

    async def async_remove_domain_from_whitelist(self, domain: str) -> bool:
        """Async wrapper for remove_domain_from_whitelist"""
        async with self.semaphore:
            return await asyncio.to_thread(self.remove_domain_from_whitelist, domain)

    async def async_list_whitelisted_domains(
        self, category: Optional[str] = None
    ) -> List[DomainWhitelist]:
        """Async wrapper for list_whitelisted_domains"""
        async with self.semaphore:
            return await asyncio.to_thread(self.list_whitelisted_domains, category)


# Global database instance
_db = Database()


def get_db() -> Database:
    """Get global database instance"""
    if not _db.connection:
        _db.initialize()
    return _db
