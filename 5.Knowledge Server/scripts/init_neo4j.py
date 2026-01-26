#!/usr/bin/env python3
"""
Neo4j Schema Initialization Script

Creates the complete Neo4j schema including:
- Node constraints (UNIQUE on all entity IDs)
- Indexes for performance optimization
- Verification of schema creation

Usage:
    python scripts/init_neo4j.py

Environment variables:
    NEO4J_URI: Neo4j connection URI (default: bolt://localhost:7687)
    NEO4J_USER: Neo4j username (default: neo4j)
    NEO4J_PASSWORD: Neo4j password (default: password)
"""

import sys

from neo4j import Driver, GraphDatabase, basic_auth
from neo4j.exceptions import AuthError, ServiceUnavailable


class Neo4jSchemaInitializer:
    """Initialize Neo4j database schema with constraints and indexes."""

    def __init__(self, uri: str, user: str, password: str):
        """
        Initialize schema initializer.

        Args:
            uri: Neo4j connection URI
            user: Neo4j username
            password: Neo4j password

        Raises:
            ValueError: If default password used in production environment
        """
        # Security: Prevent default credentials in production
        import os

        if os.getenv("ENV", "development") == "production" and password == "password":
            raise ValueError(
                "Default password 'password' is not allowed in production. "
                "Set NEO4J_PASSWORD environment variable."
            )

        self.uri = uri
        self.user = user
        self.password = password
        self.driver: Driver | None = None

    def connect(self) -> bool:
        """
        Connect to Neo4j database.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.driver = GraphDatabase.driver(self.uri, auth=basic_auth(self.user, self.password))
            # Verify connection
            self.driver.verify_connectivity()
            print(f"✅ Connected to Neo4j at {self.uri}")
            return True
        except ServiceUnavailable as e:
            print(f"❌ Failed to connect to Neo4j: {e}")
            return False
        except AuthError as e:
            print(f"❌ Authentication failed: {e}")
            return False
        except Exception as e:
            print(f"❌ Unexpected error connecting to Neo4j: {e}")
            return False

    def close(self) -> None:
        """Close Neo4j connection."""
        if self.driver:
            self.driver.close()
            print("✅ Neo4j connection closed")

    def create_constraints(self) -> bool:
        """
        Create UNIQUE constraints on all entity IDs.

        Returns:
            True if successful, False otherwise
        """
        if not self.driver:
            print("❌ No database connection")
            return False

        constraints = [
            ("concept_id_unique", "Concept", "concept_id"),
            ("area_id_unique", "Area", "area_id"),
            ("topic_id_unique", "Topic", "topic_id"),
            ("subtopic_id_unique", "Subtopic", "subtopic_id"),
        ]

        print("\n📋 Creating UNIQUE constraints...")

        with self.driver.session() as session:
            for constraint_name, label, property_name in constraints:
                try:
                    # Drop existing constraint if exists (idempotent)
                    session.run(f"DROP CONSTRAINT {constraint_name} IF EXISTS")

                    # Create new constraint
                    query = f"""
                    CREATE CONSTRAINT {constraint_name} IF NOT EXISTS
                    FOR (n:{label}) REQUIRE n.{property_name} IS UNIQUE
                    """
                    session.run(query)
                    print(f"  ✅ Created constraint: {constraint_name} on {label}.{property_name}")
                except Exception as e:
                    print(f"  ❌ Failed to create constraint {constraint_name}: {e}")
                    return False

        return True

    def create_indexes(self) -> bool:
        """
        Create indexes for performance optimization.

        Returns:
            True if successful, False otherwise
        """
        if not self.driver:
            print("❌ No database connection")
            return False

        # Single property indexes
        single_indexes = [
            ("concept_name_idx", "Concept", "name"),
            ("concept_confidence_idx", "Concept", "confidence_score"),
            ("concept_created_idx", "Concept", "created_at"),
            ("concept_modified_idx", "Concept", "last_modified"),
        ]

        # Composite indexes
        composite_indexes = [
            ("concept_area_topic_idx", "Concept", ["area", "topic"]),
        ]

        print("\n📋 Creating indexes...")

        with self.driver.session() as session:
            # Create single property indexes
            for index_name, label, property_name in single_indexes:
                try:
                    query = f"""
                    CREATE INDEX {index_name} IF NOT EXISTS
                    FOR (n:{label}) ON (n.{property_name})
                    """
                    session.run(query)
                    print(f"  ✅ Created index: {index_name} on {label}.{property_name}")
                except Exception as e:
                    print(f"  ❌ Failed to create index {index_name}: {e}")
                    return False

            # Create composite indexes
            for index_name, label, properties in composite_indexes:
                try:
                    props_str = ", ".join([f"n.{prop}" for prop in properties])
                    query = f"""
                    CREATE INDEX {index_name} IF NOT EXISTS
                    FOR (n:{label}) ON ({props_str})
                    """
                    session.run(query)
                    props_display = ", ".join(properties)
                    print(
                        f"  ✅ Created composite index: {index_name} on {label}.({props_display})"
                    )
                except Exception as e:
                    print(f"  ❌ Failed to create composite index {index_name}: {e}")
                    return False

        return True

    def verify_schema(self) -> bool:
        """
        Verify that all constraints and indexes were created successfully.

        Returns:
            True if schema is complete, False otherwise
        """
        if not self.driver:
            print("❌ No database connection")
            return False

        print("\n🔍 Verifying schema...")

        with self.driver.session() as session:
            # Verify constraints
            try:
                result = session.run("SHOW CONSTRAINTS")
                constraints = list(result)
                print(f"\n📊 Constraints found: {len(constraints)}")
                for constraint in constraints:
                    constraint_type = constraint.get("type", "UNKNOWN")
                    name = constraint.get("name", "UNKNOWN")
                    print(f"  ✓ {name} ({constraint_type})")

                # Check expected count (4 unique constraints)
                if len(constraints) < 4:
                    print(
                        f"  ⚠️  Warning: Expected at least 4 constraints, found {len(constraints)}"
                    )
            except Exception as e:
                print(f"  ❌ Failed to verify constraints: {e}")
                return False

            # Verify indexes
            try:
                result = session.run("SHOW INDEXES")
                indexes = list(result)
                print(f"\n📊 Indexes found: {len(indexes)}")
                for index in indexes:
                    index_type = index.get("type", "UNKNOWN")
                    name = index.get("name", "UNKNOWN")
                    state = index.get("state", "UNKNOWN")
                    print(f"  ✓ {name} ({index_type}) - State: {state}")

                # Note: Index count includes constraint-backed indexes
                if len(indexes) < 9:  # 4 constraints + 5 explicit indexes
                    print(f"  ⚠️  Warning: Expected at least 9 indexes, found {len(indexes)}")
            except Exception as e:
                print(f"  ❌ Failed to verify indexes: {e}")
                return False

        print("\n✅ Schema verification complete!")
        return True

    def initialize(self) -> bool:
        """
        Initialize complete Neo4j schema.

        Returns:
            True if successful, False otherwise
        """
        print("🚀 Starting Neo4j schema initialization...\n")

        if not self.connect():
            return False

        try:
            if not self.create_constraints():
                return False

            if not self.create_indexes():
                return False

            if not self.verify_schema():
                return False

            print("\n✅ Neo4j schema initialization complete!")
            return True

        finally:
            self.close()


def main():
    """Main entry point for schema initialization."""
    from config import get_settings

    # Get connection details from centralized config
    settings = get_settings()
    uri = settings.neo4j.uri
    user = settings.neo4j.user
    password = settings.neo4j.password

    # Initialize schema
    initializer = Neo4jSchemaInitializer(uri, user, password)
    success = initializer.initialize()

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
