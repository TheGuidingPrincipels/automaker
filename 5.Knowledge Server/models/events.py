"""
Event models for event sourcing
"""

import json
import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, field_serializer, field_validator


class Event(BaseModel):
    """
    Base Event class for event sourcing

    All events in the system extend this base event model.
    Events are immutable records of state changes.

    Note: aggregate_id is the event sourcing term (DDD pattern).
    Use the concept_id property in application code for clarity.
    """

    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str
    aggregate_id: str
    aggregate_type: str
    event_data: dict[str, Any]
    metadata: dict[str, Any] | None = None
    version: int
    created_at: datetime = Field(default_factory=datetime.now)

    @property
    def concept_id(self) -> str:
        """Alias for aggregate_id - use this in application code for clarity."""
        return self.aggregate_id

    @field_validator('event_data', 'metadata', mode='after')
    @classmethod
    def validate_json_serializable(cls, value: dict[str, Any] | None, info):
        """Ensure payload dictionaries are JSON-serializable at creation time."""
        cls._ensure_serializable(value, info.field_name)
        return value

    @field_serializer("created_at")
    def serialize_datetime(self, dt: datetime) -> str:
        """Serialize datetime to ISO format string (Bug #8 fix - Pydantic V2 compatible)."""
        return dt.isoformat()

    @staticmethod
    def _ensure_serializable(data: dict[str, Any] | None, field_name: str) -> None:
        """Validate that `data` can be JSON serialized."""
        if data is None:
            return

        try:
            json.dumps(data)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"{field_name} must contain only JSON-serializable data. "
                f"Serialization failed: {exc}"
            ) from exc

    @staticmethod
    def _dump_json(data: dict[str, Any] | None, field_name: str) -> str | None:
        """Serialize payload dictionaries to JSON strings with validation."""
        if data is None:
            return None
        Event._ensure_serializable(data, field_name)
        return json.dumps(data)

    def to_json(self) -> str:
        """Convert event to JSON string"""
        payload = self.model_dump()
        payload["event_data"] = json.loads(self._dump_json(self.event_data, "event_data"))
        payload["metadata"] = (
            json.loads(self._dump_json(self.metadata, "metadata"))
            if self.metadata is not None
            else None
        )
        return json.dumps(payload)

    @classmethod
    def from_json(cls, json_str: str) -> "Event":
        """Create event from JSON string"""
        return cls.model_validate_json(json_str)

    def to_db_dict(self) -> dict[str, Any]:
        """
        Convert event to dictionary suitable for database storage

        Returns:
            Dictionary with JSON-serialized event_data and metadata
        """
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "aggregate_id": self.aggregate_id,
            "aggregate_type": self.aggregate_type,
            "event_data": self._dump_json(self.event_data, "event_data"),
            "metadata": self._dump_json(self.metadata, "metadata"),
            "version": self.version,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_db_row(cls, row: tuple) -> "Event":
        """
        Create event from database row

        Args:
            row: Tuple from SQLite query (event_id, event_type, aggregate_id,
                 aggregate_type, event_data, metadata, version, created_at)

        Returns:
            Event instance
        """
        return cls(
            event_id=row[0],
            event_type=row[1],
            aggregate_id=row[2],
            aggregate_type=row[3],
            event_data=json.loads(row[4]),
            metadata=json.loads(row[5]) if row[5] is not None else None,
            version=row[6],
            created_at=datetime.fromisoformat(row[7]),
        )


class ConceptCreated(Event):
    """Event fired when a new concept is created"""

    def __init__(self, aggregate_id: str, concept_data: dict[str, Any], version: int = 1, **kwargs):
        super().__init__(
            event_type="ConceptCreated",
            aggregate_id=aggregate_id,
            aggregate_type="Concept",
            event_data=concept_data,
            version=version,
            **kwargs,
        )


class ConceptUpdated(Event):
    """Event fired when a concept is updated"""

    def __init__(self, aggregate_id: str, updates: dict[str, Any], version: int, **kwargs):
        super().__init__(
            event_type="ConceptUpdated",
            aggregate_id=aggregate_id,
            aggregate_type="Concept",
            event_data=updates,
            version=version,
            **kwargs,
        )


class ConceptDeleted(Event):
    """Event fired when a concept is deleted"""

    def __init__(self, aggregate_id: str, version: int, **kwargs):
        super().__init__(
            event_type="ConceptDeleted",
            aggregate_id=aggregate_id,
            aggregate_type="Concept",
            event_data={"deleted": True},
            version=version,
            **kwargs,
        )


class RelationshipCreated(Event):
    """Event fired when a relationship is created between concepts"""

    def __init__(
        self, aggregate_id: str, relationship_data: dict[str, Any], version: int = 1, **kwargs
    ):
        super().__init__(
            event_type="RelationshipCreated",
            aggregate_id=aggregate_id,
            aggregate_type="Relationship",
            event_data=relationship_data,
            version=version,
            **kwargs,
        )


class RelationshipDeleted(Event):
    """Event fired when a relationship is deleted"""

    def __init__(
        self, aggregate_id: str, version: int, event_data: dict[str, Any] | None = None, **kwargs
    ):
        # Default event_data if not provided (backward compatibility)
        if event_data is None:
            event_data = {"deleted": True}
        super().__init__(
            event_type="RelationshipDeleted",
            aggregate_id=aggregate_id,
            aggregate_type="Relationship",
            event_data=event_data,
            version=version,
            **kwargs,
        )


class ConceptTauUpdated(Event):
    """
    Event fired when a concept's retention tau value is updated.

    The retention tau is a time constant (in days) used in the exponential decay
    model for calculating retention scores. It increases with each successful review,
    representing improved memory retention.

    Event data contains:
        - tau: The new tau value (int, minimum 1)
        - previous_tau: The previous tau value (optional, for audit trail)
    """

    def __init__(
        self,
        aggregate_id: str,
        tau: int,
        version: int,
        previous_tau: Optional[int] = None,
        **kwargs
    ):
        event_data = {
            "tau": max(1, int(tau)),
        }
        if previous_tau is not None:
            event_data["previous_tau"] = previous_tau

        super().__init__(
            event_type="ConceptTauUpdated",
            aggregate_id=aggregate_id,
            aggregate_type="Concept",
            event_data=event_data,
            version=version,
            **kwargs
        )
