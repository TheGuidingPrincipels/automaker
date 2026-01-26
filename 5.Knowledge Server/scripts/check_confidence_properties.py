#!/usr/bin/env python3
"""
Script to check what confidence score properties actually exist on Concept nodes in Neo4j.
"""

import json
import os
import sys
from typing import Any

from neo4j import GraphDatabase


# Add parent directory to path to import config
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import Config


def connect_to_neo4j():
    """Establish connection to Neo4j database."""
    driver = GraphDatabase.driver(Config.NEO4J_URI, auth=(Config.NEO4J_USER, Config.NEO4J_PASSWORD))
    return driver


def query_confidence_properties(driver) -> List[Dict[str, Any]]:
    """Query Neo4j for confidence score properties on Concept nodes."""
    query = """
    MATCH (c:Concept)
    WHERE c.concept_id IS NOT NULL
    RETURN c.concept_id as concept_id,
           c.confidence_score as confidence_score,
           c.confidence_score_auto as confidence_score_auto,
           keys(c) as all_properties
    LIMIT 10
    """

    with driver.session() as session:
        result = session.run(query)
        records = [dict(record) for record in result]

    return records


def analyze_properties(records: list[dict[str, Any]]):
    """Analyze the properties found in the records."""
    print("\n" + "="*80)
    print("CONFIDENCE SCORE PROPERTY ANALYSIS")
    print("="*80 + "\n")

    if not records:
        print("No Concept nodes found in the database.")
        return

    print(f"Analyzed {len(records)} Concept nodes\n")

    # Track which properties exist
    has_confidence_score = False
    has_confidence_score_auto = False
    confidence_values = []
    confidence_auto_values = []

    # Detailed view of each concept
    print("DETAILED PROPERTY VIEW:")
    print("-" * 80)

    for i, record in enumerate(records, 1):
        concept_id = record['concept_id']
        confidence_score = record.get('confidence_score')
        confidence_score_auto = record.get('confidence_score_auto')
        all_props = record['all_properties']

        print(f"\n{i}. Concept ID: {concept_id}")
        print(f"   confidence_score: {confidence_score}")
        print(f"   confidence_score_auto: {confidence_score_auto}")

        # Find all confidence-related properties
        confidence_props = [prop for prop in all_props if 'confidence' in prop.lower()]
        print(f"   All confidence properties: {confidence_props}")
        print(f"   All properties: {all_props}")

        if confidence_score is not None:
            has_confidence_score = True
            confidence_values.append(confidence_score)

        if confidence_score_auto is not None:
            has_confidence_score_auto = True
            confidence_auto_values.append(confidence_score_auto)

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY:")
    print("="*80)
    print(f"\nProperty 'confidence_score' exists: {has_confidence_score}")
    if has_confidence_score:
        print(f"  - Found in {len(confidence_values)}/{len(records)} nodes")
        print(f"  - Sample values: {confidence_values[:5]}")
        print(f"  - Value range: {min(confidence_values, default='N/A')} to {max(confidence_values, default='N/A')}")

    print(f"\nProperty 'confidence_score_auto' exists: {has_confidence_score_auto}")
    if has_confidence_score_auto:
        print(f"  - Found in {len(confidence_auto_values)}/{len(records)} nodes")
        print(f"  - Sample values: {confidence_auto_values[:5]}")
        print(f"  - Value range: {min(confidence_auto_values, default='N/A')} to {max(confidence_auto_values, default='N/A')}")

    # Check for NULL values
    null_confidence = sum(1 for r in records if r.get('confidence_score') is None)
    null_confidence_auto = sum(1 for r in records if r.get('confidence_score_auto') is None)

    print(f"\nNULL counts:")
    print(f"  - confidence_score: {null_confidence}/{len(records)} nodes")
    print(f"  - confidence_score_auto: {null_confidence_auto}/{len(records)} nodes")

    print("\n" + "=" * 80)


def get_total_concept_count(driver) -> int:
    """Get total number of Concept nodes."""
    query = "MATCH (c:Concept) RETURN count(c) as count"
    with driver.session() as session:
        result = session.run(query)
        return result.single()["count"]


def main():
    """Main execution function."""
    print("Connecting to Neo4j...")
    driver = connect_to_neo4j()

    try:
        # Get total count
        total_concepts = get_total_concept_count(driver)
        print(f"Total Concept nodes in database: {total_concepts}")

        # Query and analyze
        print("\nQuerying sample of Concept nodes...")
        records = query_confidence_properties(driver)

        # Analyze results
        analyze_properties(records)

        # Save raw data to file for reference
        output_file = os.path.join(
            os.path.dirname(__file__),
            'confidence_properties_data.json'
        )
        with open(output_file, 'w') as f:
            json.dump(records, f, indent=2, default=str)
        print(f"\nRaw data saved to: {output_file}")

    finally:
        driver.close()
        print("\nConnection closed.")


if __name__ == "__main__":
    main()
