#!/usr/bin/env python3
"""
MCP Knowledge Server - Health Check Script

This script performs comprehensive health checks on all MCP server components:
- Neo4j graph database connectivity and performance
- SQLite event store integrity and operations
- ChromaDB vector database access
- System resources and disk space

Outputs JSON for integration with monitoring tools like Prometheus, Grafana, etc.

Usage:
    python health_check.py [--json] [--verbose] [--check-write]

Exit codes:
    0: All checks passed
    1: One or more checks failed
    2: Critical failure (system unusable)
"""

import json
import os
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any


# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import chromadb
    from chromadb import PersistentClient
    from neo4j import GraphDatabase, basic_auth
except ImportError as e:
    print(f"Error: Missing required dependencies: {e}", file=sys.stderr)
    print("Install with: pip install neo4j chromadb", file=sys.stderr)
    sys.exit(2)


class HealthCheck:
    """Comprehensive health check for MCP Knowledge Server"""

    def __init__(self, verbose: bool = False, check_write: bool = False):
        self.verbose = verbose
        self.check_write = check_write
        self.results: dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat(),
            "overall_status": "healthy",
            "checks": {},
        }

        # Load configuration from centralized config system
        from config import get_settings
        settings = get_settings()

        self.neo4j_uri = settings.neo4j.uri
        self.neo4j_user = settings.neo4j.user
        self.neo4j_password = settings.neo4j.password
        self.event_store_path = settings.event_store_path
        self.chroma_persist_dir = settings.chromadb.persist_directory

    def log(self, message: str):
        """Log message if verbose mode enabled"""
        if self.verbose:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

    def check_neo4j(self) -> dict[str, Any]:
        """Check Neo4j database connectivity and health"""
        self.log("Checking Neo4j...")

        result = {
            "status": "unknown",
            "message": "",
            "latency_ms": 0,
            "database_info": {},
            "write_capable": None,
        }

        start_time = time.time()

        try:
            driver = GraphDatabase.driver(
                self.neo4j_uri, auth=basic_auth(self.neo4j_user, self.neo4j_password)
            )

            with driver.session() as session:
                # Test read capability
                test_result = session.run("RETURN 1 AS test").single()

                if test_result["test"] == 1:
                    result["status"] = "healthy"
                    result["message"] = "Neo4j connection successful"

                    # Get database info
                    try:
                        db_info = session.run(
                            "CALL dbms.components() YIELD name, versions, edition"
                        ).single()
                        result["database_info"] = {
                            "name": db_info["name"],
                            "versions": db_info["versions"],
                            "edition": db_info["edition"],
                        }
                    except Exception:
                        pass

                    # Optional write check
                    if self.check_write:
                        try:
                            session.run("CREATE (n:HealthCheck {timestamp: timestamp()}) DELETE n")
                            result["write_capable"] = True
                        except Exception as e:
                            result["write_capable"] = False
                            result["status"] = "degraded"
                            result["message"] += f" (write test failed: {e!s})"

                    # Get concept count
                    try:
                        count_result = session.run(
                            "MATCH (c:Concept) RETURN count(c) AS count"
                        ).single()
                        result["concept_count"] = count_result["count"]
                    except Exception:
                        pass

            driver.close()

            result["latency_ms"] = round((time.time() - start_time) * 1000, 2)

        except Exception as e:
            result["status"] = "unhealthy"
            result["message"] = f"Neo4j connection failed: {e!s}"
            result["latency_ms"] = round((time.time() - start_time) * 1000, 2)

        return result

    def check_sqlite(self) -> dict[str, Any]:
        """Check SQLite event store health"""
        self.log("Checking SQLite event store...")

        result = {
            "status": "unknown",
            "message": "",
            "file_exists": False,
            "file_size_mb": 0,
            "integrity": "unknown",
            "event_count": 0,
            "outbox_pending": 0,
        }

        try:
            # Check file exists
            if not os.path.exists(self.event_store_path):
                result["status"] = "unhealthy"
                result["message"] = f"Event store file not found: {self.event_store_path}"
                return result

            result["file_exists"] = True
            result["file_size_mb"] = round(
                os.path.getsize(self.event_store_path) / (1024 * 1024), 2
            )

            # Open database
            conn = sqlite3.connect(self.event_store_path)
            cursor = conn.cursor()

            # Check integrity
            integrity_result = cursor.execute("PRAGMA integrity_check").fetchone()
            if integrity_result[0] == "ok":
                result["integrity"] = "ok"
                result["status"] = "healthy"
                result["message"] = "Event store healthy"
            else:
                result["integrity"] = "corrupted"
                result["status"] = "unhealthy"
                result["message"] = f"Integrity check failed: {integrity_result[0]}"
                conn.close()
                return result

            # Get event count
            try:
                event_count = cursor.execute("SELECT COUNT(*) FROM events").fetchone()[0]
                result["event_count"] = event_count
            except Exception:
                pass

            # Get outbox pending count
            try:
                outbox_pending = cursor.execute(
                    "SELECT COUNT(*) FROM outbox WHERE status = 'pending'"
                ).fetchone()[0]
                result["outbox_pending"] = outbox_pending

                if outbox_pending > 100:
                    result["status"] = "degraded"
                    result["message"] += f" (high outbox pending: {outbox_pending})"
            except Exception:
                pass

            conn.close()

        except Exception as e:
            result["status"] = "unhealthy"
            result["message"] = f"Event store check failed: {e!s}"

        return result

    def check_chromadb(self) -> dict[str, Any]:
        """Check ChromaDB vector database health"""
        self.log("Checking ChromaDB...")

        result = {
            "status": "unknown",
            "message": "",
            "directory_exists": False,
            "directory_size_mb": 0,
            "collections": [],
            "concept_count": 0,
        }

        try:
            # Check directory exists
            if not os.path.exists(self.chroma_persist_dir):
                result["status"] = "unhealthy"
                result["message"] = f"ChromaDB directory not found: {self.chroma_persist_dir}"
                return result

            result["directory_exists"] = True

            # Get directory size
            total_size = 0
            for dirpath, _dirnames, filenames in os.walk(self.chroma_persist_dir):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    if os.path.exists(filepath):
                        total_size += os.path.getsize(filepath)
            result["directory_size_mb"] = round(total_size / (1024 * 1024), 2)

            # Connect to ChromaDB
            client = PersistentClient(path=self.chroma_persist_dir)

            # List collections
            collections = client.list_collections()
            result["collections"] = [col.name for col in collections]

            # Get concept count from "concepts" collection
            try:
                concepts_collection = client.get_collection("concepts")
                result["concept_count"] = concepts_collection.count()
            except Exception:
                pass

            result["status"] = "healthy"
            result["message"] = "ChromaDB accessible"

        except Exception as e:
            result["status"] = "unhealthy"
            result["message"] = f"ChromaDB check failed: {e!s}"

        return result

    def check_disk_space(self) -> dict[str, Any]:
        """Check disk space for data directories"""
        self.log("Checking disk space...")

        result = {"status": "healthy", "message": "Sufficient disk space", "data_directory": {}}

        try:
            import shutil

            project_dir = Path(__file__).parent.parent
            data_dir = project_dir / "data"

            if data_dir.exists():
                stat = shutil.disk_usage(str(data_dir))
                total_gb = stat.total / (1024**3)
                used_gb = stat.used / (1024**3)
                free_gb = stat.free / (1024**3)
                percent_used = (stat.used / stat.total) * 100

                result["data_directory"] = {
                    "total_gb": round(total_gb, 2),
                    "used_gb": round(used_gb, 2),
                    "free_gb": round(free_gb, 2),
                    "percent_used": round(percent_used, 2),
                }

                # Alert if less than 1GB free or more than 90% used
                if free_gb < 1.0:
                    result["status"] = "critical"
                    result["message"] = f"Critical: Only {free_gb:.2f}GB free"
                elif percent_used > 90:
                    result["status"] = "warning"
                    result["message"] = f"Warning: {percent_used:.1f}% disk used"

        except Exception as e:
            result["status"] = "unknown"
            result["message"] = f"Disk space check failed: {e!s}"

        return result

    def run_all_checks(self) -> dict[str, Any]:
        """Run all health checks"""
        self.log("Starting health checks...")

        # Run individual checks
        self.results["checks"]["neo4j"] = self.check_neo4j()
        self.results["checks"]["sqlite"] = self.check_sqlite()
        self.results["checks"]["chromadb"] = self.check_chromadb()
        self.results["checks"]["disk_space"] = self.check_disk_space()

        # Determine overall status
        statuses = [check["status"] for check in self.results["checks"].values()]

        if "unhealthy" in statuses or "critical" in statuses:
            self.results["overall_status"] = "unhealthy"
        elif "degraded" in statuses or "warning" in statuses:
            self.results["overall_status"] = "degraded"
        else:
            self.results["overall_status"] = "healthy"

        self.log(f"Health check complete: {self.results['overall_status']}")

        return self.results


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="MCP Knowledge Server Health Check")
    parser.add_argument("--json", action="store_true", help="Output in JSON format")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--check-write", action="store_true", help="Test write capability (Neo4j)")

    args = parser.parse_args()

    # Run health checks
    health_check = HealthCheck(verbose=args.verbose, check_write=args.check_write)
    results = health_check.run_all_checks()

    # Output results
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        # Human-readable output
        print("\nMCP Knowledge Server Health Check")
        print(f"Timestamp: {results['timestamp']}")
        print(f"Overall Status: {results['overall_status'].upper()}")
        print(f"\n{'='*60}")

        for component, result in results["checks"].items():
            status_symbol = (
                "✅"
                if result["status"] == "healthy"
                else "⚠️" if result["status"] in ["degraded", "warning"] else "❌"
            )
            print(f"\n{status_symbol} {component.upper()}: {result['status']}")
            print(f"   {result['message']}")

            # Show key metrics
            if component == "neo4j" and "latency_ms" in result:
                print(f"   Latency: {result['latency_ms']}ms")
                if "concept_count" in result:
                    print(f"   Concepts: {result['concept_count']}")

            if component == "sqlite":
                print(f"   Events: {result.get('event_count', 0)}")
                print(f"   Outbox Pending: {result.get('outbox_pending', 0)}")

            if component == "chromadb":
                print(f"   Concepts: {result.get('concept_count', 0)}")
                print(f"   Collections: {', '.join(result.get('collections', []))}")

            if component == "disk_space" and "data_directory" in result:
                dd = result["data_directory"]
                print(
                    f"   Disk: {dd.get('free_gb', 0):.2f}GB free ({dd.get('percent_used', 0):.1f}% used)"
                )

        print(f"\n{'='*60}\n")

    # Exit with appropriate code
    if results["overall_status"] == "healthy":
        sys.exit(0)
    elif results["overall_status"] in ["degraded", "warning"]:
        sys.exit(1)
    else:
        sys.exit(2)


if __name__ == "__main__":
    main()
