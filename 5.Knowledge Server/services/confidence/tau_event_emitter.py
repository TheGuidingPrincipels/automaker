"""
Event emitter for retention tau updates.

This module provides the event sourcing integration for tau updates,
ensuring that all writes go through EventStore -> Outbox -> Projections.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Optional, Protocol, Union

from models.events import ConceptTauUpdated
from services.confidence.models import Error, ErrorCode, Success

logger = logging.getLogger(__name__)


class TauEventEmitterProtocol(Protocol):
    """Protocol for emitting tau update events."""

    def emit_tau_updated(
        self,
        concept_id: str,
        new_tau: int,
        previous_tau: Optional[int] = None,
    ) -> Union[Success, Error]:
        """
        Emit a ConceptTauUpdated event through the event sourcing pipeline.

        Args:
            concept_id: The concept being updated
            new_tau: The new tau value
            previous_tau: The previous tau value (optional, for audit trail)

        Returns:
            Success if event was emitted and processed successfully
            Error if event emission failed
        """
        ...


class TauEventEmitter:
    """
    Emits tau update events through the event sourcing pipeline.

    Uses EventStore and Outbox to ensure reliable event processing,
    maintaining consistency with the rest of the system's event-driven architecture.
    """

    def __init__(
        self,
        event_store,  # EventStore type
        outbox,  # Outbox type
        neo4j_projection,  # Neo4jProjection type
    ) -> None:
        """
        Initialize the tau event emitter.

        Args:
            event_store: EventStore for persisting events
            outbox: Outbox for reliable async processing
            neo4j_projection: Neo4j projection for applying events
        """
        self.event_store = event_store
        self.outbox = outbox
        self.neo4j_projection = neo4j_projection

    def emit_tau_updated(
        self,
        concept_id: str,
        new_tau: int,
        previous_tau: Optional[int] = None,
    ) -> Union[Success, Error]:
        """
        Emit a ConceptTauUpdated event through the event sourcing pipeline.

        Flow:
        1. Get current version for the concept from event store
        2. Create ConceptTauUpdated event with incremented version
        3. Persist event to EventStore (source of truth)
        4. Add outbox entry for Neo4j projection
        5. Process projection synchronously
        6. Return success/failure status

        Args:
            concept_id: The concept being updated
            new_tau: The new tau value (minimum 1)
            previous_tau: The previous tau value (optional, for audit trail)

        Returns:
            Success with the new tau value if successful
            Error if event emission failed
        """
        try:
            # Ensure tau is valid
            new_tau = max(1, int(new_tau))

            # Get current version from event store
            current_version = self.event_store.get_latest_version(concept_id)
            if current_version == 0:
                # Concept doesn't exist in event store yet
                # This shouldn't happen in normal flow, but handle gracefully
                logger.warning(
                    f"Concept {concept_id} not found in event store. "
                    f"Using version 1 for tau update."
                )
                current_version = 0

            new_version = current_version + 1

            # Create the event
            event = ConceptTauUpdated(
                aggregate_id=concept_id,
                tau=new_tau,
                version=new_version,
                previous_tau=previous_tau,
            )

            # Persist to event store
            if not self.event_store.append_event(event):
                error_msg = f"Failed to persist tau update event for concept {concept_id}"
                logger.error(error_msg)
                return Error(error_msg, ErrorCode.DATABASE_ERROR)

            logger.debug(
                f"Event {event.event_id} persisted for concept {concept_id} tau update"
            )

            # Add outbox entry for Neo4j projection
            # (ChromaDB doesn't need tau, so we only add Neo4j entry)
            outbox_id = self.outbox.add_to_outbox(event.event_id, "neo4j")

            logger.debug(f"Outbox entry created: neo4j={outbox_id}")

            # Process projection synchronously
            try:
                self.outbox.mark_processing(outbox_id)
                success = self.neo4j_projection.project_event(event)

                if success:
                    self.outbox.mark_processed(outbox_id)
                    logger.info(
                        f"Tau updated for concept {concept_id}: "
                        f"{previous_tau} -> {new_tau}"
                    )
                    return Success(new_tau)
                else:
                    self.outbox.mark_failed(outbox_id, "Projection returned False")
                    logger.warning(
                        f"Neo4j projection failed for tau update of {concept_id}. "
                        f"Will retry via outbox."
                    )
                    # Return success since event is persisted - projection will retry
                    return Success(new_tau)

            except Exception as e:
                error_msg = f"Projection error: {e}"
                logger.error(error_msg, exc_info=True)
                self.outbox.mark_failed(outbox_id, error_msg)
                # Return success since event is persisted - projection will retry
                return Success(new_tau)

        except Exception as e:
            error_msg = f"Failed to emit tau update event: {e}"
            logger.error(error_msg, exc_info=True)
            return Error(error_msg, ErrorCode.DATABASE_ERROR)


class NoOpTauEventEmitter:
    """
    No-operation tau event emitter for testing and backwards compatibility.

    Logs a warning when used, as this bypasses event sourcing.
    """

    def emit_tau_updated(
        self,
        concept_id: str,
        new_tau: int,
        previous_tau: Optional[int] = None,
    ) -> Union[Success, Error]:
        """Log warning and return success (for testing only)."""
        logger.warning(
            f"NoOpTauEventEmitter: Tau update for {concept_id} not persisted "
            f"(no event emitter configured). This bypasses event sourcing."
        )
        return Success(new_tau)
