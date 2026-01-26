import os

import pytest
from neo4j import AsyncGraphDatabase
from neo4j.exceptions import Neo4jError, ServiceUnavailable


@pytest.fixture
async def neo4j_session():
    """
    Provide an async Neo4j session for integration tests.

    If Neo4j connectivity is unavailable, skip the tests gracefully so the
    suite can continue without brittle failures on developer machines.
    """

    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "test")
    database = os.getenv("NEO4J_DATABASE", "neo4j")

    driver = AsyncGraphDatabase.driver(uri, auth=(user, password))

    try:
        try:
            await driver.verify_connectivity()
        except (ServiceUnavailable, Neo4jError, OSError) as exc:
            await driver.close()
            pytest.skip(f"Neo4j not available: {exc}")

        session = driver.session(database=database)
        try:
            yield session
        finally:
            await session.close()
    finally:
        await driver.close()
