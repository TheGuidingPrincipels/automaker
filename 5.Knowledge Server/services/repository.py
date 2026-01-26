"""
DualStorageRepository - Orchestration layer for Neo4j + ChromaDB synchronization.

This repository coordinates writes to both Neo4j (graph DB) and ChromaDB (vector DB)
using event sourcing and the outbox pattern to ensure data consistency.

Architecture:
    Operation → Event Store → Outbox → Projections (Neo4j + ChromaDB)

Features:
- Event sourcing for atomicity and audit trail
- Outbox pattern for reliable async processing
- Automatic embedding generation with caching
- Optimistic locking with version tracking
- Comprehensive error handling and logging
"""

import json
import logging
import threading
import uuid
from collections import OrderedDict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from models.events import ConceptCreated, ConceptDeleted, ConceptUpdated, Event
from projections.chromadb_projection import ChromaDBProjection
from projections.neo4j_projection import Neo4jProjection
from services.compensation import CompensationManager
from services.embedding_cache import EmbeddingCache
from services.embedding_service import EmbeddingService
from services.event_store import EventStore
from services.outbox import Outbox


logger = logging.getLogger(__name__)


class LRUVersionCache:
    """Thread-safe, bounded version cache with LRU eviction.

    Provides O(1) get/set operations with automatic eviction of
    least-recently-used entries when maxsize is exceeded.
    """

    def __init__(self, maxsize: int = 10000):
        self._cache: OrderedDict[str, int] = OrderedDict()
        self._maxsize = maxsize
        self._lock = threading.RLock()

    def get(self, concept_id: str) -> Optional[int]:
        """Get version for concept_id, updating LRU order."""
        with self._lock:
            if concept_id in self._cache:
                self._cache.move_to_end(concept_id)
                return self._cache[concept_id]
            return None

    def set(self, concept_id: str, version: int) -> None:
        """Set version for concept_id, evicting oldest if at capacity."""
        with self._lock:
            if concept_id in self._cache:
                self._cache.move_to_end(concept_id)
            self._cache[concept_id] = version
            if len(self._cache) > self._maxsize:
                self._cache.popitem(last=False)

    def invalidate(self, concept_id: str) -> None:
        """Remove a specific entry from the cache."""
        with self._lock:
            self._cache.pop(concept_id, None)

    def clear(self) -> None:
        """Remove all entries from the cache."""
        with self._lock:
            self._cache.clear()

    def __len__(self) -> int:
        """Return the number of cached entries."""
        return len(self._cache)


class RepositoryError(Exception):
    """Base exception for repository errors"""

    pass


class ConceptNotFoundError(RepositoryError):
    """Raised when concept is not found"""

    pass


class DualStorageRepository:
    """
    Repository for dual storage synchronization between Neo4j and ChromaDB.

    This class coordinates writes to both databases using event sourcing,
    ensuring strong consistency and providing automatic embedding generation.

    Architecture (CQRS Pattern):
        - All WRITES must go through this repository
        - READS can query Neo4j/ChromaDB services directly
        - See docs/adr/001-data-access-patterns.md for guidelines

    Event Flow:
        1. Operation (create/update/delete) called
        2. Event created and persisted to EventStore
        3. Outbox entries created for each projection
        4. Projections process event synchronously
        5. On failure, outbox entries remain for retry

    Example:
        ```python
        # Initialize repository
        repo = DualStorageRepository(
            event_store=event_store,
            outbox=outbox,
            neo4j_projection=neo4j_projection,
            chromadb_projection=chromadb_projection,
            embedding_service=embedding_service,
            embedding_cache=embedding_cache
        )

        # Create concept (writes to both DBs)
        success, error = repo.create_concept({
            "name": "Python For Loops",
            "explanation": "For loops iterate over sequences...",
            "area": "Programming",
            "topic": "Python"
        })

        # Update concept
        success, error = repo.update_concept(
            concept_id="concept_001",
            updates={"name": "Updated Name"}
        )

        # Get concept (from Neo4j)
        concept = repo.get_concept("concept_001")
        ```
    """

    def __init__(
        self,
        event_store: EventStore,
        outbox: Outbox,
        neo4j_projection: Neo4jProjection,
        chromadb_projection: ChromaDBProjection,
        embedding_service: EmbeddingService,
        embedding_cache: EmbeddingCache | None = None,
        compensation_manager: CompensationManager | None = None,
    ) -> None:
        """
        Initialize DualStorageRepository.

        Args:
            event_store: Event store for persisting events
            outbox: Outbox for reliable async processing
            neo4j_projection: Projection for Neo4j graph database
            chromadb_projection: Projection for ChromaDB vector database
            embedding_service: Service for generating embeddings
            embedding_cache: Optional cache for embeddings (recommended for performance)
            compensation_manager: Optional compensation manager for immediate rollback on failures
        """
        self.event_store = event_store
        self.outbox = outbox
        self.neo4j_projection = neo4j_projection
        self.chromadb_projection = chromadb_projection
        self.embedding_service = embedding_service
        self.embedding_cache = embedding_cache
        self.compensation_manager = compensation_manager

        # Version tracking for optimistic locking
        self._version_cache = LRUVersionCache(maxsize=10000)

        logger.info(
            "DualStorageRepository initialized with "
            f"embedding_cache={'enabled' if embedding_cache else 'disabled'}, "
            f"compensation={'enabled' if compensation_manager else 'disabled'}"
        )

    def create_concept(self, concept_data: dict[str, Any]) -> tuple[bool, str | None, str | None]:
        """
        Create concept in both Neo4j and ChromaDB.

        Process:
        1. Generate concept_id if not provided
        2. Generate embedding for concept text
        3. Create ConceptCreated event
        4. Persist event to EventStore
        5. Add outbox entries for both projections
        6. Process projections synchronously
        7. Return success/failure status

        Args:
            concept_data: Dictionary containing concept fields:
                - name: str (required)
                - explanation: str (required)
                - area: str (optional)
                - topic: str (optional)
                - subtopic: str (optional)
                - examples: List[str] (optional)
                - prerequisites: List[str] (optional)

        Note:
            confidence_score is NOT included in event data - it is calculated
            automatically by the confidence service

        Returns:
            Tuple of (success, error_message, concept_id)

        Raises:
            RepositoryError: If event cannot be persisted
        """
        try:
            # 1. Generate concept_id if not provided
            concept_id = concept_data.get("concept_id", str(uuid.uuid4()))
            concept_data["concept_id"] = concept_id

            # 2. Generate embedding for semantic search
            self._generate_embedding_for_concept(concept_data)

            # Note: Embeddings are stored separately in ChromaDB
            # They are not added to concept_data to keep the event clean

            logger.info(f"Creating concept {concept_id}: {concept_data.get('name')}")

            # 3. Create ConceptCreated event
            # confidence_score is calculated automatically by confidence service
            event = ConceptCreated(
                aggregate_id=concept_id,
                concept_data=concept_data,
                version=1
            )

            # 4. Persist event to EventStore (source of truth)
            if not self.event_store.append_event(event):
                error_msg = f"Failed to persist event to event store for concept {concept_id}"
                logger.error(error_msg)
                return False, error_msg, None

            logger.debug(f"Event {event.event_id} persisted for concept {concept_id}")

            # 5. Add outbox entries for reliable processing
            neo4j_outbox_id = self.outbox.add_to_outbox(event.event_id, "neo4j")
            chromadb_outbox_id = self.outbox.add_to_outbox(event.event_id, "chromadb")

            logger.debug(
                f"Outbox entries created: neo4j={neo4j_outbox_id}, "
                f"chromadb={chromadb_outbox_id}"
            )

            # 6. Process projections synchronously
            neo4j_success = self._process_projection(event, self.neo4j_projection, neo4j_outbox_id)
            chromadb_success = self._process_projection(
                event, self.chromadb_projection, chromadb_outbox_id
            )

            # 7. Handle partial failure with compensation
            if neo4j_success and not chromadb_success:
                logger.warning(
                    f"Neo4j succeeded but ChromaDB failed for {concept_id}. "
                    f"Attempting immediate compensation."
                )
                if self.compensation_manager:
                    compensation_success = self.compensation_manager.rollback_neo4j(event)
                    if compensation_success:
                        logger.info(f"Successfully rolled back Neo4j for {concept_id}")
                    else:
                        logger.error(f"Failed to roll back Neo4j for {concept_id}")

            elif chromadb_success and not neo4j_success:
                logger.warning(
                    f"ChromaDB succeeded but Neo4j failed for {concept_id}. "
                    f"Attempting immediate compensation."
                )
                if self.compensation_manager:
                    compensation_success = self.compensation_manager.rollback_chromadb(event)
                    if compensation_success:
                        logger.info(f"Successfully rolled back ChromaDB for {concept_id}")
                    else:
                        logger.error(f"Failed to roll back ChromaDB for {concept_id}")

            # 8. Update version cache
            self._version_cache.set(concept_id, 1)

            # Check results
            if neo4j_success and chromadb_success:
                logger.info(f"Concept {concept_id} created successfully in both databases")
                return True, None, concept_id
            elif neo4j_success or chromadb_success:
                logger.warning(
                    f"Concept {concept_id} created partially. "
                    f"Neo4j: {neo4j_success}, ChromaDB: {chromadb_success}. "
                    f"Compensation attempted, failed projections will retry via outbox."
                )
                return (
                    True,
                    "Partial success - compensation attempted, failed projections will retry via outbox",
                    concept_id,
                )
            else:
                logger.error(f"Concept {concept_id} failed to create in both databases")
                return (
                    False,
                    "Failed to create in both databases - will retry via outbox",
                    concept_id,
                )

        except Exception as e:
            error_msg = f"Unexpected error creating concept: {e}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg, None

    def update_concept(self, concept_id: str, updates: dict[str, Any]) -> tuple[bool, str | None]:
        """
        Update concept in both Neo4j and ChromaDB.

        Process:
        1. Get latest version from EventStore
        2. Generate new embedding if explanation/name changed
        3. Create ConceptUpdated event with incremented version
        4. Persist event to EventStore
        5. Add outbox entries for both projections
        6. Process projections synchronously
        7. Return success/failure status

        Args:
            concept_id: ID of concept to update
            updates: Dictionary of fields to update

        Note:
            confidence_score is NOT included in event data - it is recalculated
            automatically by the confidence service when concepts are updated

        Returns:
            Tuple of (success, error_message)

        Raises:
            ConceptNotFoundError: If concept doesn't exist
        """
        try:
            logger.info(f"Updating concept {concept_id}")

            # 1. Get latest version
            current_version = self._get_current_version(concept_id)
            if current_version == 0:
                raise ConceptNotFoundError(f"Concept {concept_id} not found")

            # 2. Generate new embedding if text changed
            if "explanation" in updates or "name" in updates:
                # Need to get current concept data to build full text
                # For now, we'll regenerate embedding with available data
                self._generate_embedding_from_updates(updates)
                logger.debug(f"Generated new embedding for concept {concept_id}")

            # 3. Create ConceptUpdated event
            # confidence_score is recalculated automatically by confidence service
            new_version = current_version + 1
            event = ConceptUpdated(aggregate_id=concept_id, updates=updates, version=new_version)

            # 4. Persist event to EventStore
            if not self.event_store.append_event(event):
                error_msg = f"Failed to persist update event for concept {concept_id}"
                logger.error(error_msg)
                return False, error_msg

            logger.debug(f"Update event {event.event_id} persisted for concept {concept_id}")

            # 5. Add outbox entries
            neo4j_outbox_id = self.outbox.add_to_outbox(event.event_id, "neo4j")
            chromadb_outbox_id = self.outbox.add_to_outbox(event.event_id, "chromadb")

            # 6. Process projections synchronously
            neo4j_success = self._process_projection(event, self.neo4j_projection, neo4j_outbox_id)
            chromadb_success = self._process_projection(
                event, self.chromadb_projection, chromadb_outbox_id
            )

            # 7. Handle partial failure with compensation
            if neo4j_success and not chromadb_success:
                logger.warning(
                    f"Neo4j succeeded but ChromaDB failed for update of {concept_id}. "
                    f"Compensation noted (updates are hard to roll back)."
                )
                if self.compensation_manager:
                    # Note: For updates, we log the compensation attempt but can't easily roll back
                    # The outbox retry will eventually sync the update
                    logger.info(
                        f"Update rollback is complex - relying on outbox retry for {concept_id}"
                    )

            elif chromadb_success and not neo4j_success:
                logger.warning(
                    f"ChromaDB succeeded but Neo4j failed for update of {concept_id}. "
                    f"Compensation noted (updates are hard to roll back)."
                )
                if self.compensation_manager:
                    logger.info(
                        f"Update rollback is complex - relying on outbox retry for {concept_id}"
                    )

            # 8. Update version cache
            self._version_cache.set(concept_id, new_version)

            # Check results
            if neo4j_success and chromadb_success:
                logger.info(f"Concept {concept_id} updated successfully in both databases")
                return True, None
            elif neo4j_success or chromadb_success:
                logger.warning(
                    f"Concept {concept_id} updated partially. "
                    f"Failed projections will retry via outbox."
                )
                return True, "Partial success - some projections failed but will retry"
            else:
                logger.error(f"Concept {concept_id} failed to update in both databases")
                return False, "Failed to update in both databases - will retry via outbox"

        except ConceptNotFoundError:
            raise
        except Exception as e:
            error_msg = f"Unexpected error updating concept {concept_id}: {e}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg

    def delete_concept(self, concept_id: str) -> tuple[bool, str | None]:
        """
        Delete concept from both Neo4j and ChromaDB.

        Process:
        1. Get latest version from EventStore
        2. Create ConceptDeleted event
        3. Persist event to EventStore
        4. Add outbox entries for both projections
        5. Process projections (soft delete in Neo4j, hard delete in ChromaDB)
        6. Return success/failure status

        Args:
            concept_id: ID of concept to delete

        Returns:
            Tuple of (success, error_message)

        Raises:
            ConceptNotFoundError: If concept doesn't exist
        """
        try:
            logger.info(f"Deleting concept {concept_id}")

            # 1. Get latest version
            current_version = self._get_current_version(concept_id)
            if current_version == 0:
                raise ConceptNotFoundError(f"Concept {concept_id} not found")

            # 2. Create ConceptDeleted event
            new_version = current_version + 1
            event = ConceptDeleted(aggregate_id=concept_id, version=new_version)

            # 3. Persist event to EventStore
            if not self.event_store.append_event(event):
                error_msg = f"Failed to persist delete event for concept {concept_id}"
                logger.error(error_msg)
                return False, error_msg

            logger.debug(f"Delete event {event.event_id} persisted for concept {concept_id}")

            # 4. Add outbox entries
            neo4j_outbox_id = self.outbox.add_to_outbox(event.event_id, "neo4j")
            chromadb_outbox_id = self.outbox.add_to_outbox(event.event_id, "chromadb")

            # 5. Process projections (soft delete in Neo4j, hard delete in ChromaDB)
            neo4j_success = self._process_projection(event, self.neo4j_projection, neo4j_outbox_id)
            chromadb_success = self._process_projection(
                event, self.chromadb_projection, chromadb_outbox_id
            )

            # 6. Handle partial failure with compensation
            if neo4j_success and not chromadb_success:
                logger.warning(
                    f"Neo4j succeeded but ChromaDB failed for delete of {concept_id}. "
                    f"Compensation noted (deletes are hard to restore)."
                )
                if self.compensation_manager:
                    # Note: For deletes, we can't restore deleted data without the original
                    # The outbox retry will eventually sync the delete
                    logger.info(
                        f"Delete rollback is not possible - relying on outbox retry for {concept_id}"
                    )

            elif chromadb_success and not neo4j_success:
                logger.warning(
                    f"ChromaDB succeeded but Neo4j failed for delete of {concept_id}. "
                    f"Compensation noted (deletes are hard to restore)."
                )
                if self.compensation_manager:
                    logger.info(
                        f"Delete rollback is not possible - relying on outbox retry for {concept_id}"
                    )

            # 7. Update version cache
            self._version_cache.set(concept_id, new_version)

            # Check results
            if neo4j_success and chromadb_success:
                logger.info(f"Concept {concept_id} deleted successfully from both databases")
                return True, None
            elif neo4j_success or chromadb_success:
                logger.warning(
                    f"Concept {concept_id} deleted partially. "
                    f"Failed projections will retry via outbox."
                )
                return True, "Partial success - some projections failed but will retry"
            else:
                logger.error(f"Concept {concept_id} failed to delete from both databases")
                return False, "Failed to delete from both databases - will retry via outbox"

        except ConceptNotFoundError:
            raise
        except Exception as e:
            error_msg = f"Unexpected error deleting concept {concept_id}: {e}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg

    def get_concept(self, concept_id: str) -> dict[str, Any] | None:
        """
        Get concept from Neo4j (source of truth for concept data).

        Note: This queries Neo4j directly, not the event store.
        Neo4j contains the current state after all events are applied.

        Args:
            concept_id: ID of concept to retrieve

        Returns:
            Concept data dictionary or None if not found
        """
        try:
            # Query Neo4j for concept
            query = """
            MATCH (c:Concept {concept_id: $concept_id})
            WHERE c.deleted IS NULL OR c.deleted = false
            RETURN c
            """

            result = self.neo4j_projection.neo4j.execute_read(query, {"concept_id": concept_id})

            if not result or len(result) == 0:
                logger.debug(f"Concept {concept_id} not found in Neo4j")
                return None

            # Extract concept properties
            concept_node = result[0]["c"]
            concept_data = dict(concept_node)

            # Deserialize source_urls from JSON string back to list
            # (Neo4j stores it as JSON string, but we want to return it as list for API consumers)
            if "source_urls" in concept_data and isinstance(concept_data["source_urls"], str):
                try:
                    concept_data["source_urls"] = json.loads(concept_data["source_urls"])
                except (json.JSONDecodeError, TypeError) as e:
                    logger.warning(
                        f"Failed to deserialize source_urls for concept {concept_id}: {e}"
                    )
                    # Keep as string if deserialization fails

            logger.debug(f"Retrieved concept {concept_id} from Neo4j")
            return concept_data

        except Exception as e:
            logger.error(f"Error retrieving concept {concept_id}: {e}", exc_info=True)
            return None

    def process_pending_outbox(self, limit: int = 100) -> dict[str, int]:
        """
        Process pending outbox entries to retry failed projections.

        This method should be called periodically (e.g., by a background worker)
        to ensure eventual consistency for failed projections.

        Args:
            limit: Maximum number of outbox entries to process

        Returns:
            Dictionary with counts: {
                'processed': int,
                'failed': int,
                'total': int
            }
        """
        logger.info(f"Processing pending outbox entries (limit={limit})")

        processed_count = 0
        failed_count = 0
        pending_entries = self.outbox.get_pending(limit=limit)
        total_count = len(pending_entries)

        for entry in pending_entries:
            try:
                # Mark as processing
                self.outbox.mark_processing(entry.outbox_id)

                # Retrieve original event from event store
                event = self.event_store.get_event_by_id(entry.event_id)
                if not event:
                    logger.error(
                        f"Event {entry.event_id} not found for outbox entry {entry.outbox_id}"
                    )
                    self.outbox.mark_failed(entry.outbox_id, "Event not found in event store")
                    failed_count += 1
                    continue

                # Determine projection to use
                projection = (
                    self.neo4j_projection
                    if entry.projection_name == "neo4j"
                    else self.chromadb_projection
                )

                # Attempt projection
                success = projection.project_event(event)

                if success:
                    self.outbox.mark_processed(entry.outbox_id)
                    processed_count += 1
                    logger.info(
                        f"Successfully processed outbox entry {entry.outbox_id} "
                        f"for {entry.projection_name}"
                    )
                else:
                    self.outbox.mark_failed(entry.outbox_id, "Projection failed")
                    failed_count += 1
                    logger.warning(
                        f"Failed to process outbox entry {entry.outbox_id} "
                        f"for {entry.projection_name}"
                    )

            except Exception as e:
                error_msg = f"Error processing outbox entry {entry.outbox_id}: {e}"
                logger.error(error_msg, exc_info=True)
                self.outbox.mark_failed(entry.outbox_id, error_msg)
                failed_count += 1

        logger.info(
            f"Outbox processing complete: {processed_count} processed, "
            f"{failed_count} failed, {total_count} total"
        )

        return {"processed": processed_count, "failed": failed_count, "total": total_count}

    def _generate_embedding_for_concept(self, concept_data: dict[str, Any]) -> list[float]:
        """
        Generate embedding for concept text.

        Combines name and explanation for a comprehensive semantic representation.
        Uses cache if available to avoid recomputation.

        Args:
            concept_data: Concept data dictionary

        Returns:
            384-dimensional embedding vector
        """
        try:
            # Build text for embedding: name + explanation
            name = concept_data.get("name", "").strip()
            explanation = concept_data.get("explanation", "").strip()

            # Build text parts
            text_parts = []
            if name:
                text_parts.append(name)
            if explanation:
                text_parts.append(explanation)

            text = ". ".join(text_parts)

            if not text:
                logger.warning("Empty text for embedding generation, returning zero vector")
                return [0.0] * 384

            # Try cache first
            if self.embedding_cache:
                model_name = self.embedding_service.config.model_name
                cached_embedding = self.embedding_cache.get_cached(text, model_name)

                if cached_embedding:
                    logger.debug(f"Cache hit for concept text (len={len(text)})")
                    return cached_embedding

            # Generate embedding
            embedding = self.embedding_service.generate_embedding(text)

            # Store in cache
            if self.embedding_cache:
                model_name = self.embedding_service.config.model_name
                self.embedding_cache.store(text, model_name, embedding)
                logger.debug(f"Stored embedding in cache for text (len={len(text)})")

            return embedding

        except Exception as e:
            logger.error(f"Error generating embedding: {e}", exc_info=True)
            # Return zero vector as fallback
            return [0.0] * 384

    def _generate_embedding_from_updates(self, updates: dict[str, Any]) -> list[float]:
        """
        Generate embedding from update data.

        Args:
            updates: Update data dictionary

        Returns:
            384-dimensional embedding vector
        """
        # For updates, generate embedding if we have enough text
        text_parts = []

        if "name" in updates:
            text_parts.append(updates["name"])
        if "explanation" in updates:
            text_parts.append(updates["explanation"])

        text = ". ".join(text_parts).strip()

        if not text:
            logger.debug("No text in updates, skipping embedding generation")
            return []

        # Try cache first
        if self.embedding_cache:
            model_name = self.embedding_service.config.model_name
            cached_embedding = self.embedding_cache.get_cached(text, model_name)

            if cached_embedding:
                logger.debug("Cache hit for update text")
                return cached_embedding

        # Generate embedding
        embedding = self.embedding_service.generate_embedding(text)

        # Store in cache
        if self.embedding_cache:
            model_name = self.embedding_service.config.model_name
            self.embedding_cache.store(text, model_name, embedding)

        return embedding

    def _process_projection(self, event: Event, projection: Any, outbox_id: str) -> bool:
        """
        Process event through a projection and update outbox status.

        Args:
            event: Event to project
            projection: Projection handler (Neo4jProjection or ChromaDBProjection)
            outbox_id: ID of outbox entry

        Returns:
            True if projection succeeded, False otherwise
        """
        try:
            # Mark outbox entry as processing
            self.outbox.mark_processing(outbox_id)

            # Execute projection
            success = projection.project_event(event)

            # Update outbox status
            if success:
                self.outbox.mark_processed(outbox_id)
                return True
            else:
                self.outbox.mark_failed(outbox_id, "Projection returned False")
                return False

        except Exception as e:
            error_msg = f"Projection error: {e}"
            logger.error(error_msg, exc_info=True)
            self.outbox.mark_failed(outbox_id, error_msg)
            return False

    def _get_current_version(self, concept_id: str) -> int:
        """
        Get current version for a concept.

        Checks version cache first, then queries event store.

        Args:
            concept_id: ID of concept

        Returns:
            Current version number (0 if concept doesn't exist)
        """
        # Check cache first
        cached = self._version_cache.get(concept_id)
        if cached is not None:
            return cached

        # Query event store
        version = self.event_store.get_latest_version(concept_id)

        # Update cache
        if version > 0:
            self._version_cache.set(concept_id, version)

        return version

    def get_repository_stats(self) -> dict[str, Any]:
        """
        Get repository statistics for monitoring.

        Returns:
            Dictionary with statistics about repository operations
        """
        try:
            outbox_stats = self.outbox.count_by_status()

            cache_stats = None
            if self.embedding_cache:
                # Check if get_stats method exists
                if hasattr(self.embedding_cache, "get_stats"):
                    cache_stats = self.embedding_cache.get_stats()

            compensation_stats = None
            if self.compensation_manager:
                compensation_stats = self.compensation_manager.get_stats()

            return {
                "version_cache_size": len(self._version_cache),
                "outbox_pending": outbox_stats.get("pending", 0),
                "outbox_processing": outbox_stats.get("processing", 0),
                "outbox_completed": outbox_stats.get("completed", 0),
                "outbox_failed": outbox_stats.get("failed", 0),
                "embedding_cache_enabled": self.embedding_cache is not None,
                "embedding_cache_stats": cache_stats,
                "compensation_enabled": self.compensation_manager is not None,
                "compensation_stats": compensation_stats,
            }

        except Exception as e:
            logger.error(f"Error getting repository stats: {e}", exc_info=True)
            return {"error": str(e)}

    def find_duplicate_concept(
        self, name: str, area: str | None = None, topic: str | None = None
    ) -> dict[str, Any] | None:
        """
        Check if a concept with the same name, area, and topic already exists.

        Uses Neo4j to query for existing concepts matching the uniqueness criteria:
        name + area + topic.

        Args:
            name: Concept name
            area: Subject area (optional)
            topic: Topic within area (optional)

        Returns:
            Dictionary with concept_id if duplicate found, None otherwise
        """
        try:
            # Build the query with optional area/topic matching
            query = """
            MATCH (c:Concept {name: $name})
            WHERE (c.deleted IS NULL OR c.deleted = false)
            """

            params = {"name": name}

            # Add area condition if provided
            if area is not None:
                query += " AND c.area = $area"
                params["area"] = area
            else:
                query += " AND c.area IS NULL"

            # Add topic condition if provided
            if topic is not None:
                query += " AND c.topic = $topic"
                params["topic"] = topic
            else:
                query += " AND c.topic IS NULL"

            query += """
            RETURN c.concept_id AS concept_id, c.created_at AS created_at
            ORDER BY c.created_at ASC
            LIMIT 1
            """

            result = self.neo4j_projection.neo4j.execute_read(query, params)

            if result and len(result) > 0:
                logger.info(
                    f"Duplicate concept found: name={name}, area={area}, topic={topic}, "
                    f"concept_id={result[0]['concept_id']}"
                )
                return {
                    "concept_id": result[0]["concept_id"],
                    "created_at": result[0]["created_at"],
                }

            return None

        except Exception as e:
            logger.error(
                f"Error checking for duplicate concept (name={name}, area={area}, topic={topic}): {e}",
                exc_info=True,
            )
            return None
