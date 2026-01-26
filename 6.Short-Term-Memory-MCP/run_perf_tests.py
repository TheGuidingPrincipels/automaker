#!/usr/bin/env python3
"""Run performance tests and capture timing measurements"""
import time
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent))

from short_term_mcp.database import Database, Session, Concept

def test_db_init():
    """Test database initialization performance"""
    db_path = Path("test_perf.db")
    start = time.time()
    db = Database(db_path)
    db.initialize()
    elapsed = (time.time() - start) * 1000
    db.close()
    db_path.unlink()
    return elapsed

def test_batch_insert():
    """Test batch insert performance"""
    db_path = Path("test_perf_batch.db")
    db = Database(db_path)
    db.initialize()

    session = Session(session_id="2025-10-10", date="2025-10-10")
    db.create_session(session)

    concepts = [
        Concept(
            concept_id=f"concept-{i}",
            session_id="2025-10-10",
            concept_name=f"Concept {i}",
            current_data={"index": i}
        )
        for i in range(25)
    ]

    start = time.time()
    for concept in concepts:
        db.create_concept(concept)
    elapsed = (time.time() - start) * 1000

    db.close()
    db_path.unlink()
    return elapsed

def test_query():
    """Test query performance"""
    db_path = Path("test_perf_query.db")
    db = Database(db_path)
    db.initialize()

    session = Session(session_id="2025-10-10", date="2025-10-10")
    db.create_session(session)

    # Insert 25 concepts
    for i in range(25):
        concept = Concept(
            concept_id=f"concept-{i}",
            session_id="2025-10-10",
            concept_name=f"Concept {i}"
        )
        db.create_concept(concept)

    start = time.time()
    db.get_concepts_by_session("2025-10-10")
    elapsed = (time.time() - start) * 1000

    db.close()
    db_path.unlink()
    return elapsed

def test_complete_pipeline():
    """Test complete pipeline: init + insert + query"""
    db_path = Path("test_perf_pipeline.db")

    start = time.time()

    # Initialize
    db = Database(db_path)
    db.initialize()

    # Create session
    session = Session(session_id="2025-10-10", date="2025-10-10")
    db.create_session(session)

    # Insert 100 concepts
    for i in range(100):
        concept = Concept(
            concept_id=f"concept-{i}",
            session_id="2025-10-10",
            concept_name=f"Concept {i}",
            current_data={"index": i}
        )
        db.create_concept(concept)

    # Query
    db.get_concepts_by_session("2025-10-10")

    elapsed = (time.time() - start) * 1000

    db.close()
    db_path.unlink()
    return elapsed

if __name__ == "__main__":
    print("PERFORMANCE TEST RESULTS")
    print("=" * 60)

    # DB Init
    db_init_time = test_db_init()
    print(f"1. Database Initialization: {db_init_time:.2f}ms (target: <100ms)")
    print(f"   Status: {'PASS' if db_init_time < 100 else 'FAIL'}")

    # Batch Insert
    batch_time = test_batch_insert()
    print(f"\n2. Batch Insert (25 concepts): {batch_time:.2f}ms (target: <100ms)")
    print(f"   Status: {'PASS' if batch_time < 100 else 'FAIL'}")

    # Query
    query_time = test_query()
    print(f"\n3. Query Performance (25 concepts): {query_time:.2f}ms (target: <50ms)")
    print(f"   Status: {'PASS' if query_time < 50 else 'FAIL'}")

    # Complete Pipeline
    pipeline_time = test_complete_pipeline()
    print(f"\n4. Complete Pipeline (100 concepts): {pipeline_time:.2f}ms (target: <5000ms)")
    print(f"   Status: {'PASS' if pipeline_time < 5000 else 'FAIL'}")

    # Overall
    print("\n" + "=" * 60)
    all_pass = (
        db_init_time < 100 and
        batch_time < 100 and
        query_time < 50 and
        pipeline_time < 5000
    )
    print(f"OVERALL STATUS: {'PASS' if all_pass else 'FAIL'}")

    sys.exit(0 if all_pass else 1)
