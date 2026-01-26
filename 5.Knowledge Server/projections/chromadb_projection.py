"""
ChromaDB Projection for Event Sourcing.

Projects events from the event store to ChromaDB vector database,
creating concept embeddings for semantic search.

Domain Mapping:
    Concept.explanation → ChromaDB 'documents' field (required for text content)
    Concept.{name,area,topic,subtopic} → ChromaDB 'metadatas' dict
    Concept.concept_id → ChromaDB 'ids' list
    confidence_score is stored in metadata (updated by confidence service)
"""

import logging
from datetime import UTC, datetime

from models.events import Event
from projections.base_projection import BaseProjection
from services.chromadb_service import ChromaDbService


logger = logging.getLogger(__name__)


class ChromaDBProjection(BaseProjection):
    """
    Projects events to ChromaDB vector database.

    Transforms event store events into vector embeddings,
    enabling semantic search across concepts.
    """

    def __init__(self, chromadb_service: ChromaDbService) -> None:
        """
        Initialize ChromaDB projection.

        Args:
            chromadb_service: ChromaDB service instance for database operations
        """
        self.chromadb = chromadb_service
        self.projection_name = "chromadb"

    def get_projection_name(self) -> str:
        """Get the name of this projection."""
        return self.projection_name

    def project_event(self, event: Event) -> bool:
        """
        Project an event to ChromaDB.

        Routes events to appropriate handlers based on event type.

        Args:
            event: The event to project

        Returns:
            True if projection successful, False otherwise
        """
        try:
            # Verify ChromaDB connection before processing
            if not self.chromadb.is_connected():
                logger.error(
                    f"ChromaDB not connected. Cannot project event {event.event_id}. "
                    f"Call chromadb_service.connect() first."
                )
                return False

            # Route to appropriate handler based on event type
            handler_map = {
                "ConceptCreated": self._handle_concept_created,
                "ConceptUpdated": self._handle_concept_updated,
                "ConceptDeleted": self._handle_concept_deleted,
            }

            handler = handler_map.get(event.event_type)
            if not handler:
                logger.warning(
                    f"No handler found for event type: {event.event_type}. "
                    f"Event ID: {event.event_id}"
                )
                return False

            # Execute handler
            success = handler(event)

            if success:
                logger.info(
                    f"Successfully projected {event.event_type} event. "
                    f"Event ID: {event.event_id}, Aggregate: {event.aggregate_id}"
                )
            else:
                logger.warning(
                    f"Failed to project {event.event_type} event. "
                    f"Event ID: {event.event_id}, Aggregate: {event.aggregate_id}"
                )

            return success

        except RuntimeError as e:
            logger.error(f"ChromaDB runtime error while projecting event {event.event_id}: {e}")
            return False

        except Exception as e:
            logger.error(f"Unexpected error projecting event {event.event_id}: {e}", exc_info=True)
            return False

    def _handle_concept_created(self, event: Event) -> bool:
        """
        Handle ConceptCreated event.

        Creates a new document in ChromaDB with concept text and metadata.

        Args:
            event: ConceptCreated event

        Returns:
            True if successful, False otherwise
        """
        try:
            concept_id = event.aggregate_id
            event_data = event.event_data

            # Extract document text (explanation)
            explanation = event_data.get("explanation", "")
            if not explanation:
                logger.warning(
                    f"ConceptCreated event {event.event_id} has empty explanation. "
                    f"Storing empty document for concept {concept_id}."
                )

            # Build metadata for filtering and display
            metadata = {
                "name": event_data.get("name", ""),
                "created_at": event.created_at.isoformat(),
                "last_modified": event.created_at.isoformat(),
            }

            # Add optional hierarchical metadata
            if "area" in event_data:
                metadata["area"] = event_data["area"]
            if "topic" in event_data:
                metadata["topic"] = event_data["topic"]
            if "subtopic" in event_data:
                metadata["subtopic"] = event_data["subtopic"]
            if "confidence_score" in event_data:
                metadata["confidence_score"] = event_data["confidence_score"]

            # NEW: Add source_urls summary (not full array - prevents metadata size issues)
            if event_data.get("source_urls"):
                urls = event_data["source_urls"]  # Already a list
                metadata["source_urls_count"] = len(urls)
                metadata["has_official_sources"] = any(
                    u.get("domain_category") == "official" for u in urls
                )
                # Full data stored in Neo4j only

            # Get collection
            collection = self.chromadb.get_collection()

            # Add document to ChromaDB (collection.add expects lists)
            collection.add(ids=[concept_id], documents=[explanation], metadatas=[metadata])

            logger.debug(
                f"ConceptCreated projection: Added document for concept {concept_id} "
                f"with metadata: {list(metadata.keys())}"
            )

            return True

        except Exception as e:
            logger.error(
                f"Error handling ConceptCreated event {event.event_id}: {e}", exc_info=True
            )
            return False

    def _handle_concept_updated(self, event: Event) -> bool:
        """
        Handle ConceptUpdated event.

        Updates the document and metadata for an existing concept.
        If explanation changed, embedding will be regenerated.

        Args:
            event: ConceptUpdated event

        Returns:
            True if successful, False otherwise
        """
        try:
            concept_id = event.aggregate_id
            updates = event.event_data.copy()

            # Get collection
            collection = self.chromadb.get_collection()

            # Check if concept exists first
            try:
                existing = collection.get(ids=[concept_id])
                if not existing or not existing["ids"]:
                    logger.warning(
                        f"ConceptUpdated: Concept {concept_id} not found in ChromaDB. "
                        f"Event: {event.event_id}. Cannot update non-existent document."
                    )
                    return False
            except Exception as e:
                logger.error(f"Error checking if concept exists: {e}")
                return False

            # Extract updated document (if explanation changed)
            updated_document = updates.get("explanation")

            # Build updated metadata
            # Start with existing metadata, then apply updates
            existing_metadata = existing["metadatas"][0] if existing["metadatas"] else {}
            updated_metadata = existing_metadata.copy()

            # Update timestamp
            updated_metadata["last_modified"] = datetime.now(UTC).isoformat()

            # Apply field updates from event
            if "name" in updates:
                updated_metadata["name"] = updates["name"]
            if "area" in updates:
                updated_metadata["area"] = updates["area"]
            if "topic" in updates:
                updated_metadata["topic"] = updates["topic"]
            if "subtopic" in updates:
                updated_metadata["subtopic"] = updates["subtopic"]
            if "confidence_score" in updates:
                updated_metadata["confidence_score"] = updates["confidence_score"]

            # NEW: Update source_urls summary if provided
            if updates.get("source_urls"):
                urls = updates["source_urls"]  # Already a list
                updated_metadata["source_urls_count"] = len(urls)
                updated_metadata["has_official_sources"] = any(
                    u.get("domain_category") == "official" for u in urls
                )

            # Use update() if we have new document, otherwise just update metadata
            if updated_document is not None:
                # Update both document and metadata
                collection.update(
                    ids=[concept_id], documents=[updated_document], metadatas=[updated_metadata]
                )
                logger.debug(
                    f"ConceptUpdated projection: Updated document and metadata "
                    f"for concept {concept_id}"
                )
            else:
                # Update only metadata (use upsert to handle metadata-only updates)
                # ChromaDB requires document for update(), so we keep existing
                existing_document = existing["documents"][0] if existing["documents"] else ""
                collection.update(
                    ids=[concept_id], documents=[existing_document], metadatas=[updated_metadata]
                )
                logger.debug(
                    f"ConceptUpdated projection: Updated metadata only " f"for concept {concept_id}"
                )

            return True

        except Exception as e:
            logger.error(
                f"Error handling ConceptUpdated event {event.event_id}: {e}", exc_info=True
            )
            return False

    def _handle_concept_deleted(self, event: Event) -> bool:
        """
        Handle ConceptDeleted event.

        Removes the concept document from ChromaDB.
        Operation is idempotent (doesn't fail if already deleted).

        Args:
            event: ConceptDeleted event

        Returns:
            True if successful, False otherwise
        """
        try:
            concept_id = event.aggregate_id

            # Get collection
            collection = self.chromadb.get_collection()

            # Delete document from ChromaDB
            # Note: ChromaDB delete() is idempotent - doesn't fail if ID doesn't exist
            collection.delete(ids=[concept_id])

            logger.debug(f"ConceptDeleted projection: Deleted document for concept {concept_id}")

            return True

        except Exception as e:
            logger.error(
                f"Error handling ConceptDeleted event {event.event_id}: {e}", exc_info=True
            )
            return False
